from __future__ import annotations

# Re-exported (not part of the public API surface below) so tests can
# monkeypatch `app.services.reports.get_settings` / `.httpx`; storage.py
# resolves both through this package namespace at call time.
import httpx  # noqa: F401
from app.config import get_settings  # noqa: F401

from .pdf import build_plan_pdf
from .storage import (
    ReportStorageError,
    delete_pdf,
    list_saved_reports,
    report_storage_configured,
    signed_download_url,
    storage_request_headers,
    upload_pdf,
)

__all__ = [
    "ReportStorageError",
    "build_plan_pdf",
    "delete_pdf",
    "list_saved_reports",
    "report_storage_configured",
    "signed_download_url",
    "upload_pdf",
    "storage_request_headers",
]
