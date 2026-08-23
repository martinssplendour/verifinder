from __future__ import annotations

import re

from app.schemas import AskInterpretation, AskRequest
from app.services.normalization import normalise_name


POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE)
LIMIT_RE = re.compile(r"\btop\s+(\d{1,2})\b", re.IGNORECASE)
LOCATION_RE = re.compile(
    r"\b(?:in|around|near|within)\s+([A-Za-z][A-Za-z .'-]{1,60}?)(?=\s+(?:for|with|that|which|where|under)\b|[?.!,]|$)",
    re.IGNORECASE,
)
INDUSTRY_ALIASES = {
    "tech": "technology",
    "technology": "technology",
    "software": "technology",
    "cyber": "technology",
    "cybersecurity": "technology",
    "data": "technology",
    "fintech": "technology",
    "finance": "financial services",
    "financial": "financial services",
    "healthcare": "healthcare",
    "health": "healthcare",
    "engineering": "engineering",
    "education": "education",
    "construction": "construction",
    "hospitality": "hospitality",
}
INDUSTRY_NAME_TERMS = {
    "technology": ("technology", "technologies", "software", "digital", "systems", "data", "cyber", "tech"),
    "financial services": ("financial", "finance", "fintech", "capital", "bank", "payments"),
    "healthcare": ("health", "medical", "care", "clinic", "pharma"),
    "engineering": ("engineering", "engineers"),
    "education": ("school", "college", "education", "academy", "university"),
    "construction": ("construction", "building", "builders"),
    "hospitality": ("hotel", "restaurant", "hospitality", "catering"),
}
FOLLOW_UP_RE = re.compile(
    r"\b(these|those|them|there|that|it|they|which|what about|how about|instead|also|"
    r"previous|earlier|same|above|former|latter)\b|^(?:and|but|so|then|now|in|near|around)\b",
    re.IGNORECASE,
)


def _location(question: str) -> str | None:
    postcode = POSTCODE_RE.search(question)
    if postcode:
        return postcode.group(0).upper()
    match = LOCATION_RE.search(question)
    return match.group(1).strip().title() if match else None


def _industry(question: str) -> str | None:
    words = set(normalise_name(question).split())
    for word, industry in INDUSTRY_ALIASES.items():
        if word in words:
            return industry
    return None


def _intent(question: str) -> str:
    value = normalise_name(question)
    if any(word in value.split() for word in ("job", "jobs", "vacancy", "vacancies", "role", "roles")) or any(
        phrase in value for phrase in ("hiring", "job opening", "career opening", "work opportunities")
    ):
        return "job_search"
    if any(word in value for word in ("sponsor", "sponsorship", "skilled worker", "work visa")):
        return "sponsor_discovery"
    if any(word in value for word in ("qualification", "certificate", "certification", "diploma", "regulated course")):
        return "qualification_search"
    if any(word in value for word in ("university", "study provider", "student sponsor", "college")):
        return "study_provider_search"
    if any(word in value for word in ("restaurant", "food", "cafe", "takeaway", "hygiene")):
        return "food_search"
    if any(word in value for word in ("property", "house", "home price", "sale price", "flat")):
        return "property_search"
    if any(word in value for word in ("crime", "flood", "planning", "area check", "postcode")):
        return "area_check"
    return "general"


def _subject(question: str, intent: str, location: str | None, industry: str | None) -> str | None:
    if intent == "sponsor_discovery":
        return None
    value = normalise_name(question)
    value = re.sub(r"\b(top\s+\d+|find|show|give|list|best|official|regulated|check|search|for|me)\b", " ", value)
    nouns = {
        "job_search": r"\b(jobs?|vacancies|vacancy|roles?|hiring|openings?|careers?|opportunities)\b",
        "qualification_search": r"\b(qualifications?|certificates?|certifications?|diplomas?|courses?)\b",
        "study_provider_search": r"\b(universities|university|colleges?|study providers?|student sponsors?)\b",
        "food_search": r"\b(restaurants?|food|cafes?|takeaways?|hygiene|ratings?)\b",
        "property_search": r"\b(properties|property|houses?|homes?|flats?|sale prices?)\b",
        "area_check": r"\b(crime|flood|planning|area|postcode|check)\b",
    }
    value = re.sub(nouns.get(intent, r"$^"), " ", value)
    if location:
        value = value.replace(normalise_name(location), " ")
    value = re.sub(r"\b(in|around|near|within|to|get|with|and)\b", " ", value)
    cleaned = " ".join(value.split())
    return cleaned or industry


def deterministic_interpretation(request: AskRequest) -> AskInterpretation:
    intent = _intent(request.question)
    location = None if intent == "qualification_search" else _location(request.question)
    industry = _industry(request.question)
    match = LIMIT_RE.search(request.question)
    limit = min(request.limit, int(match.group(1))) if match else request.limit
    route = None
    lowered = request.question.lower()
    if "skilled worker" in lowered:
        route = "Skilled Worker"
    elif "global business mobility" in lowered:
        route = "Global Business Mobility"
    elif "scale-up" in lowered or "scale up" in lowered:
        route = "Scale-up"
    assumptions: list[str] = []
    if intent == "job_search":
        assumptions.append("The question asks for live vacancies, but VeriFinder does not currently ingest a vacancies dataset.")
    if intent == "sponsor_discovery":
        assumptions.append("Results mean organisations listed on the current worker sponsor register, not employers promising a vacancy or visa.")
        if industry:
            assumptions.append("Industry is inferred from organisation-name terms because the sponsor register does not publish industry classifications.")
    return AskInterpretation(
        intent=intent,
        subject=_subject(request.question, intent, location, industry),
        location=location,
        industry=industry,
        sponsorship_route=route,
        limit=limit,
        assumptions=assumptions,
    )


def contextual_interpretation(request: AskRequest) -> AskInterpretation:
    """Resolve explicit follow-ups from the last bounded turn without inventing facts."""
    current = deterministic_interpretation(request)
    if not request.conversation or not FOLLOW_UP_RE.search(request.question):
        return current
    previous = request.conversation[-1].interpretation
    intent = previous.intent if current.intent == "general" else current.intent
    supports_industry = intent in {"job_search", "sponsor_discovery", "qualification_search"}
    supports_route = intent in {"job_search", "sponsor_discovery"}
    same_domain = intent == previous.intent or current.intent == "general"
    assumptions = list(dict.fromkeys([*previous.assumptions, *current.assumptions]))
    assumptions.append("This follow-up uses the previous question and returned records as conversation context.")
    return AskInterpretation(
        intent=intent,
        subject=current.subject or (previous.subject if same_domain else None),
        location=current.location or (previous.location if intent != "qualification_search" else None),
        industry=current.industry or (previous.industry if supports_industry else None),
        sponsorship_route=current.sponsorship_route or (previous.sponsorship_route if supports_route else None),
        limit=current.limit if LIMIT_RE.search(request.question) else min(request.limit, previous.limit),
        assumptions=list(dict.fromkeys(assumptions)),
    )
