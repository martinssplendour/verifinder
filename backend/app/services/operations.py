from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select, text

from app.billing_database import BillingSessionLocal
from app.billing_models import OperationCheck, SchedulerLease
from app.config import get_settings
from app.database import SessionLocal
from app.models import DataSource, DatasetVersion, RunStatus
from app.services.notifications import retry_pending_alerts
from app.services.refresh import refresh_due_sources
from app.services.reports import report_storage_configured, storage_request_headers
from app.services.watchlists import scan_live_watchlists


JOB_NAME = "retention-maintenance"


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def acquire_scheduler_lease(minutes: int = 30) -> bool:
    session = BillingSessionLocal()
    now = datetime.now(timezone.utc)
    try:
        lease = session.get(SchedulerLease, JOB_NAME)
        if lease and _utc(lease.locked_until) and _utc(lease.locked_until) > now:
            return False
        if lease is None:
            lease = SchedulerLease(job_name=JOB_NAME)
            session.add(lease)
        lease.locked_until = now + timedelta(minutes=minutes)
        lease.last_started_at = now
        lease.last_status = "running"
        lease.last_detail = {"phase": "starting"}
        session.commit()
        return True
    finally:
        session.close()


def finish_scheduler_lease(status: str, detail: dict) -> None:
    session = BillingSessionLocal()
    try:
        lease = session.get(SchedulerLease, JOB_NAME)
        if lease:
            lease.locked_until = None
            lease.last_finished_at = datetime.now(timezone.utc)
            lease.last_status = status
            lease.last_detail = _json_safe(detail)
            session.commit()
    finally:
        session.close()


def update_scheduler_progress(phase: str, *, source: dict | None = None, minutes: int = 30) -> None:
    """Persist a heartbeat so a long public-data refresh is observable and keeps its lease."""
    session = BillingSessionLocal()
    try:
        lease = session.get(SchedulerLease, JOB_NAME)
        if lease:
            detail = {"phase": phase, "updated_at": datetime.now(timezone.utc).isoformat()}
            if source is not None:
                detail["source"] = _json_safe(source)
            lease.last_detail = detail
            lease.locked_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
            session.commit()
    finally:
        session.close()


def _record_check(session, name: str, status: str, detail: dict) -> OperationCheck:
    check = OperationCheck(check_name=name, status=status, detail=detail)
    session.add(check)
    session.commit()
    return check


def run_operational_checks() -> list[OperationCheck]:
    settings = get_settings()
    billing = BillingSessionLocal()
    public = SessionLocal()
    checks: list[OperationCheck] = []
    try:
        try:
            billing.execute(text("select 1"))
            checks.append(_record_check(billing, "transaction_database", "ok", {"dialect": billing.get_bind().dialect.name}))
        except Exception as error:
            billing.rollback()
            checks.append(_record_check(billing, "transaction_database", "failed", {"error": str(error)[:300]}))

        try:
            sources = public.scalar(select(func.count()).select_from(DataSource)) or 0
            successful_versions = public.scalar(
                select(func.count()).select_from(DatasetVersion).where(DatasetVersion.processing_status == RunStatus.SUCCEEDED)
            ) or 0
            status = "ok" if sources and successful_versions else "attention"
            checks.append(_record_check(billing, "public_data", status, {"sources": sources, "successful_versions": successful_versions}))
        except Exception as error:
            checks.append(_record_check(billing, "public_data", "failed", {"error": str(error)[:300]}))

        if report_storage_configured():
            try:
                response = httpx.get(
                    f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket/{settings.report_storage_bucket}",
                    headers=storage_request_headers(),
                    timeout=10.0,
                )
                storage_status = "ok" if response.status_code == 200 else "failed"
                checks.append(_record_check(billing, "report_storage", storage_status, {"private_bucket_reachable": response.status_code == 200}))
            except httpx.HTTPError as error:
                checks.append(_record_check(billing, "report_storage", "failed", {"error": str(error)[:300]}))
        else:
            checks.append(_record_check(billing, "report_storage", "not_configured", {}))

        backup_detail = {
            "provider": "Supabase managed database backups",
            "verified_at": settings.supabase_backups_verified_at,
            "public_data_recoverable_from_snapshot": bool(settings.database_snapshot_url),
        }
        backup_status = "ok" if settings.supabase_backups_verified_at and settings.database_snapshot_url else "attention"
        checks.append(_record_check(billing, "backup_readiness", backup_status, backup_detail))
        return checks
    finally:
        public.close()
        billing.close()


async def run_maintenance_cycle() -> dict:
    if not acquire_scheduler_lease():
        return {"status": "skipped", "reason": "lease_held"}
    detail: dict = {}
    status = "ok"
    try:
        update_scheduler_progress("operational_checks")
        checks = await asyncio.to_thread(run_operational_checks)
        detail["checks"] = {check.check_name: check.status for check in checks}
        if any(check.status == "failed" for check in checks):
            status = "attention"

        update_scheduler_progress("public_data_refresh")

        def record_refresh_progress(result: dict) -> None:
            update_scheduler_progress("public_data_refresh", source=result)

        detail["refresh"] = await asyncio.to_thread(refresh_due_sources, on_progress=record_refresh_progress)
        if any(item.get("status") == "failed" for item in detail["refresh"]):
            status = "attention"

        update_scheduler_progress("watchlists")
        public = SessionLocal()
        billing = BillingSessionLocal()
        try:
            live_alerts = await scan_live_watchlists(public, billing)
            detail["live_alerts"] = len(live_alerts)
            detail["email_delivery"] = await asyncio.to_thread(retry_pending_alerts, billing)
        finally:
            public.close()
            billing.close()
    except Exception as error:
        status = "failed"
        detail["error"] = str(error)[:500]
    finally:
        finish_scheduler_lease(status, detail)
    return {"status": status, **detail}


async def run_bounded_maintenance_cycle(timeout_seconds: float) -> dict:
    try:
        return await asyncio.wait_for(run_maintenance_cycle(), timeout=timeout_seconds)
    except TimeoutError:
        detail = {"error": "maintenance_cycle_timeout", "timeout_seconds": timeout_seconds}
        finish_scheduler_lease("failed", detail)
        return {"status": "failed", **detail}


async def scheduler_loop(stop: asyncio.Event) -> None:
    settings = get_settings()
    try:
        await asyncio.wait_for(stop.wait(), timeout=60)
        return
    except TimeoutError:
        pass
    while not stop.is_set():
        await run_bounded_maintenance_cycle(max(5, settings.scheduler_cycle_timeout_minutes) * 60)
        try:
            await asyncio.wait_for(stop.wait(), timeout=max(15, settings.scheduler_interval_minutes) * 60)
        except TimeoutError:
            continue
