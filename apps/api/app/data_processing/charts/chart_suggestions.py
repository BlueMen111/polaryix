from typing import Any


def suggest_charts(column_profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sugere gráficos iniciais com base nos tipos semânticos detectados."""

    suggestions: list[dict[str, Any]] = []

    numeric_columns = [
        column["name"]
        for column in column_profiles
        if column["semantic_type"] in {"integer", "decimal", "currency", "percentage"}
    ]

    category_columns = [
        column["name"]
        for column in column_profiles
        if column["semantic_type"] in {"category", "boolean", "text"}
    ]

    date_columns = [
        column["name"]
        for column in column_profiles
        if column["semantic_type"] == "date"
    ]

    for category in category_columns[:5]:
        suggestions.append(
            {
                "type": "bar",
                "title": f"Distribuição por {category}",
                "description": f"Gráfico de barras para comparar frequência por '{category}'.",
                "x": category,
                "y": "count",
                "recommended_for_dashboard": True,
            }
        )

    for numeric in numeric_columns[:5]:
        suggestions.append(
            {
                "type": "histogram",
                "title": f"Distribuição de {numeric}",
                "description": (
                    f"Histograma para entender a distribuição da coluna '{numeric}'."
                ),
                "x": numeric,
                "recommended_for_dashboard": True,
            }
        )

    if date_columns and numeric_columns:
        suggestions.append(
            {
                "type": "line",
                "title": f"Evolução de {numeric_columns[0]} por {date_columns[0]}",
                "description": "Gráfico de linha recomendado para análise temporal.",
                "x": date_columns[0],
                "y": numeric_columns[0],
                "recommended_for_dashboard": True,
            }
        )

    if category_columns and numeric_columns:
        suggestions.append(
            {
                "type": "bar",
                "title": f"{numeric_columns[0]} por {category_columns[0]}",
                "description": (
                    "Gráfico de barras recomendado para comparar uma métrica por categoria."
                ),
                "x": category_columns[0],
                "y": numeric_columns[0],
                "aggregation": "sum",
                "recommended_for_dashboard": True,
            }
        )

    return suggestions