from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import SchoolRecord, SponsorRecord, StudentSponsorRecord
from app.schemas import (
    DecisionPlanResponse,
    PlanEvidence,
    PlanMetric,
    PlanQuestion,
    PlanRequest,
    PlanScenario,
    PlanStep,
)
from app.services.area_lookup import get_area_check
from app.services.gemini_reasoning import GeminiReasoner
from app.services.gias_loader import SOURCE_ID as GIAS_SOURCE_ID
from app.services.sponsor_lookup import latest_sponsor_context, source_attribution as sponsor_source
from app.services.study_lookup import latest_student_sponsor_context, source_attribution as study_source

from .interpretation import POSTCODE_RE, _location
from .property_results import _market_candidates
from .shared import _count_for_location, _latest_context, _source


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
