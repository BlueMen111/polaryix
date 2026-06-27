import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.config.settings import settings
from app.domain.dashboards.schemas import CreateDashboardRequest, DashboardWidget
from app.infrastructure.storage.analysis_storage import get_dataset_analysis


DASHBOARDS_DIR = settings.processed_path / "dashboards"
PUBLIC_DIR = settings.processed_path / "public"


class DashboardStorageError(RuntimeError):
    """Erro lançado quando não é possível salvar ou ler dashboards."""


def _ensure_dirs() -> None:
    """Garante que as pastas de dashboard existam."""

    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    """Gera um slug simples e seguro."""

    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    value = value.strip("-")

    return value or uuid4().hex[:12]


def _public_slug_exists(slug: str) -> bool:
    """Verifica se já existe dashboard público com esse slug."""

    return (PUBLIC_DIR / f"{slug}.json").exists()


def _make_unique_slug(base_slug: str) -> str:
    """Gera slug único."""

    slug = slugify(base_slug)
    candidate = slug
    counter = 2

    while _public_slug_exists(candidate):
        candidate = f"{slug}-{counter}"
        counter += 1

    return candidate


def build_default_widgets_from_dataset(dataset: dict[str, Any]) -> list[DashboardWidget]:
    """Cria widgets iniciais usando KPIs e sugestões de gráficos."""

    profile = dataset["profile"]
    widgets: list[DashboardWidget] = []

    for kpi in profile.get("kpis", [])[:6]:
        widgets.append(
            DashboardWidget(
                id=uuid4().hex,
                type="kpi",
                title=kpi["title"],
                config=kpi,
            )
        )

    for chart in profile.get("chart_suggestions", [])[:4]:
        widgets.append(
            DashboardWidget(
                id=uuid4().hex,
                type="chart",
                title=chart["title"],
                config=chart,
            )
        )

    if widgets:
        return widgets

    missing_total = sum(
        int(column.get("missing_count", 0))
        for column in profile.get("column_profiles", [])
    )

    fallback_kpis = [
        {
            "title": "Total de linhas",
            "value": profile.get("rows", 0),
            "description": "Quantidade de registros lidos no arquivo.",
        },
        {
            "title": "Total de colunas",
            "value": profile.get("columns", 0),
            "description": "Quantidade de campos detectados no dataset.",
        },
        {
            "title": "Linhas duplicadas",
            "value": profile.get("duplicate_rows", 0),
            "description": "Registros repetidos identificados na leitura inicial.",
        },
        {
            "title": "Valores ausentes",
            "value": missing_total,
            "description": "Soma de valores vazios encontrados nas colunas.",
        },
    ]

    for kpi in fallback_kpis:
        widgets.append(
            DashboardWidget(
                id=uuid4().hex,
                type="kpi",
                title=kpi["title"],
                config=kpi,
            )
        )

    return widgets


def create_dashboard(request: CreateDashboardRequest) -> dict[str, Any]:
    """Cria um dashboard baseado em um dataset analisado."""

    _ensure_dirs()

    dataset = get_dataset_analysis(request.dataset_id)

    if dataset is None:
        raise DashboardStorageError("Dataset informado não foi encontrado.")

    dashboard_id = uuid4().hex
    slug = _make_unique_slug(request.slug or request.title)

    widgets = build_default_widgets_from_dataset(dataset)

    payload: dict[str, Any] = {
        "id": dashboard_id,
        "dataset_id": request.dataset_id,
        "title": request.title,
        "slug": slug,
        "is_public": request.is_public,
        "widgets": [widget.model_dump() for widget in widgets],
        "dataset": dataset,
        "public_url": f"/d/{slug}",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    dashboard_path = DASHBOARDS_DIR / f"{dashboard_id}.json"

    try:
        dashboard_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if request.is_public:
            public_path = PUBLIC_DIR / f"{slug}.json"
            public_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    except Exception as exc:
        raise DashboardStorageError("Não foi possível salvar o dashboard.") from exc

    return payload


def save_dashboard_payload(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Atualiza um dashboard já criado em disco."""

    _ensure_dirs()

    dashboard_path = DASHBOARDS_DIR / f"{dashboard['id']}.json"
    dashboard["updated_at"] = datetime.now(UTC).isoformat()

    try:
        dashboard_path.write_text(
            json.dumps(dashboard, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if dashboard.get("is_public"):
            public_path = PUBLIC_DIR / f"{dashboard['slug']}.json"
            public_path.write_text(
                json.dumps(dashboard, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    except Exception as exc:
        raise DashboardStorageError("Não foi possível atualizar o dashboard.") from exc

    return dashboard


def list_dashboards() -> list[dict[str, Any]]:
    """Lista dashboards salvos."""

    _ensure_dirs()

    dashboards: list[dict[str, Any]] = []

    for file_path in sorted(DASHBOARDS_DIR.glob("*.json"), reverse=True):
        try:
            dashboards.append(json.loads(file_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue

    return dashboards


def get_dashboard(dashboard_id: str) -> dict[str, Any] | None:
    """Busca dashboard por ID."""

    _ensure_dirs()

    file_path = DASHBOARDS_DIR / f"{dashboard_id}.json"

    if not file_path.exists():
        return None

    return json.loads(file_path.read_text(encoding="utf-8"))


def get_public_dashboard(slug: str) -> dict[str, Any] | None:
    """Busca dashboard público por slug."""

    _ensure_dirs()

    safe_slug = slugify(slug)
    file_path = PUBLIC_DIR / f"{safe_slug}.json"

    if not file_path.exists():
        return None

    dashboard = json.loads(file_path.read_text(encoding="utf-8"))

    if not dashboard.get("is_public"):
        return None

    return dashboard
