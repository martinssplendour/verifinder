from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
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


class AppAdmin(BillingBase):
    """Database-backed access grant for VeriFinder's internal admin area."""

    __tablename__ = "app_admins"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), default="admin")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
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


class CoinWallet(BillingBase):
    """Current prepaid Ask balance for an authenticated account."""

    __tablename__ = "coin_wallets"

    # Profiles can be owned by a different Supabase database role. Keep this
    # ledger keyed by the verified subject without requiring REFERENCES on the
    # pre-existing profiles table during production migrations.
    subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class CoinTransaction(BillingBase):
    """Immutable coin ledger; unique references make purchases and refunds idempotent."""

    __tablename__ = "coin_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40))
    reference_id: Mapped[str] = mapped_column(String(120), unique=True)
    balance_after: Mapped[int] = mapped_column(Integer)
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_coin_transactions_subject_created", "subject_id", "created_at"),)


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


class AskConversation(BillingBase):
    """Server-owned Ask thread so follow-up context survives reloads and devices."""

    __tablename__ = "ask_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (Index("ix_ask_conversations_subject_updated", "subject_id", "updated_at"),)


class AskConversationRecord(BillingBase):
    """Immutable response packet used to rebuild bounded Ask context."""

    __tablename__ = "ask_conversation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ask_conversations.id", ondelete="CASCADE"), index=True
    )
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_ask_records_conversation_created", "conversation_id", "created_at"),)


class WatchlistEntry(BillingBase):
    __tablename__ = "watchlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(120))
    label: Mapped[str | None] = mapped_column(String(300))
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("ix_watchlist_subject_entity", "subject_id", "entity_type", "entity_id", unique=True),
    )


class WatchlistAlert(BillingBase):
    __tablename__ = "watchlist_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watchlist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("watchlist_entries.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(120))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict | None] = mapped_column(JSON)
    email_status: Mapped[str] = mapped_column(String(20), default="pending")
    email_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CompanySnapshot(BillingBase):
    __tablename__ = "company_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_number: Mapped[str] = mapped_column(String(12), index=True)
    company_status: Mapped[str | None] = mapped_column(String(80))
    sic_codes_hash: Mapped[str | None] = mapped_column(String(64))
    accounts_next_due: Mapped[str | None] = mapped_column(String(40))
    officer_count: Mapped[int | None] = mapped_column(Integer)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("ix_company_snapshot_number_checked", "company_number", "checked_at"),
    )


class SavedReport(BillingBase):
    __tablename__ = "saved_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    source_report_id: Mapped[str] = mapped_column(String(80))
    report_type: Mapped[str] = mapped_column(String(40), default="decision_plan")
    title: Mapped[str] = mapped_column(String(300))
    storage_bucket: Mapped[str] = mapped_column(String(100))
    storage_path: Mapped[str] = mapped_column(String(700), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(30), default="ready")
    provenance_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("ix_saved_reports_subject_created", "subject_id", "created_at"),
        Index("ix_saved_reports_subject_source", "subject_id", "source_report_id", unique=True),
    )


class WatchSnapshot(BillingBase):
    __tablename__ = "watch_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watchlist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("watchlist_entries.id", ondelete="CASCADE"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_watch_snapshots_entry_checked", "watchlist_entry_id", "checked_at"),)


class OperationCheck(BillingBase):
    __tablename__ = "operation_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    check_name: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(20))
    detail: Mapped[dict | None] = mapped_column(JSON)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_operation_checks_name_checked", "check_name", "checked_at"),)


class SchedulerLease(BillingBase):
    __tablename__ = "scheduler_leases"

    job_name: Mapped[str] = mapped_column(String(80), primary_key=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(20))
    last_detail: Mapped[dict | None] = mapped_column(JSON)
