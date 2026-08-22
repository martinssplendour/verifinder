import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base, ReadOnlySessionError
from app.models import DataSource
from app.schemas import AskRequest, PlanRequest
from app.services.decision_intelligence import (
    answer_question,
    build_plan,
    deterministic_interpretation,
)
from app.services.gemini_reasoning import _output_text
from test_area_property import data_session
from test_sponsor_lookup import sponsor_session


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
