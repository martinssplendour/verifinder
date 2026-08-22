from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BillingBase(DeclarativeBase):
    pass


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PLUS = "plus"
    PROFESSIONAL = "professional"


class Profile(BillingBase):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, native_enum=False), default=SubscriptionTier.FREE
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(80))
    subscription_status: Mapped[str | None] = mapped_column(String(40))
    subscription_current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UsageEvent(BillingBase):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    feature: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_usage_events_subject_feature_created", "subject_id", "feature", "created_at"),)
