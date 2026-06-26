"""
Analysis Sessions Progress Routes

Provides real-time progress information for analysis session processing.
"""

from fastapi import APIRouter, HTTPException, status

from app.domain.analysis_sessions import AnalysisSessionStatus
from app.infrastructure.storage.analysis_sessions_storage import (
    AnalysisSessionStorageError,
    get_analysis_session,
)

router = APIRouter(prefix="/analysis-sessions", tags=["Analysis Sessions - Progress"])


@router.get("/{session_id}/progress")
def get_session_progress(session_id: str) -> dict:
    """
    Get processing progress for an analysis session.
    
    Returns:
    - status: current session status
    - progress_percentage: estimated completion percentage
    - current_step: description of current processing step
    - completed_steps: list of completed steps
    - estimated_completion: optional ETA
    """
    try:
        session_data = get_analysis_session(session_id)
        
        if session_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis session '{session_id}' not found",
            )
        
        status_value = session_data.get("status", "draft")
        processing_steps = session_data.get("processing_steps", [])
        
        # Calculate progress based on status and steps
        progress_map = {
            AnalysisSessionStatus.DRAFT: 0,
            AnalysisSessionStatus.READY: 10,
            AnalysisSessionStatus.PROCESSING: 50,
            AnalysisSessionStatus.COMPLETED: 100,
            AnalysisSessionStatus.FAILED: 0,
            AnalysisSessionStatus.ARCHIVED: 100,
        }
        
        base_progress = progress_map.get(status_value, 0)
        
        # Refine progress for PROCESSING status based on steps
        current_step = ""
        completed_steps = processing_steps
        
        if status_value == AnalysisSessionStatus.PROCESSING:
            # Define processing steps and their weights
            all_steps = [
                ("Entendendo seu negócio", 25),
                ("Lendo arquivos", 25),
                ("Relacionando dados", 25),
                ("Gerando dashboard", 25),
            ]
            
            completed_count = len(processing_steps)
            current_step_index = min(completed_count, len(all_steps) - 1)
            
            # Calculate progress within current step
            if completed_count < len(all_steps):
                current_step = all_steps[current_step_index][0]
                # Add partial progress within current step (assume 50% if processing)
                step_progress = all_steps[current_step_index][1] * 0.5
                base_progress = 10 + sum(step[1] for step in all_steps[:completed_count]) + step_progress
            else:
                current_step = "Finalizando"
                base_progress = 95
        
        elif status_value == AnalysisSessionStatus.READY:
            current_step = "Aguardando processamento"
        
        elif status_value == AnalysisSessionStatus.COMPLETED:
            current_step = "Concluído"
        
        elif status_value == AnalysisSessionStatus.FAILED:
            current_step = "Erro no processamento"
        
        return {
            "session_id": session_id,
            "status": status_value,
            "progress_percentage": round(base_progress, 1),
            "current_step": current_step,
            "completed_steps": completed_steps,
            "files_count": len(session_data.get("files", [])),
            "error_message": session_data.get("error_message"),
        }
    
    except AnalysisSessionStorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve progress: {str(e)}",
        )