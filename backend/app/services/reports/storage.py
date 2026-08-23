from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing_models import SavedReport


class ReportStorageError(RuntimeError):
    pass


def _settings():
    # Resolved through the package namespace (not bound directly to app.config)
    # so that tests can monkeypatch `app.services.reports.get_settings`.
    from app.services import reports as _reports_pkg

    return _reports_pkg.get_settings()


def report_storage_configured() -> bool:
    settings = _settings()
    key = str(settings.supabase_secret_key or "")
    return bool(
        settings.supabase_url
        and key
        and not key.startswith("sb_secret_")
        and settings.report_storage_bucket
    )


def storage_request_headers(content_type: str | None = None) -> dict[str, str]:
    settings = _settings()
    if not report_storage_configured():
        raise ReportStorageError("Private report storage is not configured.")
    key = str(settings.supabase_secret_key)
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _object_url(path: str, *, operation: str = "object") -> str:
    settings = _settings()
    encoded_path = quote(PurePosixPath(path).as_posix(), safe="/")
    bucket = quote(settings.report_storage_bucket, safe="")
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/{operation}/{bucket}/{encoded_path}"


async def upload_pdf(path: str, pdf: bytes) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            _object_url(path),
            headers={**storage_request_headers("application/pdf"), "x-upsert": "false"},
            content=pdf,
        )
    if response.status_code not in {200, 201}:
        raise ReportStorageError(f"Supabase Storage rejected the report upload ({response.status_code}).")


async def signed_download_url(path: str) -> tuple[str, datetime]:
    settings = _settings()
    ttl = max(60, min(settings.report_signed_url_ttl_seconds, 3600))
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            _object_url(path, operation="object/sign"),
            headers=storage_request_headers("application/json"),
            json={"expiresIn": ttl, "download": True},
        )
    if response.status_code != 200:
        raise ReportStorageError(f"Supabase Storage could not sign the report download ({response.status_code}).")
    signed = response.json().get("signedURL") or response.json().get("signedUrl")
    if not isinstance(signed, str):
        raise ReportStorageError("Supabase Storage returned an invalid signed URL.")
    if signed.startswith("/"):
        signed = f"{settings.supabase_url.rstrip('/')}/storage/v1{signed}"
    expires_at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=ttl)
    return signed, expires_at


async def delete_pdf(path: str) -> None:
    settings = _settings()
    bucket = quote(settings.report_storage_bucket, safe="")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.request(
            "DELETE",
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}",
            headers=storage_request_headers("application/json"),
            json={"prefixes": [PurePosixPath(path).as_posix()]},
        )
    if response.status_code not in {200, 204, 404}:
        raise ReportStorageError(f"Supabase Storage could not remove the report ({response.status_code}).")


def list_saved_reports(session: Session, subject_id: str) -> list[SavedReport]:
    return list(
        session.scalars(
            select(SavedReport)
            .where(SavedReport.subject_id == subject_id, SavedReport.status == "ready")
            .order_by(SavedReport.created_at.desc())
        )
    )
