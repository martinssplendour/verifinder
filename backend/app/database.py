from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection

from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
public_database_url = settings.effective_public_database_url
connect_args: dict[str, object] = {}
if public_database_url.startswith("sqlite"):
    connect_args["timeout"] = 30
elif public_database_url.startswith("duckdb"):
    connect_args["read_only"] = True
engine = create_engine(public_database_url, pool_pre_ping=True, connect_args=connect_args)


if public_database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class ReadOnlySessionError(RuntimeError):
    pass


@event.listens_for(Session, "before_flush")
def _prevent_read_only_flush(session: Session, _flush_context, _instances) -> None:
    if session.info.get("read_only"):
        raise ReadOnlySessionError("Decision-intelligence sessions are read-only.")


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_read_db() -> Generator[Session, None, None]:
    """Yield a database session that the database itself prevents from writing."""
    connection: Connection = engine.connect()
    transaction = None
    if public_database_url.startswith("sqlite"):
        connection.exec_driver_sql("PRAGMA query_only = ON")
    elif public_database_url.startswith(("postgres://", "postgresql")):
        transaction = connection.begin()
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
    session = Session(bind=connection, autoflush=False, expire_on_commit=False)
    session.info["read_only"] = True
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        if transaction is not None and transaction.is_active:
            transaction.rollback()
        if public_database_url.startswith("sqlite"):
            connection.exec_driver_sql("PRAGMA query_only = OFF")
        connection.close()
