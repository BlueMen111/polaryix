"""
Pydantic schemas for Analysis Sessions.

Analysis Sessions represent a complete analysis context with multiple files,
business description, analysis objectives, and generated dashboards.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnalysisSessionStatus(str, Enum):
    """Status of an analysis session."""
    DRAFT = "draft"  # Created, awaiting files and description
    READY = "ready"  # All required info provided, ready to process
    PROCESSING = "processing"  # AI is analyzing the data
    COMPLETED = "completed"  # Dashboard generated successfully
    FAILED = "failed"  # Processing error
    ARCHIVED = "archived"  # Session archived


class AnalysisObjectiveCategory(str, Enum):
    """Predefined analysis objective categories."""
    COMMERCIAL = "comercial"
    FINANCIAL = "financeiro"
    MARKETING = "marketing"
    HR = "rh"
    OPERATIONAL = "operacional"
    LOGISTICS = "logistica"
    CUSTOMER_SERVICE = "atendimento"
    OTHER = "outro"


class AnalysisSessionFile(BaseModel):
    """File metadata within an analysis session."""
    file_id: str = Field(..., description="UUID of the uploaded file")
    filename: str = Field(..., description="Original filename")
    size_bytes: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="File format (csv, xlsx, json, etc)")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    row_count: int | None = None
    column_count: int | None = None
    column_names: list[str] | None = None


class CreateAnalysisSessionRequest(BaseModel):
    """Request to create a new analysis session."""
    title: str = Field(
        ..., 
        min_length=3, 
        max_length=255,
        description="Session title"
    )
    description: str | None = Field(
        None,
        max_length=5000,
        description="Business description in natural language"
    )
    objective: str | None = Field(
        None,
        max_length=2000,
        description="Analysis objective in natural language"
    )
    objective_category: AnalysisObjectiveCategory | None = Field(
        None,
        description="Predefined category of analysis objective"
    )


class UpdateAnalysisSessionRequest(BaseModel):
    """Request to update an analysis session."""
    title: str | None = Field(
        None,
        min_length=3,
        max_length=255
    )
    description: str | None = Field(
        None,
        max_length=5000
    )
    objective: str | None = Field(
        None,
        max_length=2000
    )
    objective_category: AnalysisObjectiveCategory | None = None


class DashboardSpecification(BaseModel):
    """Structured specification for dashboard generation."""
    title: str
    description: str | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisSession(BaseModel):
    """Complete analysis session with all context and generated dashboard."""
    id: str = Field(..., description="Unique session ID (UUID)")
    title: str
    description: str | None = None
    objective: str | None = None
    objective_category: AnalysisObjectiveCategory | None = None
    
    # Files and data
    files: list[AnalysisSessionFile] = Field(
        default_factory=list,
        description="Uploaded files for this analysis"
    )
    
    # Status and processing
    status: AnalysisSessionStatus = Field(
        default=AnalysisSessionStatus.DRAFT,
        description="Current session status"
    )
    processing_steps: list[str] = Field(
        default_factory=list,
        description="Steps completed during processing"
    )
    
    # Generated content
    dashboard_specification: DashboardSpecification | None = Field(
        None,
        description="Generated dashboard specification"
    )
    dashboard_id: str | None = Field(
        None,
        description="ID of generated dashboard"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    
    # Future: user/company tracking
    # user_id: str | None = None
    # company_id: str | None = None
    
    # Error handling
    error_message: str | None = None


class AnalysisSessionResponse(BaseModel):
    """Response model for analysis session (public API)."""
    id: str
    title: str
    description: str | None = None
    objective: str | None = None
    objective_category: AnalysisObjectiveCategory | None = None
    files_count: int
    status: AnalysisSessionStatus
    dashboard_id: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
