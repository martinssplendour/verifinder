from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_read_db
from app.models import IngestionRun, RunStatus
from app.services.food_lookup import latest_food_context
from app.services.property_lookup import latest_property_context
from app.services.qualification_lookup import (
    latest_qualification_context,
    latest_qualification_unit_context,
    latest_welsh_qualification_context,
)
from app.services.school_lookup import latest_ofsted_context, latest_school_context
from app.services.sponsor_lookup import latest_sponsor_context
from app.services.study_lookup import latest_ofs_context, latest_student_sponsor_context
from app.services.area_lookup import latest_postcode_context


router = APIRouter()
settings = get_settings()


@router.get("/admin/summary")
async def admin_summary(session: Session = Depends(get_read_db)):
    sponsor_context = latest_sponsor_context(session)
    qualification_context = latest_qualification_context(session)
    welsh_qualification_context = latest_welsh_qualification_context(session)
    qualification_unit_context = latest_qualification_unit_context(session)
    student_sponsor_context = latest_student_sponsor_context(session)
    ofs_context = latest_ofs_context(session)
    food_context = latest_food_context(session)
    postcode_context = latest_postcode_context(session)
    property_context = latest_property_context(session)
    school_context = latest_school_context(session)
    ofsted_context = latest_ofsted_context(session)
    runs = list(session.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(20)))
    failed_imports = session.scalar(
        select(func.count()).select_from(IngestionRun).where(IngestionRun.status == RunStatus.FAILED)
    ) or 0
    healthy_sources = sum(
        (
            int(bool(settings.companies_house_api_key)),
            int(bool(settings.epc_api_key)),
            int(bool(sponsor_context)),
            int(bool(qualification_context)),
            int(bool(welsh_qualification_context)),
            int(bool(qualification_unit_context)),
            int(bool(student_sponsor_context)),
            int(bool(ofs_context)),
            int(bool(food_context)),
            int(bool(postcode_context)),
            int(bool(property_context)),
            int(bool(school_context)),
            int(bool(ofsted_context)),
            1,
            1,
            1,
        )
    )
    return {
        "data_mode": "live" if settings.companies_house_api_key else "unavailable",
        "sources": {"total": 16, "healthy": healthy_sources, "attention": 16 - healthy_sources},
        "ingestion_runs": [
            {
                "id": run.id,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "status": run.status.value,
                "records_processed": run.records_processed,
                "records_added": run.records_added,
                "records_removed": run.records_removed,
                "records_changed": run.records_changed,
                "error_message": run.error_message,
            }
            for run in runs
        ],
        "unresolved_matches": 0,
        "failed_imports": failed_imports,
        "message": (
            "Official datasets are connected and independently versioned."
            if sponsor_context
            and qualification_context
            and welsh_qualification_context
            and qualification_unit_context
            and student_sponsor_context
            and ofs_context
            and food_context
            and postcode_context
            and property_context
            and school_context
            and ofsted_context
            else "One or more public datasets still need an initial import."
        ),
        "generated_at": datetime.now(timezone.utc),
    }
