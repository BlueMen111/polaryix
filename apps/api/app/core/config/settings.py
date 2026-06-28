from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None

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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
