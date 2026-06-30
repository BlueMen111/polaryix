from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Configurações principais da API."""

    app_name: str = "Polaryix API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    max_upload_size_mb: int = 100
    max_rows_preview: int = 0
    free_daily_credits: int = 30
    basic_monthly_credits: int = 1000
    pro_monthly_credits: int = 3000
    frontend_url: str = "http://localhost:3000"
    backend_public_url: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    mercadopago_access_token: str | None = None
    mercadopago_public_key: str | None = None
    mercadopago_webhook_secret: str | None = None
    mercadopago_env: str = "sandbox"
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_webhook_id: str | None = None
    paypal_env: str = "sandbox"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    conversion_workers: int = 2
    max_concurrent_conversions: int = 2
    file_retention_hours: int = 12
    cleanup_interval_hours: int = 12
    link_download_retention_minutes: int = 10
    free_storage_limit_mb: int = 25
    premium_storage_limit_mb: int = 100
    free_file_retention_hours: int = 2
    premium_file_retention_hours: int = 24
    max_free_file_size_mb: int = 100
    max_basic_file_size_mb: int = 300
    max_pro_file_size_mb: int = 1024
    admin_cleanup_token: str | None = None

    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://polaryix.vercel.app",
    ]
    allowed_origin_regex: str | None = r"^https://([a-zA-Z0-9-]+\.github\.io|[a-zA-Z0-9-]+\.vercel\.app)$"

    allowed_extensions: set[str] = {
        ".csv",
        ".xls",
        ".xlsx",
        ".json",
        ".txt",
        ".parquet",
    }

    storage_path: Path = Path("storage")
    upload_path: Path = Path("storage/uploads")
    quarantine_path: Path = Path("storage/quarantine")
    processed_path: Path = Path("storage/processed")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False

            if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True

        return value

    model_config = SettingsConfigDict(
        env_file=(API_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
