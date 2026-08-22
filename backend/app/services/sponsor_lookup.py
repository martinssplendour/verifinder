import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, RunStatus, SponsorRecord
from app.schemas import SourceAttribution, SponsorRecordView, SponsorshipSummary
from app.services.normalization import comparison_name, normalise_name
from app.services.sponsor_loader import OFFICIAL_URL, SOURCE_ID
from app.services.sponsor_matching import score_sponsor_match


@dataclass(frozen=True)
class SponsorContext:
    source: DataSource
    version: DatasetVersion


@dataclass(frozen=True)
class SponsorResolution:
    summary: SponsorshipSummary
    record: SponsorRecord | None
    context: SponsorContext | None


def latest_sponsor_context(session: Session) -> SponsorContext | None:
    version = session.scalar(
        select(DatasetVersion)
        .where(
            DatasetVersion.source_id == SOURCE_ID,
            DatasetVersion.processing_status == RunStatus.SUCCEEDED,
        )
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    )
    if version is None:
        return None
    source = session.get(DataSource, SOURCE_ID)
    if source is None:
        return None
    return SponsorContext(source=source, version=version)


def source_attribution(context: SponsorContext) -> SourceAttribution:
    return SourceAttribution(
        id=SOURCE_ID,
        organisation=context.source.organisation,
        dataset=context.source.name,
        official_url=context.source.official_url or OFFICIAL_URL,
        retrieved_at=context.version.retrieved_at,
        published_at=context.version.published_at,
        version=context.version.version_identifier,
        health=context.source.health.value,
    )


def _town_matches_address(town: str | None, address: str | None) -> bool:
    if not town or not address:
        return False
    town_value = normalise_name(town)
    address_value = normalise_name(address)
    return f" {town_value} " in f" {address_value} "


def rating_label(raw_rating: str | None) -> str | None:
    if not raw_rating:
        return None
    match = re.search(r"\(([A-Za-z]+)\s+rating\)", raw_rating, re.IGNORECASE)
    return match.group(1).upper() if match else raw_rating


def sponsor_record_view(record: SponsorRecord, context: SponsorContext) -> SponsorRecordView:
    return SponsorRecordView(
        id=record.id,
        organisation_name=record.organisation_name,
        town_city=record.town_city,
        county=record.county,
        rating=rating_label(record.sponsor_rating),
        routes=sorted(record.routes or []),
        source=source_attribution(context),
    )


def search_sponsor_records(session: Session, query: str, limit: int = 8) -> tuple[list[SponsorRecordView], SponsorContext | None]:
    context = latest_sponsor_context(session)
    if context is None:
        return [], None
    normalised_query = normalise_name(query)
    comparison_query = comparison_name(query)
    if not normalised_query:
        return [], context

    direct = list(
        session.scalars(
            select(SponsorRecord)
            .where(
                SponsorRecord.dataset_version_id == context.version.id,
                SponsorRecord.normalised_name.like(f"%{normalised_query}%"),
            )
            .limit(max(limit * 8, 40))
        )
    )
    candidates = direct
    if len(candidates) < limit:
        fuzzy_prefix = comparison_query[: max(3, min(6, len(comparison_query)))]
        if fuzzy_prefix:
            fuzzy = list(
                session.scalars(
                    select(SponsorRecord)
                    .where(
                        SponsorRecord.dataset_version_id == context.version.id,
                        SponsorRecord.normalised_name.like(f"{fuzzy_prefix[:3]}%"),
                    )
                    .limit(500)
                )
            )
            seen = {record.id for record in candidates}
            candidates.extend(record for record in fuzzy if record.id not in seen)

    whole_phrase_matches = [
        record
        for record in candidates
        if f" {normalised_query} " in f" {record.normalised_name} "
    ]
    if whole_phrase_matches:
        candidates = whole_phrase_matches

    def score(record: SponsorRecord) -> float:
        record_normalised = record.normalised_name
        record_comparison = comparison_name(record.organisation_name)
        if record_comparison == comparison_query or record_normalised == normalised_query:
            value = 1.0
        elif record_comparison.startswith(f"{comparison_query} "):
            value = 0.98
        elif record_normalised.startswith(normalised_query):
            value = 0.96
        elif normalised_query in record_normalised:
            value = 0.91
        else:
            value = SequenceMatcher(None, comparison_query, record_comparison).ratio()
        return value

    ranked = sorted(candidates, key=lambda record: (-score(record), record.organisation_name.lower()))
    filtered = [record for record in ranked if score(record) >= 0.58][:limit]
    return [sponsor_record_view(record, context) for record in filtered], context


