"""
Analysis Sessions File Upload Routes

Handles uploading and attaching files to analysis sessions.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.security.file_security import FileSecurityError, validate_uploaded_file
from app.data_processing.analysis_context import (
    build_dataset_context,
    build_session_context,
    infer_intent,
)
from app.data_processing.dashboard_engine import build_automatic_dashboard
from app.data_processing.profiling.dataset_profiler import profile_dataframe
from app.data_processing.readers import DatasetReadError, read_dataset
from app.domain.dashboards.schemas import CreateDashboardRequest
from app.infrastructure.storage.analysis_storage import (
    AnalysisStorageError,
    save_dataset_analysis,
)
from app.infrastructure.storage.analysis_sessions_storage import (
    AnalysisSessionStorageError,
    add_file_to_session,
    get_analysis_session,
    update_analysis_session,
)
from app.infrastructure.storage.dashboard_storage import (
    DashboardStorageError,
    create_dashboard,
    get_dashboard,
    save_dashboard_payload,
)
from app.infrastructure.storage.local_storage import LocalStorageError, save_upload_to_quarantine

router = APIRouter(prefix="/analysis-sessions", tags=["Analysis Sessions - Files"])

# Limite de 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024


@router.post("/{session_id}/files")
async def upload_file_to_session(
    session_id: str,
    file: UploadFile = File(...),
    file_description: str | None = Form(default=None),
) -> dict:
    """
    Upload a file to an analysis session.
    
    Supports: CSV, Excel, JSON, Parquet, TXT
    Max size: 100MB
    Max rows: No limit (analyzes all rows)
    
    The file will be:
    1. Validated for security
    2. Saved to quarantine
    3. Analyzed (columns, rows, types detected)
    4. Attached to the analysis session
    """

    try:
        print(f"[UPLOAD] Starting upload for session: {session_id}")
        
        # Validate session exists
        session = get_analysis_session(session_id)
        if session is None:
            print(f"[UPLOAD] Session not found: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis session '{session_id}' not found",
            )

        # Check file size manually (150MB limit)
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                print(f"[UPLOAD] File too large: {file_size} bytes")
                raise HTTPException(
                    status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
                    detail=f"Arquivo excede o limite de 100MB.",
                )
        await file.seek(0)  # Reset file pointer
        print(f"[UPLOAD] File size OK: {file_size} bytes")

        # Validate file security
        print(f"[UPLOAD] Validating file security...")
        metadata = await validate_uploaded_file(file)
        print(f"[UPLOAD] Security validation passed: {metadata['filename']}")

        # Save to quarantine
        stored_path = await save_upload_to_quarantine(file, metadata["filename"])

        # Read and profile dataset
        dataframe = read_dataset(
            path=stored_path,
            extension=metadata["extension"],
        )

        profile = profile_dataframe(dataframe)
        dataset_analysis = save_dataset_analysis(
            original_filename=metadata["filename"],
            stored_path=stored_path,
            metadata=metadata,
            profile=profile,
        )

        # Add file to session with metadata
        file_id = metadata.get("file_id") or str(stored_path.stem)

        # Extract column names from column profiles
        column_names = [
            col_profile["name"] for col_profile in profile.get("column_profiles", [])
        ]
        intent = infer_intent(session.get("description"), session.get("objective"))
        context_filename = (
            f"{metadata['filename']} {file_description}"
            if file_description
            else metadata["filename"]
        )
        file_context = build_dataset_context(
            filename=context_filename,
            dataset_id=dataset_analysis["dataset_id"],
            profile=profile,
            intent=intent,
        )

        session_data = add_file_to_session(
            session_id=session_id,
            file_id=file_id,
            filename=metadata["filename"],
            size_bytes=metadata["size_bytes"],
            format=metadata["extension"].lstrip("."),
            row_count=profile.get("rows"),
            column_count=profile.get("columns"),
            column_names=column_names,
            dataset_id=dataset_analysis["dataset_id"],
            analysis_context=file_context,
            user_description=file_description,
        )

        dashboard = create_dashboard(
            CreateDashboardRequest(
                dataset_id=dataset_analysis["dataset_id"],
                title=session_data["title"],
                is_public=True,
            )
        )
        selected_dashboard = dashboard
        existing_dashboard_id = session_data.get("dashboard_id")

        if existing_dashboard_id:
            existing_dashboard = get_dashboard(existing_dashboard_id)

            if existing_dashboard is not None:
                existing_profile = existing_dashboard.get("dataset", {}).get("profile", {})
                new_profile = dashboard.get("dataset", {}).get("profile", {})
                existing_score = int(existing_profile.get("rows", 0)) * int(
                    existing_profile.get("columns", 0)
                )
                new_score = int(new_profile.get("rows", 0)) * int(
                    new_profile.get("columns", 0)
                )

                if existing_score > new_score:
                    selected_dashboard = existing_dashboard

        session_context = build_session_context(session_data)
        automatic_dashboard = build_automatic_dashboard(session_data)

        if automatic_dashboard:
            selected_dashboard["widgets"] = automatic_dashboard["widgets"]
            selected_dashboard["engine"] = {
                "primary_file": automatic_dashboard["primary_file"],
                "metric_column": automatic_dashboard["metric_column"],
                "relationships": automatic_dashboard["relationships"],
            }
            session_context["filters"] = [
                *automatic_dashboard["filters"],
                *session_context.get("filters", []),
            ][:24]

        selected_dashboard["analysis_context"] = session_context
        selected_dashboard = save_dashboard_payload(selected_dashboard)

        session_data = update_analysis_session(
            session_id=session_id,
            updates={
                "status": "completed",
                "processing_steps": [
                    "Entendendo seu negócio",
                    "Lendo arquivos",
                    "Relacionando dados",
                    "Detectando indicadores",
                    "Planejando Dashboard",
                    "Construindo gráficos",
                    "Finalizando",
                ],
                "dashboard_id": selected_dashboard["id"],
                "dashboard_specification": {
                    "title": selected_dashboard["title"],
                    "description": "Dashboard inicial gerado a partir do arquivo enviado.",
                    "sections": selected_dashboard.get("widgets", []),
                    "metadata": {
                        "dataset_id": selected_dashboard.get("dataset_id"),
                        "public_url": selected_dashboard.get("public_url"),
                        "analysis_context": session_context,
                    },
                },
                "completed_at": selected_dashboard["created_at"],
                "error_message": None,
            },
        )

        return {
            "message": "File uploaded, validated and attached to analysis session successfully.",
            "session_id": session_id,
            "file": {
                "file_id": file_id,
                "filename": metadata["filename"],
                "format": metadata["extension"],
                "size_bytes": metadata["size_bytes"],
                "row_count": profile.get("rows"),
                "column_count": profile.get("columns"),
                "columns": column_names[:10],  # First 10 columns
            },
            "session": {
                "id": session_data["id"],
                "title": session_data["title"],
                "files_count": len(session_data["files"]),
                "status": session_data["status"],
                "dashboard_id": session_data["dashboard_id"],
            },
        }

    except FileSecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File security validation failed: {str(exc)}",
        ) from exc

    except DatasetReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read file: {str(exc)}",
        ) from exc

    except LocalStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(exc)}",
        ) from exc

    except (AnalysisStorageError, DashboardStorageError) as exc:
        try:
            update_analysis_session(
                session_id=session_id,
                updates={
                    "status": "failed",
                    "error_message": str(exc),
                },
            )
        except AnalysisSessionStorageError:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate dashboard: {str(exc)}",
        ) from exc

    except AnalysisSessionStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach file to session: {str(exc)}",
        ) from exc
