import re
from typing import Any


KEYWORD_GROUPS: dict[str, set[str]] = {
    "sales": {
        "venda",
        "vendas",
        "vendeu",
        "vendido",
        "sales",
        "sale",
        "sold",
        "order",
        "orders",
        "pedido",
        "pedidos",
        "item",
        "items",
        "revenue",
        "receita",
        "valor",
        "preco",
        "price",
        "amount",
        "total",
    },
    "seller": {
        "vendedor",
        "vendedores",
        "seller",
        "sellers",
        "salesperson",
        "representante",
        "consultor",
    },
    "customer": {
        "cliente",
        "clientes",
        "customer",
        "customers",
        "buyer",
        "comprador",
    },
    "product": {
        "produto",
        "produtos",
        "product",
        "products",
        "sku",
        "categoria",
        "category",
    },
    "date": {
        "data",
        "date",
        "ano",
        "year",
        "mes",
        "month",
        "dia",
        "day",
        "periodo",
        "period",
        "timestamp",
    },
    "payment": {
        "pagamento",
        "pagamentos",
        "payment",
        "payments",
        "boleto",
        "cartao",
        "credit",
        "installments",
        "parcelas",
    },
    "location": {
        "cidade",
        "city",
        "estado",
        "state",
        "uf",
        "regiao",
        "region",
        "geolocation",
        "latitude",
        "longitude",
    },
}


ROLE_LABELS = {
    "sales": "Vendas / pedidos",
    "seller": "Vendedores",
    "customer": "Clientes",
    "product": "Produtos",
    "date": "Datas e períodos",
    "payment": "Pagamentos",
    "location": "Localização",
}


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()

    return {
        token
        for token in re.split(r"[^a-zA-Z0-9_]+", value.lower())
        if token
    }


def _matches_role(value: str, role: str) -> bool:
    normalized = value.lower()
    tokens = _tokens(normalized)

    return any(keyword in normalized or keyword in tokens for keyword in KEYWORD_GROUPS[role])


def infer_intent(description: str | None, objective: str | None) -> dict[str, Any]:
    text = f"{description or ''} {objective or ''}".strip()
    matched_roles: list[str] = []

    for role in KEYWORD_GROUPS:
        if _matches_role(text, role):
            matched_roles.append(role)

    if not matched_roles:
        matched_roles = ["sales", "date", "product"]

    return {
        "summary": text[:500],
        "roles": matched_roles,
        "labels": [ROLE_LABELS[role] for role in matched_roles],
    }


def infer_column_role(column: dict[str, Any]) -> str:
    name = str(column.get("name", ""))
    semantic_type = str(column.get("semantic_type", ""))

    if semantic_type == "date" or _matches_role(name, "date"):
        return "date"

    for role in ("seller", "sales", "payment", "customer", "product", "location"):
        if _matches_role(name, role):
            return role

    if semantic_type in {"currency", "decimal", "integer"}:
        return "metric"

    if semantic_type in {"category", "text"}:
        return "dimension"

    return semantic_type or "unknown"


def build_dataset_context(
    *,
    filename: str,
    dataset_id: str,
    profile: dict[str, Any],
    intent: dict[str, Any],
) -> dict[str, Any]:
    columns = profile.get("column_profiles", [])
    intent_roles = set(intent.get("roles", []))
    column_contexts = []
    file_roles: set[str] = set()
    relevance_score = 0

    for column in columns:
        column_role = infer_column_role(column)
        file_roles.add(column_role)

        score = 1
        if column_role in intent_roles:
            score += 4
        if _matches_role(str(column.get("name", "")), column_role):
            score += 2
        if column_role in {"date", "metric"}:
            score += 1

        relevance_score += score
        column_contexts.append(
            {
                "name": column.get("name"),
                "role": column_role,
                "semantic_type": column.get("semantic_type"),
                "confidence": column.get("type_confidence"),
                "unique_count": column.get("unique_count"),
                "missing_percentage": column.get("missing_percentage"),
                "sample_values": column.get("sample_values", []),
                "relevance_score": score,
            }
        )

    filename_lower = filename.lower()
    for role in KEYWORD_GROUPS:
        if _matches_role(filename_lower, role):
            file_roles.add(role)
            relevance_score += 5 if role in intent_roles else 2

    filters = [
        {
            "column": column["name"],
            "role": column["role"],
            "label": ROLE_LABELS.get(column["role"], column["role"].title()),
            "options": column.get("sample_values", [])[:8],
        }
        for column in column_contexts
        if column["role"] in {"date", "seller", "customer", "product", "location", "payment", "dimension"}
    ]

    return {
        "dataset_id": dataset_id,
        "filename": filename,
        "rows": profile.get("rows", 0),
        "columns": profile.get("columns", 0),
        "roles": sorted(file_roles),
        "role_labels": [ROLE_LABELS.get(role, role.title()) for role in sorted(file_roles)],
        "relevance_score": relevance_score,
        "columns_detected": sorted(
            column_contexts,
            key=lambda column: column["relevance_score"],
            reverse=True,
        ),
        "filters": filters,
    }


def build_session_context(session_data: dict[str, Any]) -> dict[str, Any]:
    intent = infer_intent(
        session_data.get("description"),
        session_data.get("objective"),
    )
    files = session_data.get("files", [])
    ranked_files = sorted(
        files,
        key=lambda file: file.get("analysis_context", {}).get("relevance_score", 0),
        reverse=True,
    )
    all_filters = []

    for file in ranked_files:
        for filter_item in file.get("analysis_context", {}).get("filters", []):
            all_filters.append(
                {
                    **filter_item,
                    "filename": file.get("filename"),
                }
            )

    return {
        "intent": intent,
        "files": [
            {
                "filename": file.get("filename"),
                "rows": file.get("row_count"),
                "columns": file.get("column_count"),
                "roles": file.get("analysis_context", {}).get("roles", []),
                "role_labels": file.get("analysis_context", {}).get("role_labels", []),
                "relevance_score": file.get("analysis_context", {}).get("relevance_score", 0),
                "columns_detected": file.get("analysis_context", {}).get("columns_detected", [])[:8],
            }
            for file in ranked_files
        ],
        "filters": all_filters[:24],
    }
