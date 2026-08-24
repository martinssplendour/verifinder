import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base, ReadOnlySessionError
from app.models import DataSource, SponsorRecord
from app.schemas import AskInterpretation, AskRequest, PlanRequest
from app.services.decision_intelligence import (
    answer_question,
    build_plan,
    contextual_interpretation,
    deterministic_interpretation,
)
from app.services.decision_intelligence.interpretation import (
    canonical_industry,
    canonical_route,
    fallback_response_style,
)
from app.services.gemini_reasoning import GeminiReasoner, _output_text
from test_area_property import data_session
from test_sponsor_lookup import sponsor_session


@pytest.fixture(autouse=True)
def deterministic_reasoner(monkeypatch: pytest.MonkeyPatch):
    """Hold the model out of these tests.

    They assert VeriFinder's own query, review and presentation logic. A live
    Gemini call would make them slow, billable and non-reproducible, and an
    unconfigured reasoner is the exact fallback path the service already takes.
    """
    monkeypatch.setattr(GeminiReasoner, "configured", property(lambda self: False))


def test_sponsorship_question_becomes_controlled_location_query():
    query = deterministic_interpretation(
        AskRequest(question="Top 10 companies to get sponsorship in London", limit=20)
    )
    assert query.intent == "sponsor_discovery"
    assert query.location == "London"
    assert query.limit == 10
    assert query.subject is None
    assert "not employers promising" in query.assumptions[0]


def test_technology_is_an_explicit_inference_filter():
    query = deterministic_interpretation(
        AskRequest(question="Show me technology companies with sponsorship", limit=10)
    )
    assert query.intent == "sponsor_discovery"
    assert query.industry == "technology"
    assert any("organisation-name" in item for item in query.assumptions)


def test_job_question_is_not_misrepresented_as_verified_vacancies():
    query = deterministic_interpretation(
        AskRequest(question="Top 10 tech jobs in Sheffield", limit=10)
    )
    assert query.intent == "job_search"
    assert query.location == "Sheffield"
    assert query.industry == "technology"

    # The register is the closest verifiable evidence, so a jobs question is
    # answered from it - but every record is labelled a sponsor, never a vacancy.
    response = asyncio.run(
        answer_question(
            sponsor_session(),
            AskRequest(question="Top 10 jobs in London", limit=10),
        )
    )
    assert response.total == 1
    assert response.results[0].title == "Northstar Labs Ltd"
    assert response.results[0].result_type == "worker_sponsor"
    assert response.results[0].subtitle == "Licensed worker sponsor"
    assert "licensed" in response.headline.lower()
    assert "vacanc" not in response.headline.lower()
    assert any("live jobs or vacancies feed" in item for item in response.limitations)
    assert any("not vacancies" in item for item in response.limitations)
    assert response.suggested_questions == []


def test_jobs_question_without_matches_offers_a_way_forward():
    response = asyncio.run(
        answer_question(
            sponsor_session(),
            AskRequest(question="Top 10 hospitality jobs in Aberdeen", limit=10),
        )
    )
    assert response.results == []
    assert response.suggested_questions == [
        "Show me hospitality organisations with worker sponsorship in Aberdeen",
        "Find regulated hospitality qualifications",
    ]


def test_ask_returns_sponsor_records_with_receipts_and_no_hiring_claim():
    session = sponsor_session()
    response = asyncio.run(
        answer_question(
            session,
            AskRequest(question="Top 5 companies with sponsorship in London", limit=10),
        )
    )
    assert response.total == 1
    assert response.results[0].title == "Northstar Labs Ltd"
    assert response.results[0].source.organisation == "UK Visas and Immigration"
    assert any("not a prediction" in item for item in response.limitations)


