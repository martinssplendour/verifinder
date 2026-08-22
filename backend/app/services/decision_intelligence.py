from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    DataSource,
    DatasetVersion,
    FoodEstablishmentRecord,
    OfsProviderRecord,
    PostcodeRecord,
    PropertySaleRecord,
    QualificationRecord,
    RunStatus,
    SchoolRecord,
    SponsorRecord,
    StudentSponsorRecord,
)
from app.schemas import (
    AskInterpretation,
    AskRequest,
    AskResponse,
    AskResult,
    DecisionFact,
    DecisionPlanResponse,
    PlanEvidence,
    PlanMetric,
    PlanQuestion,
    PlanRequest,
    PlanScenario,
    PlanStep,
    SourceAttribution,
)
from app.services.area_lookup import get_area_check
from app.services.dataset_utils import normalise_postcode
from app.services.food_lookup import latest_food_context
from app.services.gias_loader import SOURCE_ID as GIAS_SOURCE_ID
from app.services.normalization import normalise_name
from app.services.gemini_reasoning import GeminiReasoner
from app.services.property_loader import SOURCE_ID as PROPERTY_SOURCE_ID
from app.services.property_lookup import latest_property_context, search_properties
from app.services.qualification_lookup import search_qualifications
from app.services.sponsor_lookup import latest_sponsor_context, rating_label, source_attribution as sponsor_source
from app.services.study_lookup import latest_ofs_context, latest_student_sponsor_context, source_attribution as study_source


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


