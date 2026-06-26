from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config.settings import settings


class LocalStorageError(RuntimeError):
    """Erro lançado quando o arquivo não pode ser salvo localmente."""


async def save_upload_to_quarantine(file: UploadFile, safe_filename: str) -> Path:
    """Salva o upload em quarentena com nome seguro e único."""

    settings.quarantine_path.mkdir(parents=True, exist_ok=True)

    extension = Path(safe_filename).suffix.lower()
    stored_name = f"{uuid4().hex}{extension}"
    destination = settings.quarantine_path / stored_name

    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)

        await file.seek(0)
        return destination

    except Exception as exc:
        raise LocalStorageError("Não foi possível salvar o arquivo enviado.") from exc