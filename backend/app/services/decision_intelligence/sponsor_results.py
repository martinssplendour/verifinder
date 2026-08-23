from __future__ import annotations

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models import SponsorRecord
from app.schemas import AskInterpretation, AskResult
from app.services.sponsor_lookup import latest_sponsor_context, rating_label, source_attribution as sponsor_source

from .interpretation import INDUSTRY_NAME_TERMS
from .shared import _fact


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