def _latest_context(session: Session, source_id: str) -> tuple[DataSource, DatasetVersion] | None:
    row = session.execute(
        select(DataSource, DatasetVersion)
        .join(DatasetVersion, DatasetVersion.source_id == DataSource.id)
        .where(DataSource.id == source_id, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else None


def _source(context: tuple[DataSource, DatasetVersion]) -> SourceAttribution:
    source, version = context
    return SourceAttribution(
        id=source.id,
        organisation=source.organisation,
        dataset=source.name,
        official_url=source.official_url,
        retrieved_at=version.retrieved_at,
        published_at=version.published_at,
        version=version.version_identifier,
        health=source.health.value,
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


def _fact(label: str, value: str, kind: str = "verified_fact") -> DecisionFact:
    return DecisionFact(kind=kind, label=label, value=value)


def _sponsor_results(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str]]:
    context = latest_sponsor_context(session)
    if not context:
        return [], ["The worker sponsor register has not been imported."]
    conditions = [SponsorRecord.dataset_version_id == context.version.id, SponsorRecord.active.is_(True)]
    if query.location:
        place = query.location.lower()
        conditions.append(
            or_(func.lower(SponsorRecord.town_city).contains(place), func.lower(SponsorRecord.county).contains(place))
        )
    industry_terms = INDUSTRY_NAME_TERMS.get(query.industry or "", ())
    if industry_terms:
        conditions.append(or_(*(SponsorRecord.normalised_name.contains(term) for term in industry_terms)))
    if query.sponsorship_route:
        conditions.append(cast(SponsorRecord.routes, Text).contains(query.sponsorship_route))
    candidates = list(session.scalars(select(SponsorRecord).where(*conditions).limit(max(query.limit * 30, 150))))

    def score(record: SponsorRecord) -> tuple[int, str]:
        value = 0
        if query.location and (record.town_city or "").lower() == query.location.lower():
            value += 4
        if query.sponsorship_route and query.sponsorship_route in (record.routes or []):
            value += 3
        if industry_terms and any(term in record.normalised_name for term in industry_terms):
            value += 2
        if rating_label(record.sponsor_rating) == "A":
            value += 1
        return (-value, record.organisation_name.lower())

    ranked = sorted(candidates, key=score)[: query.limit]
    source = sponsor_source(context)
    results: list[AskResult] = []
    for rank, record in enumerate(ranked, start=1):
        why = ["Listed on the current Home Office worker sponsor register"]
        facts = [
            _fact("Sponsor rating", rating_label(record.sponsor_rating) or "Not stated"),
            _fact("Routes", ", ".join(sorted(record.routes or [])) or "Not stated"),
            _fact("Register location", ", ".join(filter(None, (record.town_city, record.county))) or "Not stated"),
        ]
        if query.location:
            why.append(f"Register location matches {query.location}")
        if industry_terms:
            matched = sorted({term for term in industry_terms if term in record.normalised_name})
            facts.append(_fact("Industry signal", ", ".join(matched), "inference"))
            why.append("Organisation name contains the requested industry signal")
        results.append(
            AskResult(
                rank=rank,
                id=record.id,
                result_type="worker_sponsor",
                title=record.organisation_name,
                subtitle="Licensed worker sponsor",
                href=f"/sponsor/{record.id}",
                facts=facts,
                why_it_matches=why,
                source=source,
            )
        )
    limitations = [
        "This is a relevance shortlist, not a prediction of who will hire, sponsor, or approve a visa.",
        "The sponsor register does not contain vacancies, salaries, sponsorship history, or acceptance rates.",
    ]
    if industry_terms:
        limitations.append("Industry filtering uses organisation-name signals and must be verified against the legal company profile and role itself.")
    return results, limitations


def _qualification_results(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str]]:
    subject = query.subject or query.industry or ""
    records, _ = search_qualifications(session, subject, query.limit)
    return [
        AskResult(
            rank=index,
            id=item.id,
            result_type="qualification",
            title=item.title,
            subtitle=item.qualification_number,
            href=f"/qualification/{item.id}",
            facts=[
                _fact("Regulator", item.regulator),
                _fact("Awarding organisation", item.awarding_organisation_name),
                _fact("Level", item.level or "Not stated"),
                _fact("Status", item.status or "Not stated"),
            ],
            why_it_matches=[f"Official title matches “{subject}”"],
            source=item.source,
        )
        for index, item in enumerate(records, start=1)
    ], ["A regulated qualification match does not show which provider offers it locally or whether it fits a particular career goal."]


def _study_results(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str]]:
    results: list[AskResult] = []
    if query.location:
        student_context = latest_student_sponsor_context(session)
        if student_context:
            _, version = student_context
            rows = list(
                session.scalars(
                    select(StudentSponsorRecord)
                    .where(
                        StudentSponsorRecord.dataset_version_id == version.id,
                        func.lower(StudentSponsorRecord.town_city).contains(query.location.lower()),
                    )
                    .order_by(StudentSponsorRecord.organisation_name)
                    .limit(query.limit)
                )
            )
            source = study_source(student_context)
            for row in rows:
                results.append(
                    AskResult(
                        rank=0,
                        id=str(row.id),
                        result_type="student_sponsor",
                        title=row.organisation_name,
                        subtitle=row.sponsor_type or "Licensed student sponsor",
                        href=f"/study/student_sponsor/{row.id}",
                        facts=[_fact("Location", row.town_city or "Not stated"), _fact("Routes", ", ".join(row.routes or []))],
                        why_it_matches=[f"Student sponsor register location matches {query.location}"],
                        source=source,
                    )
                )
        ofs_context = latest_ofs_context(session)
        if ofs_context and len(results) < query.limit:
            _, version = ofs_context
            rows = list(
                session.scalars(
                    select(OfsProviderRecord)
                    .where(
                        OfsProviderRecord.dataset_version_id == version.id,
                        func.lower(OfsProviderRecord.contact_address).contains(query.location.lower()),
                    )
                    .order_by(OfsProviderRecord.legal_name)
                    .limit(query.limit - len(results))
                )
            )
            source = study_source(ofs_context)
            for row in rows:
                results.append(
                    AskResult(
                        rank=0,
                        id=str(row.id),
                        result_type="ofs_provider",
                        title=row.legal_name,
                        subtitle="Office for Students registered provider",
                        href=f"/study/ofs/{row.id}",
                        facts=[_fact("UKPRN", row.ukprn), _fact("Registration category", row.registration_category or "Not stated")],
                        why_it_matches=[f"Registered contact address matches {query.location}"],
                        source=source,
                    )
                )
    else:
        from app.services.study_lookup import search_study_providers

        records, _, _ = search_study_providers(session, query.subject or "", query.limit)
        for item in records[: query.limit]:
            results.append(
                AskResult(
                    rank=0,
                    id=item.id,
                    result_type=item.record_type,
                    title=item.name,
                    subtitle=item.provider_type,
                    href=f"/study/{item.record_type}/{item.id}",
                    facts=[_fact("Status", item.status or "Listed"), _fact("Location", item.town_city or "Not stated")],
                    why_it_matches=["Official provider name matches the request"],
                    source=item.source,
                )
            )
    for index, item in enumerate(results[: query.limit], start=1):
        item.rank = index
    return results[: query.limit], ["Student sponsorship permission and Office for Students registration are separate checks; neither alone is a course-quality score."]


