from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VeriFinder API"
    environment: str = "development"
    database_url: str = "sqlite:///./verifinder.sqlite3"
    public_data_mode: str = "sqlite"
    public_data_root: str = "../public-data"
    public_database_url: str | None = None
    transaction_database_url: str | None = None
    transaction_migration_database_url: str | None = None
    companies_house_api_key: str | None = None
    epc_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    subject_signing_key: str | None = None
    app_url: str = "http://localhost:3000"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_plus_price_id: str | None = None
    stripe_professional_price_id: str | None = None
    stripe_portal_configuration_id: str | None = None
    raw_data_storage: str = "../raw-data"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def public_catalog_path(self) -> Path:
        return Path(self.public_data_root).expanduser().resolve() / "verifinder.duckdb"

    @property
    def effective_public_database_url(self) -> str:
        if self.public_data_mode == "parquet":
            return self.public_database_url or f"duckdb:///{self.public_catalog_path.as_posix()}"
        return self.public_database_url or self.database_url

    @property
    def effective_transaction_database_url(self) -> str:
        if self.transaction_database_url:
            return self.transaction_database_url
        if self.public_data_mode == "parquet":
            return "sqlite:///./verifinder-transactions.sqlite3"
        return self.database_url

    @property
    def effective_transaction_migration_database_url(self) -> str:
        return self.transaction_migration_database_url or self.effective_transaction_database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
