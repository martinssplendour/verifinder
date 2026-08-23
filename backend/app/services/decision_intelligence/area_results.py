from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas import AskInterpretation, AskResult
from app.services.area_lookup import get_area_check
from app.services.dataset_utils import normalise_postcode

from .interpretation import POSTCODE_RE
from .shared import _fact


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
