from typing import Any

from pydantic import BaseModel, Field


class DashboardWidget(BaseModel):
    id: str
    type: str
    title: str
    config: dict[str, Any] = Field(default_factory=dict)


class CreateDashboardRequest(BaseModel):
    dataset_id: str
    title: str
    slug: str | None = None
    is_public: bool = True


class Dashboard(BaseModel):
    id: str
    dataset_id: str
    title: str
    slug: str
    is_public: bool
    public_url: str | None = None
    widgets: list[DashboardWidget] = Field(default_factory=list)
    dataset: dict[str, Any] | None = None