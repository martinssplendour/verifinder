from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.services.refresh as refresh
from app.services.govuk_content import GovUkContentError, pick_latest_csv_attachment
from app.services.refresh import is_due
from app.services.source_fetch import SourceFetchError


def test_is_due_when_never_retrieved():
    assert is_due(None, timedelta(days=1)) is True


def test_is_due_when_cadence_has_elapsed():
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    last = now - timedelta(days=2)
    assert is_due(last, timedelta(days=1), now=now) is True


def test_is_due_when_cadence_has_not_elapsed():
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    last = now - timedelta(hours=2)
    assert is_due(last, timedelta(days=1), now=now) is False


def test_is_due_at_exact_cadence_boundary():
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    last = now - timedelta(days=1)
    assert is_due(last, timedelta(days=1), now=now) is True


def test_is_due_handles_naive_datetime_from_sqlite():
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    naive_last = datetime(2026, 8, 20)
    assert naive_last.tzinfo is None
    assert is_due(naive_last, timedelta(days=1), now=now) is True
    assert is_due(datetime(2026, 8, 21, 23, 0), timedelta(days=1), now=now) is False


def test_pick_latest_csv_attachment_takes_last_chronological_match():
    attachments = [
        {"title": "Latest inspections as at 31 May 2026", "url": "https://assets.publishing.service.gov.uk/may.csv", "content_type": "text/csv"},
        {"title": "Latest inspections as at 30 June 2026", "url": "https://assets.publishing.service.gov.uk/june.csv", "content_type": "text/csv"},
        {"title": "Some other spreadsheet", "url": "https://assets.publishing.service.gov.uk/other.xlsx", "content_type": "application/vnd.ms-excel"},
    ]
    url, title = pick_latest_csv_attachment(attachments, title_contains="latest inspections")
    assert url == "https://assets.publishing.service.gov.uk/june.csv"
    assert "30 June 2026" in title


def test_pick_latest_csv_attachment_ignores_non_csv():
    attachments = [
        {"title": "Report", "url": "https://assets.publishing.service.gov.uk/report.csv", "content_type": "text/csv"},
        {"title": "Report", "url": "https://assets.publishing.service.gov.uk/report.xlsx", "content_type": "application/vnd.ms-excel"},
    ]
    url, _ = pick_latest_csv_attachment(attachments)
    assert url == "https://assets.publishing.service.gov.uk/report.csv"


def test_pick_latest_csv_attachment_raises_when_nothing_matches():
    with pytest.raises(GovUkContentError, match="No matching CSV"):
        pick_latest_csv_attachment([{"title": "Nope", "url": "https://assets.publishing.service.gov.uk/x.xlsx", "content_type": "application/vnd.ms-excel"}])


def test_pick_latest_csv_attachment_rejects_urls_outside_the_allowlist():
    attachments = [
        {"title": "Untrusted", "url": "https://evil.example/data.csv", "content_type": "text/csv"},
        {"title": "Trusted", "url": "https://assets.publishing.service.gov.uk/data.csv", "content_type": "text/csv"},
    ]
    url, _ = pick_latest_csv_attachment(attachments)
    assert url == "https://assets.publishing.service.gov.uk/data.csv"

    with pytest.raises(GovUkContentError, match="No matching CSV"):
        pick_latest_csv_attachment([{"title": "Only untrusted", "url": "https://evil.example/data.csv", "content_type": "text/csv"}])


def test_refresh_gias_skips_html_error_page_and_falls_back_a_day(tmp_path: Path, monkeypatch):
    fixed_today = date(2026, 8, 22)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 22, tzinfo=tz)

    monkeypatch.setattr(refresh, "datetime", FixedDatetime)

    yesterday = fixed_today - timedelta(days=1)

    def fake_download(url: str) -> bytes:
        if fixed_today.strftime("%Y%m%d") in url:
            return b"<!DOCTYPE html><html>Azure error page</html>"
        if yesterday.strftime("%Y%m%d") in url:
            return b"URN,EstablishmentName\n100000,Example School\n"
        raise SourceFetchError("not found")

    captured = {}

    def fake_ingest_school_file(path: Path, published_on=None):
        captured["path"] = path
        captured["published_on"] = published_on
        return {"processing_status": "succeeded"}

    monkeypatch.setattr(refresh, "download_bytes", fake_download)
    monkeypatch.setattr(refresh, "ingest_school_file", fake_ingest_school_file)

    result = refresh._refresh_gias(tmp_path)

    assert result == {"processing_status": "succeeded"}
    assert captured["path"].exists()
    assert captured["published_on"] == yesterday
