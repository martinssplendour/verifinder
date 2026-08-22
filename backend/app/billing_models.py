from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Subscription(BillingBase):
    """Canonical billing state synchronized from Stripe webhooks."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, index=True
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, native_enum=False), default=SubscriptionTier.FREE
    )
    provider: Mapped[str] = mapped_column(String(24), default="stripe")
    customer_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    subscription_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    status: Mapped[str | None] = mapped_column(String(40))
    price_id: Mapped[str | None] = mapped_column(String(80))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class StripeEvent(BillingBase):
    """Processed Stripe event ledger used to make webhook handling idempotent."""

    __tablename__ = "stripe_events"

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UsageEvent(BillingBase):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    feature: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str | None] = mapped_column(Text)
    network_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    quota_key: Mapped[str | None] = mapped_column(String(96), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_usage_events_subject_feature_created", "subject_id", "feature", "created_at"),)
