from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import AskRequest, AskResponse
from app.services.gemini_reasoning import GeminiReasoner

from .area_results import _area_results
from .food_results import _food_results
from .interpretation import FOLLOW_UP_RE, contextual_interpretation
from .property_results import _property_results
from .qualification_results import _qualification_results
from .sponsor_results import _sponsor_results
from .study_results import _study_results


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
