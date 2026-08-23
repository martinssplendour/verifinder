from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import OfsProviderRecord, StudentSponsorRecord
from app.schemas import AskInterpretation, AskResult
from app.services.study_lookup import latest_ofs_context, latest_student_sponsor_context, source_attribution as study_source

from .shared import _fact


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
