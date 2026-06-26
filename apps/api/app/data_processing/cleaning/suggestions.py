from typing import Any

import pandas as pd


def generate_cleaning_suggestions(
    df: pd.DataFrame,
    column_profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Gera sugestões iniciais de limpeza para o dataset."""

    suggestions: list[dict[str, Any]] = []

    duplicate_count = int(df.duplicated().sum())

    if duplicate_count > 0:
        suggestions.append(
            {
                "type": "duplicate_rows",
                "severity": "medium",
                "title": "Linhas duplicadas encontradas",
                "description": f"Foram encontradas {duplicate_count} linhas duplicadas.",
                "recommended_action": (
                    "Revisar e remover duplicatas caso elas não sejam intencionais."
                ),
            }
        )

    for profile in column_profiles:
        column_name = profile["name"]
        missing_percentage = profile["missing_percentage"]
        semantic_type = profile["semantic_type"]

        if missing_percentage > 0:
            severity = "low"

            if missing_percentage >= 40:
                severity = "high"
            elif missing_percentage >= 10:
                severity = "medium"

            suggestions.append(
                {
                    "type": "missing_values",
                    "severity": severity,
                    "column": column_name,
                    "title": "Valores ausentes detectados",
                    "description": (
                        f"A coluna '{column_name}' possui "
                        f"{missing_percentage}% de valores ausentes."
                    ),
                    "recommended_action": (
                        "Avaliar preenchimento, remoção ou tratamento específico "
                        "para valores ausentes."
                    ),
                }
            )

        if semantic_type == "date":
            suggestions.append(
                {
                    "type": "standardize_dates",
                    "severity": "low",
                    "column": column_name,
                    "title": "Padronização de datas",
                    "description": f"A coluna '{column_name}' parece conter datas.",
                    "recommended_action": (
                        "Padronizar para ISO 8601 antes de gerar dashboards "
                        "e filtros temporais."
                    ),
                }
            )

        if semantic_type == "currency":
            suggestions.append(
                {
                    "type": "standardize_currency",
                    "severity": "medium",
                    "column": column_name,
                    "title": "Padronização monetária",
                    "description": (
                        f"A coluna '{column_name}' parece conter valores monetários."
                    ),
                    "recommended_action": (
                        "Converter valores para número decimal e armazenar moeda "
                        "separadamente quando necessário."
                    ),
                }
            )

        if semantic_type == "percentage":
            suggestions.append(
                {
                    "type": "standardize_percentage",
                    "severity": "low",
                    "column": column_name,
                    "title": "Padronização de porcentagem",
                    "description": (
                        f"A coluna '{column_name}' parece conter porcentagens."
                    ),
                    "recommended_action": (
                        "Converter porcentagens para formato numérico consistente."
                    ),
                }
            )

    return suggestions