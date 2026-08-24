from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import AskInterpretation, AskRequest, AskResponse, AskResult
from app.services.gemini_reasoning import GeminiReasoner

from .area_results import _area_results
from .food_results import _food_results
from .interpretation import FOLLOW_UP_RE, contextual_interpretation
from .property_results import _property_results
from .qualification_results import _qualification_results
from .sponsor_results import _sponsor_results
from .study_results import _study_results


# A jobs question cannot be answered from a vacancies feed VeriFinder does not
# hold, but the licensed-sponsor register is the closest verifiable evidence, so
# the question is served from there and the records are labelled as sponsors.
JOB_SEARCH_LIMITATIONS = [
    "VeriFinder does not currently ingest a live jobs or vacancies feed, so it cannot verify or rank current openings.",
    "These are licensed sponsors, not vacancies. A sponsor-licence record shows that an organisation is licensed; it does not show that it is hiring or that a particular role is eligible for sponsorship.",
]

GENERAL_LIMITATION = (
    "Ask VeriFinder currently answers questions about sponsors, qualifications, study providers, "
    "food hygiene, property sales, and postcode area checks."
)


async def _execute(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str], str]:
    """Run the controlled query form against the source it names."""
    if query.intent in {"job_search", "sponsor_discovery"}:
        results, limitations = _sponsor_results(session, query)
        if query.intent == "job_search":
            limitations = [*JOB_SEARCH_LIMITATIONS, *limitations]
        return results, limitations, "licensed worker sponsor"
    if query.intent == "qualification_search":
        results, limitations = _qualification_results(session, query)
        return results, limitations, "regulated qualification"
    if query.intent == "study_provider_search":
        results, limitations = _study_results(session, query)
        return results, limitations, "study provider"
    if query.intent == "food_search":
        results, limitations = _food_results(session, query)
        return results, limitations, "food hygiene record"
    if query.intent == "property_search":
        results, limitations = _property_results(session, query)
        return results, limitations, "recent property sale"
    if query.intent == "area_check":
        results, limitations = await _area_results(session, query)
        return results, limitations, "area check"
    return [], [GENERAL_LIMITATION], "public-data result"


def _headline(query: AskInterpretation, results: list[AskResult], label: str) -> tuple[str, str]:
    place = f" in {query.location}" if query.location else ""
    if query.intent == "general":
        return (
            "That question is outside the connected evidence",
            "I kept your question in the conversation, but the connected records cannot answer it yet. "
            "Try asking about sponsors, qualifications, study providers, food hygiene, property sales, or a postcode area check.",
        )
    if query.intent == "job_search":
        industry = f"{query.industry} " if query.industry else ""
        if results:
            return (
                f"{len(results)} licensed {industry}sponsor{'' if len(results) == 1 else 's'}{place}",
                "VeriFinder has no live vacancies feed, so it cannot rank current openings. These organisations are on "
                f"the Home Office worker sponsor register and match your filters{place} - a licence means they are "
                "able to sponsor a worker, not that they are hiring.",
            )
        return (
            "No licensed sponsors matched that search",
            "VeriFinder has no live vacancies feed, so it answers jobs questions from the Home Office worker sponsor "
            "register instead. No organisation on the current register matched those filters.",
        )
    return (
        f"{len(results)} {label}{'' if len(results) == 1 else 's'}{place}",
        "These are the strongest matches under the interpreted filters. Open a result to inspect its official source and full record."
        if results
        else "No records matched the interpreted filters. Review the interpretation or make the question more specific.",
    )


def _suggested_questions(query: AskInterpretation, results: list[AskResult]) -> list[str]:
    """Offer a way forward only when the answer came back empty."""
    if results or query.intent not in {"job_search", "general"}:
        return []
    industry = f"{query.industry} " if query.industry else ""
    place = f" in {query.location}" if query.location else ""
    suggestions = [f"Show me {industry}organisations with worker sponsorship{place}".replace("  ", " ")]
    if query.industry:
        suggestions.append(f"Find regulated {query.industry} qualifications")
    return suggestions


async def answer_question(session: Session, request: AskRequest) -> AskResponse:
    settings = get_settings()
    deterministic = contextual_interpretation(request)
    reasoner = GeminiReasoner(settings.gemini_api_key, settings.gemini_model)
    # Follow-up resolution stays a deterministic guardrail: an LLM interpretation
    # must not erase filters inherited from the previous turn.
    guarded_context = bool(request.conversation and FOLLOW_UP_RE.search(request.question))
    interpreted = None
    if not guarded_context:
        interpreted = await reasoner.interpret_question(
            request.question,
            request.limit,
            request.conversation,
        )
    query = deterministic if guarded_context else (interpreted or deterministic)
    interpreted_used = interpreted is not None and query is interpreted
    query.limit = min(query.limit, request.limit)

    results, limitations, label = await _execute(session, query)

    # One revision only. Gemini may judge the records inadequate and hand back a
    # different query form, but VeriFinder runs it and keeps the revision only
    # when it actually returns more, so a poor revision cannot make things worse.
    review = await reasoner.review_results(
        question=request.question,
        interpretation=query,
        results=results,
        requested_limit=request.limit,
    )
    revised = False
    if review and not review.answers_question and review.revision:
        candidate = review.revision
        candidate.limit = min(candidate.limit, request.limit)
        retry_results, retry_limitations, retry_label = await _execute(session, candidate)
        if len(retry_results) > len(results):
            query, results, limitations, label = candidate, retry_results, retry_limitations, retry_label
            revised = True

    if revised and review and review.assessment:
        query.assumptions = [
            *query.assumptions,
            f"The first query was re-run after review: {review.assessment}",
        ]
    headline, deterministic_summary = _headline(query, results, label)
    synthesized = None
    if query.intent != "general":
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
        suggested_questions=_suggested_questions(query, results),
        ai_mode="gemini" if interpreted_used or synthesized or revised else "deterministic",
        generated_at=datetime.now(timezone.utc),
    )