def get_sponsor_record(session: Session, record_id: str) -> SponsorRecordView | None:
    context = latest_sponsor_context(session)
    if context is None:
        return None
    record = session.scalar(
        select(SponsorRecord).where(
            SponsorRecord.id == record_id,
            SponsorRecord.dataset_version_id == context.version.id,
        )
    )
    return sponsor_record_view(record, context) if record else None


def _possible_candidates(session: Session, version_id: str, company_name: str) -> list[SponsorRecord]:
    normalised = normalise_name(company_name)
    exact = list(
        session.scalars(
            select(SponsorRecord).where(
                SponsorRecord.dataset_version_id == version_id,
                SponsorRecord.normalised_name == normalised,
            )
        )
    )
    if exact:
        return exact
    first_token = comparison_name(company_name).split()[0] if comparison_name(company_name).split() else normalised
    return list(
        session.scalars(
            select(SponsorRecord)
            .where(
                SponsorRecord.dataset_version_id == version_id,
                SponsorRecord.normalised_name.like(f"{first_token}%"),
            )
            .limit(200)
        )
    )


def resolve_company_sponsorship(
    session: Session,
    company_name: str,
    registered_office: str | None,
) -> SponsorResolution:
    context = latest_sponsor_context(session)
    if context is None:
        return SponsorResolution(
            summary=SponsorshipSummary(
                status="data_unavailable",
                label="Sponsorship data unavailable",
                explanation="No successful sponsor-register dataset has been imported in this environment.",
            ),
            record=None,
            context=None,
        )

    attribution = source_attribution(context)
    candidates = _possible_candidates(session, context.version.id, company_name)
    if not candidates:
        return SponsorResolution(
            summary=SponsorshipSummary(
                status="no_match",
                label="No matching record found",
                explanation=(
                    "We couldn't find a matching organisation in the latest imported sponsor-register dataset. "
                    "This does not prove that the company cannot sponsor someone."
                ),
                source=attribution,
            ),
            record=None,
            context=context,
        )

    company_comparison = comparison_name(company_name)
    scored: list[tuple[float, str, SponsorRecord]] = []
    for candidate in candidates:
        exact_name = comparison_name(candidate.organisation_name) == company_comparison
        town_match = _town_matches_address(candidate.town_city, registered_office)
        if exact_name and town_match:
            scored.append((0.98, "exact_name_town", candidate))
            continue
        decision = score_sponsor_match(company_name, candidate.organisation_name)
        scored.append((decision.confidence, decision.method, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    confidence, method, best = scored[0]
    equally_strong = [item for item in scored if abs(item[0] - confidence) < 0.01]

    if method == "exact_name_town" and len(equally_strong) == 1:
        status = "match_found"
        label = "Licensed sponsor"
        explanation = (
            "Found on the latest imported UK worker sponsor register. "
            "The normalised organisation name and town match this company record."
        )
    elif confidence >= 0.78:
        status = "possible_match"
        label = "Possible sponsor-register match"
        explanation = (
            "An organisation with a similar name appears in the latest sponsor register, "
            "but the available evidence is not sufficient to confirm it is the same legal entity."
        )
    else:
        return SponsorResolution(
            summary=SponsorshipSummary(
                status="no_match",
                label="No matching record found",
                explanation=(
                    "We couldn't find a sufficiently confident organisation match in the latest imported "
                    "sponsor-register dataset. This does not prove that the company cannot sponsor someone."
                ),
                source=attribution,
            ),
            record=None,
            context=context,
        )

    return SponsorResolution(
        summary=SponsorshipSummary(
            status=status,
            label=label,
            explanation=explanation,
            routes=sorted(best.routes or []),
            rating=rating_label(best.sponsor_rating),
            match_confidence=confidence,
            match_method=method,
            source=attribution,
        ),
        record=best,
        context=context,
    )
