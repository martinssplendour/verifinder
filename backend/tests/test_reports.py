from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.billing_models import BillingBase, SavedReport
from app.schemas import DecisionPlanResponse
from app.services.reports import build_plan_pdf, list_saved_reports


def _plan() -> DecisionPlanResponse:
    return DecisionPlanResponse.model_validate(
        {
            "id": "plan-123",
            "title": "Manchester relocation plan",
            "goal": "Choose a well-evidenced place to relocate around Manchester",
            "location": "Manchester",
            "summary": "Compare housing, sponsorship and area evidence before committing.",
            "status": "draft",
            "questions": [{"id": "q1", "question": "What commute is acceptable?", "why_it_matters": "It changes the search radius."}],
            "scenarios": [{
                "id": "s1", "title": "Central Manchester", "description": "A starting scenario.",
                "location": "Manchester", "metrics": [{"label": "Recent sales", "value": "2025–2026"}],
                "strengths": ["Connected evidence"], "tradeoffs": ["Check current travel times"], "evidence_ids": ["e1"],
            }],
            "evidence": [{
                "id": "e1", "kind": "verified_fact", "title": "Recent sale coverage", "detail": "The connected snapshot covers 2025 and 2026.",
                "source": {"id": "hmlr", "organisation": "HM Land Registry", "dataset": "Price Paid Data", "official_url": "https://www.gov.uk/government/collections/price-paid-data", "health": "healthy"},
            }],
            "steps": [{"position": 1, "title": "Verify the shortlist", "description": "Open the official records.", "status": "ready", "evidence_ids": ["e1"]}],
            "limitations": ["Public records can change."],
            "ai_mode": "deterministic",
            "created_at": datetime.now(timezone.utc),
        }
    )


def test_build_plan_pdf_is_a_real_pdf_with_multiple_sections():
    pdf = build_plan_pdf(_plan())
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 3000


def test_list_saved_reports_is_scoped_to_owner_and_ready_state():
    engine = create_engine("sqlite://")
    BillingBase.metadata.create_all(engine)
    session = Session(engine)
    session.add_all([
        SavedReport(id="r1", subject_id="user-1", source_report_id="p1", title="Ready", storage_bucket="reports", storage_path="user-1/r1.pdf", size_bytes=100, provenance_count=1),
        SavedReport(id="r2", subject_id="user-1", source_report_id="p2", title="Failed", storage_bucket="reports", storage_path="user-1/r2.pdf", size_bytes=0, status="failed", provenance_count=0),
        SavedReport(id="r3", subject_id="user-2", source_report_id="p3", title="Other", storage_bucket="reports", storage_path="user-2/r3.pdf", size_bytes=100, provenance_count=1),
    ])
    session.commit()
    assert [report.id for report in list_saved_reports(session, "user-1")] == ["r1"]