def _food_results(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str]]:
    context = latest_food_context(session)
    if not context:
        return [], ["The Food Standards Agency snapshot has not been imported."]
    _, version = context
    conditions = [FoodEstablishmentRecord.dataset_version_id == version.id]
    term = query.location or query.subject
    if term:
        value = term.lower()
        conditions.append(
            or_(
                func.lower(FoodEstablishmentRecord.business_name).contains(value),
                func.lower(FoodEstablishmentRecord.address).contains(value),
                func.lower(FoodEstablishmentRecord.local_authority_name).contains(value),
                func.lower(FoodEstablishmentRecord.postcode).contains(value),
            )
        )
    rows = list(
        session.scalars(
            select(FoodEstablishmentRecord)
            .where(*conditions)
            .order_by(FoodEstablishmentRecord.rating_value.desc(), FoodEstablishmentRecord.rating_date.desc())
            .limit(query.limit)
        )
    )
    source = _source(context)
    return [
        AskResult(
            rank=index,
            id=row.id,
            result_type="food_establishment",
            title=row.business_name,
            subtitle=row.business_type,
            href=f"/food/{row.id}",
            facts=[
                _fact("Food hygiene rating", row.rating_value or "Not stated"),
                _fact("Rating date", row.rating_date.isoformat() if row.rating_date else "Not stated"),
                _fact("Address", ", ".join(filter(None, (row.address, row.postcode))) or "Not stated"),
            ],
            why_it_matches=[f"Official record matches {term}" if term else "Current official food hygiene record"],
            source=source,
        )
        for index, row in enumerate(rows, start=1)
    ], ["Food hygiene ratings measure compliance at inspection; they are not reviews of taste, price, or service."]


def _property_results(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str]]:
    context = latest_property_context(session)
    if not context:
        return [], ["The 2025–2026 Price Paid snapshot has not been imported."]
    source, version = context
    term = query.location or query.subject or ""
    if POSTCODE_RE.fullmatch(term.strip()):
        records, _ = search_properties(session, term, query.limit)
        return [
            AskResult(
                rank=index,
                id=row.property_key,
                result_type="property_sale",
                title=row.address,
                subtitle=row.postcode,
                href=f"/property/{row.property_key}",
                facts=[_fact("Latest recorded price", f"£{row.latest_price:,.0f}"), _fact("Transfer date", row.latest_transfer_date.isoformat())],
                why_it_matches=[f"Recorded sale postcode matches {term.upper()}"],
                source=row.source,
            )
            for index, row in enumerate(records, start=1)
        ], ["Property coverage is deliberately limited to imported 2025–2026 Price Paid records for England and Wales."]
    rows = list(
        session.scalars(
            select(PropertySaleRecord)
            .where(
                PropertySaleRecord.dataset_version_id == version.id,
                PropertySaleRecord.town_city == term.upper(),
            )
            .order_by(PropertySaleRecord.transfer_date.desc())
            .limit(query.limit * 8)
        )
    )
    unique: dict[str, PropertySaleRecord] = {}
    for row in rows:
        unique.setdefault(row.property_key, row)
    attribution = _source((source, version))
    return [
        AskResult(
            rank=index,
            id=row.property_key,
            result_type="property_sale",
            title=row.full_address,
            subtitle=row.postcode,
            href=f"/property/{row.property_key}",
            facts=[_fact("Recorded price", f"£{row.price:,.0f}"), _fact("Transfer date", row.transfer_date.isoformat())],
            why_it_matches=[f"Recorded sale location matches {term}"],
            source=attribution,
        )
        for index, row in enumerate(list(unique.values())[: query.limit], start=1)
    ], ["Results are recent recorded sales, not current listings, valuations, or a recommendation to buy.", "Coverage is limited to the imported 2025–2026 snapshot."]


