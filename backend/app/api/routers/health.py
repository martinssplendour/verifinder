from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing_database import get_billing_db
from app.billing_models import OperationCheck, SchedulerLease
from app.config import get_settings
from app.database import get_read_db
from app.schemas import OperationCheckView
from app.services.area_lookup import latest_postcode_context
from app.services.food_lookup import latest_food_context
from app.services.notifications import email_configured
from app.services.operations import JOB_NAME
from app.services.property_lookup import latest_property_context
from app.services.qualification_lookup import (
    latest_qualification_context,
    latest_qualification_unit_context,
    latest_welsh_qualification_context,
)
from app.services.reports import report_storage_configured
from app.services.school_lookup import latest_ofsted_context, latest_school_context
from app.services.sponsor_lookup import latest_sponsor_context
from app.services.stripe_billing import billing_configured
from app.services.study_lookup import latest_ofs_context, latest_student_sponsor_context


router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health(
    session: Session = Depends(get_read_db),
    billing_session: Session = Depends(get_billing_db),
) -> dict:
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
    transaction_database = billing_session.get_bind().dialect.name
    return {
        "status": "ok",
        "public_data_store": session.get_bind().dialect.name,
        "transaction_database": transaction_database,
        "companies_house": "configured" if settings.companies_house_api_key else "not_configured",
        "epc": "configured" if settings.epc_api_key else "not_configured",
        "gemini": "configured" if settings.gemini_api_key else "not_configured",
        "supabase_auth": "configured" if settings.supabase_url and settings.supabase_publishable_key else "not_configured",
        "stripe": "configured" if billing_configured() else "not_configured",
        "report_storage": "configured" if report_storage_configured() else "not_configured",
        "email_notifications": "configured" if email_configured() else "not_configured",
        "sponsor_register": "healthy" if sponsor_context else "not_ingested",
        "sponsor_dataset_version": sponsor_context.version.version_identifier if sponsor_context else None,
        "qualifications": "healthy" if qualification_context else "not_ingested",
        "qualification_dataset_version": qualification_context[1].version_identifier if qualification_context else None,
        "welsh_qualifications": "healthy" if welsh_qualification_context else "not_ingested",
        "qualification_units": "healthy" if qualification_unit_context else "not_ingested",
        "student_sponsors": "healthy" if student_sponsor_context else "not_ingested",
        "ofs_register": "healthy" if ofs_context else "not_ingested",
        "food_hygiene": "healthy" if food_context else "not_ingested",
        "food_dataset_version": food_context[1].version_identifier if food_context else None,
        "postcodes": "healthy" if postcode_context else "not_ingested",
        "postcode_dataset_version": postcode_context[1].version_identifier if postcode_context else None,
        "property_sales": "healthy" if property_context else "not_ingested",
        "property_dataset_version": property_context[1].version_identifier if property_context else None,
        "gias_schools": "healthy" if school_context else "not_ingested",
        "gias_dataset_version": school_context[1].version_identifier if school_context else None,
        "ofsted_inspections": "healthy" if ofsted_context else "not_ingested",
        "ofsted_dataset_version": ofsted_context[1].version_identifier if ofsted_context else None,
        "police_uk": "configured",
        "planning_data": "configured",
        "flood_monitoring": "configured",
    }


@router.get("/operations/status")
async def operations_status(billing_session: Session = Depends(get_billing_db)) -> dict:
    recent = list(
        billing_session.scalars(select(OperationCheck).order_by(OperationCheck.checked_at.desc()).limit(100))
    )
    latest: dict[str, OperationCheckView] = {}
    for check in recent:
        if check.check_name not in latest:
            latest[check.check_name] = OperationCheckView(
                check_name=check.check_name,
                status=check.status,
                detail=check.detail,
                checked_at=check.checked_at,
            )
    lease = billing_session.get(SchedulerLease, JOB_NAME)
    locked_until = lease.locked_until if lease else None
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    scheduler_stale = bool(
        lease
        and lease.last_status == "running"
        and locked_until
        and locked_until < datetime.now(timezone.utc)
    )
    return {
        "status": "ok" if latest and not scheduler_stale and all(item.status != "failed" for item in latest.values()) else "attention",
        "scheduler": {
            "enabled": settings.scheduler_enabled,
            "interval_minutes": settings.scheduler_interval_minutes,
            "last_started_at": lease.last_started_at if lease else None,
            "last_finished_at": lease.last_finished_at if lease else None,
            "last_status": "stale" if scheduler_stale else (lease.last_status if lease else "not_run"),
            "phase": (lease.last_detail or {}).get("phase") if lease else None,
            "detail": lease.last_detail if lease else None,
        },
        "checks": list(latest.values()),
    }