def test_follow_up_inherits_prior_query_and_result_context():
    session = sponsor_session()
    first = asyncio.run(
        answer_question(
            session,
            AskRequest(question="Top 5 companies with sponsorship in London", limit=10),
        )
    )
    follow_up = AskRequest(
        question="Which of those are in Leeds?",
        limit=10,
        conversation=[
            {
                "question": first.question,
                "headline": first.headline,
                "summary": first.summary,
                "interpretation": first.interpretation,
                "results": first.results,
            }
        ],
    )
    query = contextual_interpretation(follow_up)
    assert query.intent == "sponsor_discovery"
    assert query.location == "Leeds"
    assert any("previous question" in item for item in query.assumptions)


def test_explicit_follow_up_intent_keeps_missing_location_and_industry_filters():
    first = asyncio.run(
        answer_question(
            sponsor_session(),
            AskRequest(question="Top 5 technology jobs in Sheffield", limit=10),
        )
    )
    follow_up = AskRequest(
        question="Which of those have worker sponsorship?",
        limit=10,
        conversation=[
            {
                "question": first.question,
                "headline": first.headline,
                "summary": first.summary,
                "interpretation": first.interpretation,
                "results": first.results,
            }
        ],
    )
    query = contextual_interpretation(follow_up)
    assert query.intent == "sponsor_discovery"
    assert query.location == "Sheffield"
    assert query.industry == "technology"
    assert query.limit == 5


def test_relocation_plan_uses_recent_sales_without_persistence():
    session = data_session()
    response = asyncio.run(
        build_plan(
            session,
            PlanRequest(
                goal="Help me compare relocation options around London",
                location="London",
                budget=525_000,
                priorities=["Housing cost"],
            ),
        )
    )
    assert response.scenarios
    assert response.scenarios[0].location == "N1"
    assert any(item.id == "property-1" and "2 sales" in item.detail for item in response.evidence)
    assert not session.new
    assert not session.dirty


def test_read_only_session_guard_rejects_a_flush():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.info["read_only"] = True
    session.add(
        DataSource(
            id="must-not-write",
            organisation="Example",
            name="Example",
            source_type="API",
            official_url="https://example.test",
            country="GB",
        )
    )
    with pytest.raises(ReadOnlySessionError):
        session.flush()


def test_gemini_output_text_is_extracted_from_candidate_parts():
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"intent":"general"}'}],
                },
            }
        ]
    }
    assert _output_text(payload) == '{"intent":"general"}'


def test_unstated_count_returns_a_short_list():
    query = deterministic_interpretation(
        AskRequest(question="Show me technology companies with sponsorship in Leeds", limit=20)
    )
    assert query.limit == 5


def test_a_named_count_is_honoured_whether_spelled_or_written():
    spelled = deterministic_interpretation(
        AskRequest(question="top ten tech companies in Swinton", limit=20)
    )
    digits = deterministic_interpretation(
        AskRequest(question="Top 10 tech companies in Swinton", limit=20)
    )
    assert spelled.limit == 10
    assert digits.limit == 10


def test_a_named_count_never_exceeds_the_caller_limit():
    query = deterministic_interpretation(
        AskRequest(question="top twenty sponsors in Leeds", limit=6)
    )
    assert query.limit == 6


def test_a_list_request_returns_records_without_prose():
    response = asyncio.run(
        answer_question(
            sponsor_session(),
            AskRequest(question="top ten companies with sponsorship in London", limit=10),
        )
    )
    assert response.results[0].title == "Northstar Labs Ltd"
    assert response.summary == ""
    assert response.headline == "1 licensed worker sponsor in London"


def test_a_phrased_question_still_gets_an_answer_in_words():
    response = asyncio.run(
        answer_question(
            sponsor_session(),
            AskRequest(question="Which companies have worker sponsorship in London?", limit=10),
        )
    )
    assert response.results
    assert response.summary


def test_a_named_count_stays_a_list_even_when_punctuated_as_a_question():
    # "top ten ... ?" is a request for records, not something to explain.
    assert fallback_response_style("top ten tech companies in Swinton?") == "list"
    assert fallback_response_style("any tech sponsors in Leeds?") == "list"