async def _area_results(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str]]:
    postcode = query.location if query.location and POSTCODE_RE.fullmatch(query.location.strip()) else None
    if not postcode:
        return [], ["Area checks require a full postcode so crime, planning, and flood evidence can be matched precisely."]
    area = await get_area_check(session, postcode)
    if not area:
        return [], ["The postcode was not found in the current Code-Point Open snapshot."]
    facts = [
        _fact("Postcode", area.postcode.postcode),
        _fact("Latest monthly crime count", str(area.crime.latest_total) if area.crime.latest_total is not None else "Unavailable", "calculated_finding"),
        _fact("Planning constraints returned", str(area.planning.total) if area.planning.total is not None else "Unavailable", "calculated_finding"),
        _fact("Active flood warnings within 10 km", str(area.flood.total) if area.flood.total is not None else "Unavailable", "calculated_finding"),
    ]
    return [
        AskResult(
            rank=1,
            id=normalise_postcode(postcode) or postcode,
            result_type="area",
            title=f"Area check for {area.postcode.postcode}",
            href=f"/areas?postcode={postcode.replace(' ', '+')}",
            facts=facts,
            why_it_matches=["Exact postcode matched to the official postcode snapshot"],
            source=area.postcode.source,
        )
    ], area.limitations


async def answer_question(session: Session, request: AskRequest) -> AskResponse:
    settings = get_settings()
    deterministic = contextual_interpretation(request)
    reasoner = GeminiReasoner(settings.gemini_api_key, settings.gemini_model)
    # Follow-up resolution and capability boundaries are deterministic guardrails.
    # An LLM interpretation must not erase inherited filters or turn a vacancy
    # request into an unsupported general answer. Skipping interpretation here
    # also avoids paying for an unnecessary model call.
    guarded_context = bool(request.conversation and FOLLOW_UP_RE.search(request.question))
    interpreted = None
    if not guarded_context and deterministic.intent != "job_search":
        interpreted = await reasoner.interpret_question(
            request.question,
            request.limit,
            request.conversation,
        )
    query = deterministic if guarded_context or deterministic.intent == "job_search" else (interpreted or deterministic)
    interpreted_used = interpreted is not None and query is interpreted
    query.limit = min(query.limit, request.limit)
    suggested_questions: list[str] = []
    if query.intent == "job_search":
        results = []
        limitations = [
            "VeriFinder does not currently ingest a live jobs or vacancies feed, so it cannot verify or rank current openings.",
            "A sponsor-licence record shows that an organisation is licensed; it does not show that the organisation is hiring or that a particular role is eligible for sponsorship.",
        ]
        label = "live vacancy"
        industry_label = f"{query.industry} " if query.industry else ""
        location_label = f" in {query.location}" if query.location else ""
        suggested_questions = [
            f"Show me {industry_label}organisations with worker sponsorship{location_label}".replace("  ", " "),
        ]
        if query.industry:
            suggested_questions.append(f"Find regulated {query.industry} qualifications")
    elif query.intent == "sponsor_discovery":
        results, limitations = _sponsor_results(session, query)
        label = "licensed worker sponsor"
    elif query.intent == "qualification_search":
        results, limitations = _qualification_results(session, query)
        label = "regulated qualification"
    elif query.intent == "study_provider_search":
        results, limitations = _study_results(session, query)
        label = "study provider"
    elif query.intent == "food_search":
        results, limitations = _food_results(session, query)
        label = "food hygiene record"
    elif query.intent == "property_search":
        results, limitations = _property_results(session, query)
        label = "recent property sale"
    elif query.intent == "area_check":
        results, limitations = await _area_results(session, query)
        label = "area check"
    else:
        results, limitations, label = [], ["Ask VeriFinder currently answers questions about sponsors, qualifications, study providers, food hygiene, property sales, and postcode area checks."], "public-data result"
    place = f" in {query.location}" if query.location else ""
    if query.intent == "job_search":
        headline = "Live job listings are not connected yet"
        deterministic_summary = (
            f"I understood this as a request for {query.industry or 'job'} vacancies{place}, but I cannot "
            "truthfully produce a current top-ten list without a verified vacancies source. I can use the connected "
            "Home Office register to find relevant licensed worker sponsors instead."
        )
    elif query.intent == "general":
        headline = "That question is outside the connected evidence"
        deterministic_summary = (
            "I kept your question in the conversation, but the connected records cannot answer it yet. "
            "Try asking about sponsors, qualifications, study providers, food hygiene, property sales, or a postcode area check."
        )
    else:
        headline = f"{len(results)} {label}{'' if len(results) == 1 else 's'}{place}"
        deterministic_summary = (
            "These are the strongest matches under the interpreted filters. Open a result to inspect its official source and full record."
            if results
            else "No records matched the interpreted filters. Review the interpretation or make the question more specific."
        )
    synthesized = None
    if query.intent not in {"job_search", "general"}:
        synthesized = await reasoner.summarize_answer(
            question=request.question,
            interpretation=query,
            results=results,
            conversation=request.conversation,
            deterministic_summary=deterministic_summary,
        )
    return AskResponse(
        question=request.question,
        interpretation=query,
        headline=headline,
        summary=synthesized or deterministic_summary,
        results=results,
        total=len(results),
        limitations=limitations,
        suggested_questions=suggested_questions,
        ai_mode="gemini" if interpreted_used or synthesized else "deterministic",
        generated_at=datetime.now(timezone.utc),
    )


