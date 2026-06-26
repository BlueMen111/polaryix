import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config.settings import settings


DATASETS_DIR = settings.processed_path / "datasets"


class AnalysisStorageError(RuntimeError):
    """Erro lançado quando não é possível salvar ou ler uma análise."""


def _ensure_datasets_dir() -> None:
    """Garante que a pasta de datasets processados exista."""

    DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def save_dataset_analysis(
    original_filename: str,
    stored_path: Path,
    metadata: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Salva a análise do dataset em JSON local."""

    _ensure_datasets_dir()

    dataset_id = uuid4().hex

    payload: dict[str, Any] = {
        "dataset_id": dataset_id,
        "original_filename": original_filename,
        "stored_filename": stored_path.name,
        "extension": metadata["extension"],
        "content_type": metadata.get("content_type"),
        "size_bytes": metadata["size_bytes"],
        "profile": profile,
        "created_at": datetime.now(UTC).isoformat(),
    }

    destination = DATASETS_DIR / f"{dataset_id}.json"

    try:
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        raise AnalysisStorageError("Não foi possível salvar a análise do dataset.") from exc

    return payload


def list_dataset_analyses() -> list[dict[str, Any]]:
    """Lista análises de datasets salvas localmente."""

    _ensure_datasets_dir()

    datasets: list[dict[str, Any]] = []

    for file_path in sorted(DATASETS_DIR.glob("*.json"), reverse=True):
        try:
            datasets.append(json.loads(file_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue

    return datasets


def get_dataset_analysis(dataset_id: str) -> dict[str, Any] | None:
    """Busca uma análise de dataset pelo ID."""

    _ensure_datasets_dir()

    file_path = DATASETS_DIR / f"{dataset_id}.json"

    if not file_path.exists():
        return None

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AnalysisStorageError("Arquivo de análise corrompido.") from exc