def test_fallback_style_recognises_asks_that_do_not_open_with_a_question_word():
    assert fallback_response_style("tell me if Acme Ltd is licensed") == "answer"
    assert fallback_response_style("explain why this postcode is flagged") == "answer"
    assert fallback_response_style("is Acme Ltd licensed") == "answer"


def test_response_style_from_the_model_decides_whether_prose_is_written(monkeypatch: pytest.MonkeyPatch):
    async def interpret(self, question, requested_limit, conversation=None):
        # Phrased as a bare list request, but the user wanted it explained.
        return AskInterpretation(
            intent="sponsor_discovery",
            location="London",
            response_style="answer",
            limit=5,
        )

    monkeypatch.setattr(GeminiReasoner, "interpret_question", interpret)
    response = asyncio.run(
        answer_question(
            sponsor_session(),
            AskRequest(question="sponsors in London", limit=10),
        )
    )
    assert response.results
    assert response.summary

def test_industry_wording_from_the_model_is_mapped_before_it_reaches_the_filter():
    # "Tech" used to match no industry term, so the filter was dropped in silence
    # and the answer was every sponsor in the town, alphabetically.
    assert canonical_industry("Tech") == "technology"
    assert canonical_industry("Technology") == "technology"
    assert canonical_industry("software development") == "technology"
    assert canonical_industry("Financial Services") == "financial services"
    assert canonical_industry("retail") is None
    assert canonical_route("skilled worker") == "Skilled Worker"
    assert canonical_route("scale up") == "Scale-up"


def test_a_free_text_industry_still_filters_the_sponsor_list(monkeypatch: pytest.MonkeyPatch):
    async def interpret(self, question, requested_limit, conversation=None):
        return AskInterpretation(
            intent="sponsor_discovery",
            location="London",
            industry="Tech",
            response_style="list",
            limit=10,
        )

    monkeypatch.setattr(GeminiReasoner, "interpret_question", interpret)
    session = sponsor_session()
    session.add_all(
        [
            SponsorRecord(
                dataset_version_id="version-1",
                source_record_key="f" * 64,
                organisation_name="Aardvark Catering Ltd",
                normalised_name="aardvark catering limited",
                town_city="London",
                county=None,
                sponsor_rating="Worker (A rating)",
                routes=["Skilled Worker"],
                active=True,
                raw_record=[],
            ),
            SponsorRecord(
                dataset_version_id="version-1",
                source_record_key="g" * 64,
                organisation_name="Zenith Software Systems Ltd",
                normalised_name="zenith software systems limited",
                town_city="London",
                county=None,
                sponsor_rating="Worker (A rating)",
                routes=["Skilled Worker"],
                active=True,
                raw_record=[],
            ),
        ]
    )
    session.commit()

    response = asyncio.run(
        answer_question(session, AskRequest(question="Top 10 tech companies in London", limit=10))
    )
    # The catering firm sorts first alphabetically and the software firm last, so
    # returning only the software firm proves the industry filter actually ran.
    assert [result.title for result in response.results] == ["Zenith Software Systems Ltd"]
    assert response.interpretation.industry == "technology"


def test_an_unfilterable_industry_is_reported_rather_than_ignored(monkeypatch: pytest.MonkeyPatch):
    async def interpret(self, question, requested_limit, conversation=None):
        return AskInterpretation(
            intent="sponsor_discovery",
            location="London",
            industry="aerospace",
            response_style="list",
            limit=10,
        )

    monkeypatch.setattr(GeminiReasoner, "interpret_question", interpret)
    response = asyncio.run(
        answer_question(sponsor_session(), AskRequest(question="Top 10 aerospace firms in London", limit=10))
    )
    assert response.interpretation.industry is None
    assert any("aerospace" in item for item in response.interpretation.assumptions)
