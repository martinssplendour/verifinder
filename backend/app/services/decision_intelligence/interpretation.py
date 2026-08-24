from __future__ import annotations

import re

from app.schemas import AskInterpretation, AskRequest
from app.services.normalization import normalise_name


POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE)

# A list is capped at five unless the question names a count, so "sponsors in
# Leeds" returns a short readable list rather than a wall of twenty.
DEFAULT_LIST_LIMIT = 5
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
}
LIMIT_RE = re.compile(
    r"\b(?:top|first|best)\s+(\d{1,2}|" + "|".join(NUMBER_WORDS) + r")\b",
    re.IGNORECASE,
)
# Only a fallback for when Gemini is unavailable: the model decides response
# style as part of the query form, because phrasing varies far too much to
# capture in a pattern. A trailing question mark is deliberately not a signal -
# "top ten tech companies in Swinton?" is still a request for a list.
ANSWER_OPENER_RE = re.compile(
    r"^\s*(?:is|are|was|were|do|does|did|can|could|should|would|will|may|has|have|had|am"
    r"|what|which|who|whose|whom|how|why|when|where|tell|explain|compare)\b",
    re.IGNORECASE,
)
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
ROUTE_NAMES = {
    "skilled worker": "Skilled Worker",
    "scale up": "Scale-up",
    "scaleup": "Scale-up",
    "global business mobility": "Global Business Mobility",
}
FOLLOW_UP_RE = re.compile(
    r"\b(these|those|them|there|that|it|they|which|what about|how about|instead|also|"
    r"previous|earlier|same|above|former|latter)\b|^(?:and|but|so|then|now|in|near|around)\b",
    re.IGNORECASE,
)


def canonical_industry(value: str | None) -> str | None:
    """Map any wording of an industry onto the vocabulary the filters understand.

    The filter table is keyed on canonical names, so an unmapped value such as
    "Tech" silently matched nothing and dropped the filter altogether. Every
    industry reaching a query now passes through here first.
    """
    if not value:
        return None
    cleaned = normalise_name(value)
    if cleaned in INDUSTRY_NAME_TERMS:
        return cleaned
    for word in cleaned.split():
        if word in INDUSTRY_ALIASES:
            return INDUSTRY_ALIASES[word]
    return None


def canonical_route(value: str | None) -> str | None:
    """Match a sponsorship route to the exact spelling stored on the record."""
    if not value:
        return None
    return ROUTE_NAMES.get(normalise_name(value))


def explicit_limit(question: str) -> int | None:
    """The count the question names, written either as a word or a digit."""
    match = LIMIT_RE.search(question)
    if not match:
        return None
    value = match.group(1).lower()
    return NUMBER_WORDS.get(value) or int(value)


def fallback_response_style(question: str) -> str:
    """A rough guess used only when Gemini did not fill the form.

    Biased towards "list", because records are the evidence and a wrongly
    withheld list is a worse answer than a wrongly omitted paragraph.
    """
    if explicit_limit(question) is not None:
        return "list"
    return "answer" if ANSWER_OPENER_RE.search(question.strip()) else "list"


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
    named = explicit_limit(request.question)
    limit = min(request.limit, named if named is not None else DEFAULT_LIST_LIMIT)
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
        response_style=fallback_response_style(request.question),
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
        response_style=current.response_style,
        limit=current.limit if explicit_limit(request.question) is not None else min(request.limit, previous.limit),
        assumptions=list(dict.fromkeys(assumptions)),
    )
