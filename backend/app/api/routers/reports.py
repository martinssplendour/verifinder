import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routers.account_billing import _entitlement_error
from app.billing_database import get_billing_db
from app.billing_models import SavedReport
from app.config import get_settings
from app.schemas import (
    SavedReportCreate,
    SavedReportReady,
    SavedReportView,
    SignedDownloadResponse,
)
from app.services.auth import RequestIdentity, identity_dependency, require_authenticated
from app.services.entitlements import check_report_entitlement
from app.services.reports import (
    ReportStorageError,
    build_plan_pdf,
    delete_pdf,
    list_saved_reports,
    report_storage_configured,
    signed_download_url,
    upload_pdf,
)


router = APIRouter()
settings = get_settings()


def _saved_report_view(report: SavedReport) -> SavedReportView:
    return SavedReportView(
        id=report.id,
        source_report_id=report.source_report_id,
        report_type=report.report_type,
        title=report.title,
        mime_type=report.mime_type,
        size_bytes=report.size_bytes,
        provenance_count=report.provenance_count,
        created_at=report.created_at,
    )


@router.post("/reports", response_model=SavedReportReady)
async def save_report(
    request: SavedReportCreate,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    result = check_report_entitlement(billing_session, identity.subject_id)
    if not result.allowed:
        raise _entitlement_error(result)
    if not report_storage_configured():
        raise HTTPException(status_code=503, detail="Private report storage is not configured.")
    existing = billing_session.scalar(
        select(SavedReport).where(
            SavedReport.subject_id == identity.subject_id,
            SavedReport.source_report_id == request.plan.id,
            SavedReport.status == "ready",
        )
    )
    try:
        if existing:
            url, expires_at = await signed_download_url(existing.storage_path)
            return SavedReportReady(report=_saved_report_view(existing), download_url=url, expires_at=expires_at)

        report_id = str(uuid.uuid4())
        storage_path = f"{identity.subject_id}/{datetime.now(timezone.utc):%Y/%m}/{report_id}.pdf"
        pdf = await asyncio.to_thread(build_plan_pdf, request.plan)
        await upload_pdf(storage_path, pdf)
        report = SavedReport(
            id=report_id,
            subject_id=identity.subject_id,
            source_report_id=request.plan.id,
            title=request.plan.title,
            storage_bucket=settings.report_storage_bucket,
            storage_path=storage_path,
            size_bytes=len(pdf),
            provenance_count=sum(1 for item in request.plan.evidence if item.source is not None),
        )
        billing_session.add(report)
        try:
            billing_session.commit()
        except Exception:
            billing_session.rollback()
            await delete_pdf(storage_path)
            raise
        url, expires_at = await signed_download_url(storage_path)
    except ReportStorageError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return SavedReportReady(report=_saved_report_view(report), download_url=url, expires_at=expires_at)


@router.get("/reports", response_model=list[SavedReportView])
async def get_saved_reports(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    return [_saved_report_view(report) for report in list_saved_reports(billing_session, identity.subject_id)]


@router.post("/reports/{report_id}/download", response_model=SignedDownloadResponse)
async def get_report_download(
    report_id: str,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    report = billing_session.get(SavedReport, report_id)
    if report is None or report.subject_id != identity.subject_id or report.status != "ready":
        raise HTTPException(status_code=404, detail="Saved report not found.")
    try:
        url, expires_at = await signed_download_url(report.storage_path)
    except ReportStorageError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return SignedDownloadResponse(url=url, expires_at=expires_at)


@router.delete("/reports/{report_id}")
async def remove_saved_report(
    report_id: str,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    report = billing_session.get(SavedReport, report_id)
    if report is None or report.subject_id != identity.subject_id:
        raise HTTPException(status_code=404, detail="Saved report not found.")
    try:
        await delete_pdf(report.storage_path)
    except ReportStorageError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    billing_session.delete(report)
    billing_session.commit()
    return {"status": "removed"}
