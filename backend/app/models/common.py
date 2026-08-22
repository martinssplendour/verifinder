from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone


def uuid_string() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceHealth(str, enum.Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    INGESTION_FAILED = "ingestion_failed"
    SCHEMA_CHANGED = "schema_changed"


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNCHANGED = "unchanged"


class MatchStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNMATCHED = "unmatched"
    REJECTED = "rejected"
