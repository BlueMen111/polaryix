"""
Analysis Sessions API Routes

Endpoints for managing multi-file analysis sessions.
"""

from fastapi import APIRouter, HTTPException, status

from app.domain.analysis_sessions import (
    CreateAnalysisSessionRequest,
    UpdateAnalysisSessionRequest,
    AnalysisSessionResponse,
)
from app.infrastructure.storage.analysis_sessions_storage import (
    create_analysis_session,
    get_analysis_session,
    list_analysis_sessions,
    update_analysis_session,
    delete_analysis_session,
    AnalysisSessionStorageError,
)

router = APIRouter(prefix="/analysis-sessions", tags=["Analysis Sessions"])


@router.post(
    "",
    response_model=AnalysisSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new analysis session",
)
def create_session(request: CreateAnalysisSessionRequest):
    """
    Create a new analysis session.
    
    This session will store:
    - Multiple uploaded files
    - Business description
    - Analysis objective
    - Generated dashboard specification
    """
    try:
        session_data = create_analysis_session(
            title=request.title,
            description=request.description,
            objective=request.objective,
            objective_category=request.objective_category.value
            if request.objective_category
            else None,
        )

        return AnalysisSessionResponse(
            id=session_data["id"],
            title=session_data["title"],
            description=session_data["description"],
            objective=session_data["objective"],
            objective_category=session_data["objective_category"],
            files_count=len(session_data["files"]),
            status=session_data["status"],
            dashboard_id=session_data["dashboard_id"],
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            completed_at=session_data["completed_at"],
        )
    except AnalysisSessionStorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analysis session: {str(e)}",
        )


@router.get(
    "",
    response_model=list[AnalysisSessionResponse],
    summary="List all analysis sessions",
)
def list_sessions():
    """List all analysis sessions."""
    try:
        sessions_data = list_analysis_sessions()

        return [
            AnalysisSessionResponse(
                id=session["id"],
                title=session["title"],
                description=session["description"],
                objective=session["objective"],
                objective_category=session["objective_category"],
                files_count=len(session["files"]),
                status=session["status"],
                dashboard_id=session["dashboard_id"],
                created_at=session["created_at"],
                updated_at=session["updated_at"],
                completed_at=session["completed_at"],
            )
            for session in sessions_data
        ]
    except AnalysisSessionStorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list analysis sessions: {str(e)}",
        )


@router.get(
    "/{session_id}",
    response_model=AnalysisSessionResponse,
    summary="Get analysis session details",
)
def get_session(session_id: str):
    """Get details of a specific analysis session."""
    try:
        session_data = get_analysis_session(session_id)

        if session_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis session '{session_id}' not found",
            )

        return AnalysisSessionResponse(
            id=session_data["id"],
            title=session_data["title"],
            description=session_data["description"],
            objective=session_data["objective"],
            objective_category=session_data["objective_category"],
            files_count=len(session_data["files"]),
            status=session_data["status"],
            dashboard_id=session_data["dashboard_id"],
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            completed_at=session_data["completed_at"],
        )
    except AnalysisSessionStorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analysis session: {str(e)}",
        )


@router.patch(
    "/{session_id}",
    response_model=AnalysisSessionResponse,
    summary="Update analysis session",
)
def update_session(
    session_id: str,
    request: UpdateAnalysisSessionRequest,
):
    """Update an analysis session (title, description, objective)."""
    try:
        updates = request.model_dump(exclude_unset=True)

        # Convert enum to value if present
        if "objective_category" in updates and updates["objective_category"]:
            updates["objective_category"] = updates["objective_category"].value

        session_data = update_analysis_session(session_id, updates)

        return AnalysisSessionResponse(
            id=session_data["id"],
            title=session_data["title"],
            description=session_data["description"],
            objective=session_data["objective"],
            objective_category=session_data["objective_category"],
            files_count=len(session_data["files"]),
            status=session_data["status"],
            dashboard_id=session_data["dashboard_id"],
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            completed_at=session_data["completed_at"],
        )
    except AnalysisSessionStorageError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update analysis session: {str(e)}",
        )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete analysis session",
)
def delete_session(session_id: str):
    """Delete an analysis session."""
    try:
        delete_analysis_session(session_id)
    except AnalysisSessionStorageError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete analysis session: {str(e)}",
        )
