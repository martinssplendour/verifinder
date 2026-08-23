from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas import AskInterpretation, AskResult
from app.services.qualification_lookup import search_qualifications

from .shared import _fact


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