def _count_for_location(session: Session, model, version_id: str, column, location: str) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(model).where(model.dataset_version_id == version_id, func.lower(column).contains(location.lower()))
        )
        or 0
    )


def _market_candidates(session: Session, location: str, budget: int | None) -> tuple[list[dict], SourceAttribution | None]:
    context = latest_property_context(session)
    if not context:
        return [], None
    source, version = context
    compact = normalise_postcode(location)
    postcode = bool(POSTCODE_RE.fullmatch(location.strip()))
    outward = func.substr(PropertySaleRecord.normalised_postcode, 1, func.length(PropertySaleRecord.normalised_postcode) - 3)
    conditions = [PropertySaleRecord.dataset_version_id == version.id, PropertySaleRecord.normalised_postcode.is_not(None)]
    if postcode:
        conditions.append(PropertySaleRecord.normalised_postcode == compact)
    else:
        conditions.append(PropertySaleRecord.town_city == location.upper())
    rows = session.execute(
        select(
            outward.label("outward"),
            func.count(PropertySaleRecord.id).label("sales"),
            func.avg(PropertySaleRecord.price).label("average"),
            func.min(PropertySaleRecord.price).label("minimum"),
            func.max(PropertySaleRecord.price).label("maximum"),
            func.max(PropertySaleRecord.transfer_date).label("latest"),
            func.max(PropertySaleRecord.postcode).label("representative_postcode"),
        )
        .where(*conditions)
        .group_by(outward)
        .order_by(func.count(PropertySaleRecord.id).desc())
        .limit(12)
    ).all()
    candidates = [
        {
            "outward": row.outward,
            "sales": int(row.sales),
            "average": round(float(row.average)),
            "minimum": int(row.minimum),
            "maximum": int(row.maximum),
            "latest": row.latest,
            "representative_postcode": row.representative_postcode,
        }
        for row in rows
        if row.outward
    ]
    if budget:
        candidates.sort(key=lambda item: (abs(item["average"] - budget), -item["sales"]))
    return candidates, _source((source, version))


