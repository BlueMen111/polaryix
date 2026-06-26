from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações principais da API."""

    app_name: str = "Polaryix API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    max_upload_size_mb: int = 25
    max_rows_preview: int = 1000

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()