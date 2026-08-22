from __future__ import annotations

import json
from urllib.parse import urlparse

from app.services.source_fetch import SourceFetchError, download_bytes


CONTENT_API_BASE = "https://www.gov.uk/api/content"
ALLOWED_ATTACHMENT_HOSTS = {"assets.publishing.service.gov.uk", "www.gov.uk"}


class GovUkContentError(RuntimeError):
    pass


def _is_allowed_attachment_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_ATTACHMENT_HOSTS


def pick_latest_csv_attachment(attachments: list[dict], title_contains: str | None = None) -> tuple[str, str]:
    """Attachments on a GOV.UK content item are appended in publication order, so the
    last matching CSV is the current release."""
    matches = [
        attachment
        for attachment in attachments
        if attachment.get("content_type") == "text/csv"
        and attachment.get("url")
        and _is_allowed_attachment_url(attachment["url"])
        and (title_contains is None or title_contains.lower() in (attachment.get("title") or "").lower())
    ]
    if not matches:
        raise GovUkContentError(f"No matching CSV attachment found (title_contains={title_contains!r}).")
    latest = matches[-1]
    return latest["url"], latest.get("title", "")


def resolve_latest_csv_attachment(content_path: str, title_contains: str | None = None) -> tuple[str, str]:
    url = f"{CONTENT_API_BASE}/{content_path.strip('/')}"
    try:
        payload = json.loads(download_bytes(url))
    except SourceFetchError as error:
        raise GovUkContentError(str(error)) from error
    except json.JSONDecodeError as error:
        raise GovUkContentError(f"GOV.UK content API returned invalid JSON for {url}") from error
    attachments = (payload.get("details") or {}).get("attachments") or []
    return pick_latest_csv_attachment(attachments, title_contains)
