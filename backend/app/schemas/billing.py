from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FeatureAllowance(BaseModel):
    allowed: bool
    reset_at: datetime | None = None
    word_limit: int | None = None


class AccountEntitlements(BaseModel):
    tier: Literal["free", "plus", "professional"]
    ask: FeatureAllowance
    planner: FeatureAllowance
    report_download: FeatureAllowance
    watchlists: FeatureAllowance


class AccountStatusResponse(BaseModel):
    authenticated: bool
    email: str | None = None
    entitlements: AccountEntitlements
    billing_configured: bool
    coin_billing_configured: bool
    coin_balance: int = 0
    has_billing_account: bool = False


class CheckoutRequest(BaseModel):
    tier: Literal["plus", "professional"]
    cadence: Literal["monthly", "annual"] = "monthly"


class CoinCheckoutRequest(BaseModel):
    pack: Literal["coins_25", "coins_75"]


class RedirectResponse(BaseModel):
    url: str


class ReportAccessResponse(BaseModel):
    allowed: bool
