"""
Analysis Sessions File Upload Routes

Handles uploading and attaching files to analysis sessions.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.security.file_security import FileSecurityError, validate_uploaded_file
from app.data_processing.profiling.dataset_profiler import profile_dataframe
from app.data_processing.readers import DatasetReadError, read_dataset
from app.domain.analysis_sessions import AnalysisSessionFile
from app.infrastructure.storage.analysis_sessions_storage import (
    AnalysisSessionStorageError,
    add_file_to_session,
    get_analysis_session,
)
from app.infrastructure.storage.local_storage import LocalStorageError, save_upload_to_quarantine

router = APIRouter(prefix="/analysis-sessions", tags=["Analysis Sessions - Files"])


@router.post("/{session_id}/files")
async def upload_file_to_session(
    session_id: str,
    file: UploadFile = File(...),
) -> dict:
    """
    Upload a file to an analysis session.
    
    Supports: CSV, Excel, JSON, Parquet, TXT
    Max size: 25MB
    
    The file will be:
    1. Validated for security
    2. Saved to quarantine
    3. Analyzed (columns, rows, types detected)
    4. Attached to the analysis session
    """

    try:
        # Validate session exists
        session = get_analysis_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis session '{session_id}' not found",
            )

        # Validate file security
        metadata = await validate_uploaded_file(file)

        # Save to quarantine
        stored_path = await save_upload_to_quarantine(file, metadata["filename"])

        # Read and profile dataset
        dataframe = read_dataset(
            path=stored_path,
            extension=metadata["extension"],
        )

        profile = profile_dataframe(dataframe)

        # Add file to session with metadata
        file_id = metadata.get("file_id") or str(stored_path.stem)

        # Extract column names from column profiles
        column_names = [
            col_profile["name"] for col_profile in profile.get("column_profiles", [])
        ]

        session_data = add_file_to_session(
            session_id=session_id,
            file_id=file_id,
            filename=metadata["filename"],
            size_bytes=metadata["size_bytes"],
            format=metadata["extension"].lstrip("."),
            row_count=profile.get("rows"),
            column_count=profile.get("columns"),
            column_names=column_names,
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

    except AnalysisSessionStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach file to session: {str(exc)}",
        ) from exc
