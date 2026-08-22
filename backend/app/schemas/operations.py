from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OperationCheckView(BaseModel):
    check_name: str
    status: str
    detail: dict | None
    checked_at: datetime