async def build_plan(session: Session, request: PlanRequest) -> DecisionPlanResponse:
    location = request.location.strip() if request.location else _location(request.goal)
    title = f"{request.template.title()} plan" + (f" for {location}" if location else "")
    plan_id = str(uuid.uuid4())
    status = "ready" if location else "needs_input"
    created_at = datetime.now(timezone.utc)

    evidence: list[PlanEvidence] = []
    questions: list[PlanQuestion] = []
    scenarios: list[PlanScenario] = []
    if not location:
        evidence.append(PlanEvidence(id="location-missing", kind="unknown", title="Target location", detail="No town, city, area, or full postcode could be identified from the goal."))
        questions.append(PlanQuestion(id="location", question="Which town, city, area, or postcode should this plan cover?", why_it_matters="Location is required to match the public datasets."))
    else:
        candidates, property_source = _market_candidates(session, location, request.budget)
        for index, candidate in enumerate(candidates[:3], start=1):
            evidence_id = f"property-{index}"
            evidence.append(
                PlanEvidence(
                    id=evidence_id,
                    kind="calculated_finding",
                    title=f"Recorded sales in {candidate['outward']}",
                    detail=(
                        f"{candidate['sales']:,} sales in the 2025–2026 snapshot; average £{candidate['average']:,.0f}, "
                        f"range £{candidate['minimum']:,.0f}–£{candidate['maximum']:,.0f}."
                    ),
                    source=property_source,
                )
            )
            strengths = [f"Backed by {candidate['sales']:,} recent recorded transactions"]
            if request.budget and candidate["average"] <= request.budget:
                strengths.append("Snapshot average is within the stated purchase budget")
            tradeoffs = ["Recorded sale prices are not current asking prices or valuations"]
            if request.budget and candidate["average"] > request.budget:
                tradeoffs.append(f"Snapshot average is £{candidate['average'] - request.budget:,.0f} above the stated budget")
            scenarios.append(
                PlanScenario(
                    id=f"area-{candidate['outward'].lower()}",
                    title=f"Explore {candidate['outward']}",
                    description="A postal-district shortlist based on recent transaction evidence, ready for exact-postcode checks.",
                    location=candidate["outward"],
                    metrics=[
                        PlanMetric(label="Recorded sales", value=f"{candidate['sales']:,}"),
                        PlanMetric(label="Average recorded price", value=f"£{candidate['average']:,.0f}"),
                        PlanMetric(label="Latest record", value=candidate["latest"].isoformat()),
                    ],
                    strengths=strengths,
                    tradeoffs=tradeoffs,
                    evidence_ids=[evidence_id],
                )
            )
        if not candidates:
            evidence.append(PlanEvidence(id="property-unknown", kind="unknown", title="Recent property evidence", detail=f"No 2025–2026 Price Paid records matched {location}."))

        sponsor_context = latest_sponsor_context(session)
        if sponsor_context:
            sponsor_count = _count_for_location(session, SponsorRecord, sponsor_context.version.id, SponsorRecord.town_city, location)
            evidence.append(
                PlanEvidence(
                    id="worker-sponsors",
                    kind="calculated_finding",
                    title="Worker sponsor presence",
                    detail=f"{sponsor_count:,} current worker-sponsor register records have a town/city matching {location}.",
                    source=sponsor_source(sponsor_context),
                )
            )
        student_context = latest_student_sponsor_context(session)
        if student_context:
            student_count = _count_for_location(session, StudentSponsorRecord, student_context[1].id, StudentSponsorRecord.town_city, location)
            evidence.append(
                PlanEvidence(
                    id="student-sponsors",
                    kind="calculated_finding",
                    title="Student sponsor presence",
                    detail=f"{student_count:,} current student-sponsor records have a town/city matching {location}.",
                    source=study_source(student_context),
                )
            )
        school_context = _latest_context(session, GIAS_SOURCE_ID)
        if school_context:
            school_count = _count_for_location(session, SchoolRecord, school_context[1].id, SchoolRecord.town, location)
            evidence.append(
                PlanEvidence(
                    id="schools",
                    kind="calculated_finding",
                    title="School register coverage",
                    detail=f"{school_count:,} school records have a town matching {location}; this is a count, not a quality ranking.",
                    source=_source(school_context),
                )
            )
        if POSTCODE_RE.fullmatch(location):
            area = await get_area_check(session, location)
            if area:
                evidence.extend(
                    [
                        PlanEvidence(id="crime", kind="calculated_finding", title="Latest street-crime count", detail=f"Police.uk returned {area.crime.latest_total if area.crime.latest_total is not None else 'no available'} crimes for the latest matched month around the postcode."),
                        PlanEvidence(id="planning", kind="calculated_finding", title="Planning designations", detail=f"Planning Data returned {area.planning.total if area.planning.total is not None else 'no available'} nearby designation records."),
                        PlanEvidence(id="flood", kind="calculated_finding", title="Active flood warnings", detail=f"The Environment Agency returned {area.flood.total if area.flood.total is not None else 'no available'} warnings within 10 km."),
                    ]
                )
        else:
            questions.append(PlanQuestion(id="postcodes", question=f"Which two or three exact postcodes in {location} should we compare?", why_it_matters="Crime, planning, and flood checks require exact postcode coordinates."))

    if request.budget is None:
        questions.append(PlanQuestion(id="budget", question="What is your purchase or monthly housing budget?", why_it_matters="A budget lets the planner distinguish viable options from interesting but unaffordable ones."))
    if not request.priorities:
        questions.append(PlanQuestion(id="priorities", question="Which matter most: work sponsorship, study, schools, housing cost, crime, planning, or flood risk?", why_it_matters="Priorities determine tradeoffs; there is no universally best relocation area."))
    if request.moving_date is None:
        questions.append(PlanQuestion(id="date", question="When do you want to move?", why_it_matters="A target date turns checks into an ordered action plan."))

    evidence_ids = [item.id for item in evidence if item.kind != "unknown"]
    summary = (
        f"This first-pass plan found {len(scenarios)} evidence-backed postal-district option{'s' if len(scenarios) != 1 else ''} for {location}. "
        "They are starting points for comparison, not a declaration of the best place to live."
        if location
        else "The goal is saved, but a target location is needed before VeriFinder can match public records."
    )
    steps = [
        PlanStep(position=1, title="Complete the decision brief", description="Answer the open questions so affordability and tradeoffs can be judged.", status="needs_input" if questions else "ready"),
        PlanStep(position=2, title="Shortlist locations", description="Compare the evidence-backed postal districts and keep two or three candidates.", status="ready" if scenarios else "needs_input", evidence_ids=[item for item in evidence_ids if item.startswith("property-")]),
        PlanStep(position=3, title="Run exact area checks", description="Check crime, planning designations, and flood warnings for exact postcodes; avoid inferring neighbourhood safety from a town-wide label.", status="later"),
        PlanStep(position=4, title="Verify the critical institution", description="Open the legal company, sponsor, study-provider, qualification, school, food, or property record that the decision depends on.", status="later", evidence_ids=[item for item in evidence_ids if item in {"worker-sponsors", "student-sponsors", "schools"}]),
        PlanStep(position=5, title="Re-check before committing", description="Refresh time-sensitive records immediately before applying, paying a deposit, signing, or moving.", status="later"),
    ]
    settings = get_settings()
    reasoner = GeminiReasoner(settings.gemini_api_key, settings.gemini_model)
    refinement = await reasoner.refine_plan(goal=request.goal, deterministic_summary=summary, evidence=evidence)
    if refinement:
        summary = refinement.summary
        evidence.extend(refinement.inferences)
    limitations = [
        "The planner combines public-data evidence; it does not replace immigration, legal, financial, educational, or property advice.",
        "HM Land Registry evidence is limited to the imported 2025–2026 Price Paid snapshot for England and Wales.",
        "Counts show dataset presence, not quality, availability, eligibility, or the probability of a successful outcome.",
    ]
    response = DecisionPlanResponse(
        id=plan_id,
        title=title,
        goal=request.goal,
        location=location,
        summary=summary,
        status=status,
        questions=questions,
        scenarios=scenarios,
        evidence=evidence,
        steps=steps,
        limitations=limitations,
        ai_mode="gemini" if refinement else "deterministic",
        created_at=created_at,
    )
    return response
