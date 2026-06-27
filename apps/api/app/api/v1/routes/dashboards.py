from fastapi import APIRouter, HTTPException

from app.data_processing.analysis_context import (
    ROLE_LABELS,
    build_dataset_context,
    infer_intent,
    infer_column_role,
)
from app.data_processing.dashboard_engine import build_automatic_dashboard
from app.domain.dashboards.schemas import CreateDashboardRequest
from app.infrastructure.storage.analysis_sessions_storage import list_analysis_sessions
from app.infrastructure.storage.dashboard_storage import (
    create_dashboard,
    get_dashboard,
    get_public_dashboard,
    list_dashboards,
)

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _basic_file_context(file_data: dict, intent: dict) -> dict:
    columns = []

    for column_name in file_data.get("column_names") or []:
        column = {
            "name": column_name,
            "semantic_type": "unknown",
            "type_confidence": 0,
            "unique_count": None,
            "missing_percentage": None,
            "sample_values": [],
        }
        role = infer_column_role(column)
        columns.append(
            {
                "name": column_name,
                "role": role,
                "semantic_type": "unknown",
                "confidence": 0,
                "unique_count": None,
                "missing_percentage": None,
                "sample_values": [],
                "relevance_score": 1,
            }
        )

    roles = sorted({column["role"] for column in columns})
    filters = [
        {
            "column": column["name"],
            "role": column["role"],
            "label": ROLE_LABELS.get(column["role"], column["role"].title()),
            "options": [],
        }
        for column in columns
        if column["role"] in {"date", "seller", "sales", "customer", "product", "location", "payment", "dimension"}
    ]

    return {
        "filename": file_data.get("filename"),
        "rows": file_data.get("row_count"),
        "columns": file_data.get("column_count"),
        "roles": roles,
        "role_labels": [ROLE_LABELS.get(role, role.title()) for role in roles],
        "relevance_score": len(columns),
        "columns_detected": columns,
        "filters": filters,
    }


def _enrich_dashboard_context(dashboard: dict) -> dict:
    matching_session = None
    public_url = dashboard.get("public_url")

    for session in list_analysis_sessions():
        dashboard_specification = session.get("dashboard_specification") or {}
        metadata = dashboard_specification.get("metadata") or {}

        if session.get("dashboard_id") == dashboard.get("id") or metadata.get("public_url") == public_url:
            matching_session = session
            break

    if matching_session is not None:
        intent = infer_intent(
            matching_session.get("description"),
            matching_session.get("objective"),
        )
        automatic_dashboard = build_automatic_dashboard(matching_session)

        if automatic_dashboard:
            dashboard["widgets"] = automatic_dashboard["widgets"]
            dashboard["engine"] = {
                "primary_file": automatic_dashboard["primary_file"],
                "metric_column": automatic_dashboard["metric_column"],
                "relationships": automatic_dashboard["relationships"],
            }

        files = [
            file.get("analysis_context") or _basic_file_context(file, intent)
            for file in matching_session.get("files", [])
        ]
    else:
        intent = infer_intent(None, dashboard.get("title"))
        dataset = dashboard.get("dataset") or {}
        profile = dataset.get("profile") or {}
        files = [
            build_dataset_context(
                filename=dataset.get("original_filename", "dataset"),
                dataset_id=dataset.get("dataset_id", dashboard.get("dataset_id")),
                profile=profile,
                intent=intent,
            )
        ]

    ranked_files = sorted(
        files,
        key=lambda file: file.get("relevance_score", 0),
        reverse=True,
    )
    filters = []

    for file in ranked_files:
        for filter_item in file.get("filters", []):
            filters.append({**filter_item, "filename": file.get("filename")})

    if matching_session is not None and dashboard.get("engine"):
        automatic_dashboard = build_automatic_dashboard(matching_session)
        if automatic_dashboard:
            filters = [*automatic_dashboard["filters"], *filters]

    dashboard["analysis_context"] = {
        "intent": intent,
        "files": ranked_files,
        "filters": filters[:24],
    }

    return dashboard


@router.post("")
def create_dashboard_route(payload: CreateDashboardRequest):
    return create_dashboard(payload)


@router.get("")
def list_dashboards_route():
    return list_dashboards()


@router.get("/{dashboard_id}")
def get_dashboard_route(dashboard_id: str):
    dashboard = get_dashboard(dashboard_id)

    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return _enrich_dashboard_context(dashboard)


@router.get("/public/{slug}")
def get_public_dashboard_route(slug: str):
    dashboard = get_public_dashboard(slug)

    if dashboard is None:
        raise HTTPException(status_code=404, detail="Public dashboard not found")

    return _enrich_dashboard_context(dashboard)
