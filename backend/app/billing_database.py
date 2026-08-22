from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


settings = get_settings()
transaction_url = settings.effective_transaction_database_url
connect_args: dict[str, object] = {}
if transaction_url.startswith("sqlite"):
    connect_args["timeout"] = 30
elif ":6543/" in transaction_url:
    # Supabase's transaction-mode pooler cannot retain connection-local prepared
    # statement state between requests.
    connect_args["prepare_threshold"] = None
billing_engine = create_engine(
    transaction_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)
BillingSessionLocal = sessionmaker(bind=billing_engine, autoflush=False, expire_on_commit=False)


def get_billing_db() -> Generator[Session, None, None]:
    session = BillingSessionLocal()
    try:
        yield session
    finally:
        session.close()
