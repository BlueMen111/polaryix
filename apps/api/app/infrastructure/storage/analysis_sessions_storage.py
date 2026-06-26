"""
Analysis Sessions Storage

Handles persistence of analysis sessions (multi-file analysis contexts) to local JSON.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config.settings import settings
from app.domain.analysis_sessions import AnalysisSession


ANALYSIS_SESSIONS_DIR = settings.processed_path / "analysis_sessions"


class AnalysisSessionStorageError(RuntimeError):
    """Erro ao salvar ou ler uma sessão de análise."""


def _ensure_analysis_sessions_dir() -> None:
    """Garante que a pasta de sessões de análise exista."""
    ANALYSIS_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def create_analysis_session(
    title: str,
    description: str | None = None,
    objective: str | None = None,
    objective_category: str | None = None,
) -> dict[str, Any]:
    """Cria e persiste uma nova sessão de análise."""

    _ensure_analysis_sessions_dir()

    session_id = uuid4().hex
    now = datetime.now(UTC).isoformat()

    session_data: dict[str, Any] = {
        "id": session_id,
        "title": title,
        "description": description,
        "objective": objective,
        "objective_category": objective_category,
        "files": [],
        "status": "draft",
        "processing_steps": [],
        "dashboard_specification": None,
        "dashboard_id": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "error_message": None,
    }

    session_file = ANALYSIS_SESSIONS_DIR / f"{session_id}.json"

    try:
        session_file.write_text(
            json.dumps(session_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return session_data
    except OSError as e:
        raise AnalysisSessionStorageError(
            f"Falha ao salvar sessão de análise {session_id}: {e}"
        )


def get_analysis_session(session_id: str) -> dict[str, Any] | None:
    """Recupera uma sessão de análise pelo ID."""

    session_file = ANALYSIS_SESSIONS_DIR / f"{session_id}.json"

    if not session_file.exists():
        return None

    try:
        return json.loads(session_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise AnalysisSessionStorageError(
            f"Falha ao ler sessão de análise {session_id}: {e}"
        )


def list_analysis_sessions() -> list[dict[str, Any]]:
    """Lista todas as sessões de análise."""

    _ensure_analysis_sessions_dir()

    sessions = []
    try:
        for session_file in ANALYSIS_SESSIONS_DIR.glob("*.json"):
            try:
                session_data = json.loads(session_file.read_text(encoding="utf-8"))
                sessions.append(session_data)
            except json.JSONDecodeError:
                continue
        return sessions
    except OSError as e:
        raise AnalysisSessionStorageError(f"Falha ao listar sessões: {e}")


def update_analysis_session(
    session_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Atualiza uma sessão de análise."""

    session_data = get_analysis_session(session_id)

    if session_data is None:
        raise AnalysisSessionStorageError(f"Sessão {session_id} não encontrada")

    # Atualizar com novos valores
    session_data.update(updates)
    session_data["updated_at"] = datetime.now(UTC).isoformat()

    session_file = ANALYSIS_SESSIONS_DIR / f"{session_id}.json"

    try:
        session_file.write_text(
            json.dumps(session_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return session_data
    except OSError as e:
        raise AnalysisSessionStorageError(
            f"Falha ao atualizar sessão {session_id}: {e}"
        )


def add_file_to_session(
    session_id: str,
    file_id: str,
    filename: str,
    size_bytes: int,
    format: str,
    row_count: int | None = None,
    column_count: int | None = None,
    column_names: list[str] | None = None,
) -> dict[str, Any]:
    """Adiciona um arquivo a uma sessão de análise."""

    session_data = get_analysis_session(session_id)

    if session_data is None:
        raise AnalysisSessionStorageError(f"Sessão {session_id} não encontrada")

    file_entry = {
        "file_id": file_id,
        "filename": filename,
        "size_bytes": size_bytes,
        "format": format,
        "uploaded_at": datetime.now(UTC).isoformat(),
        "row_count": row_count,
        "column_count": column_count,
        "column_names": column_names,
    }

    session_data["files"].append(file_entry)
    session_data["updated_at"] = datetime.now(UTC).isoformat()

    session_file = ANALYSIS_SESSIONS_DIR / f"{session_id}.json"

    try:
        session_file.write_text(
            json.dumps(session_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return session_data
    except OSError as e:
        raise AnalysisSessionStorageError(
            f"Falha ao adicionar arquivo à sessão {session_id}: {e}"
        )


def delete_analysis_session(session_id: str) -> bool:
    """Deleta uma sessão de análise."""

    session_file = ANALYSIS_SESSIONS_DIR / f"{session_id}.json"

    if not session_file.exists():
        raise AnalysisSessionStorageError(f"Sessão {session_id} não encontrada")

    try:
        session_file.unlink()
        return True
    except OSError as e:
        raise AnalysisSessionStorageError(
            f"Falha ao deletar sessão {session_id}: {e}"
        )
