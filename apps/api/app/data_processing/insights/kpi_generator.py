from typing import Any

import pandas as pd


def generate_kpis(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Gera KPIs automáticos iniciais para o dataset."""

    kpis: list[dict[str, Any]] = []

    kpis.append(
        {
            "id": "total_rows",
            "title": "Total de linhas",
            "value": int(len(df)),
            "type": "count",
            "description": "Quantidade total de registros no dataset.",
        }
    )

    kpis.append(
        {
            "id": "total_columns",
            "title": "Total de colunas",
            "value": int(len(df.columns)),
            "type": "count",
            "description": "Quantidade total de campos disponíveis para análise.",
        }
    )

    duplicate_rows = int(df.duplicated().sum())

    kpis.append(
        {
            "id": "duplicate_rows",
            "title": "Linhas duplicadas",
            "value": duplicate_rows,
            "type": "quality",
            "description": "Quantidade de registros duplicados detectados.",
        }
    )

    total_cells = int(df.shape[0] * df.shape[1])
    missing_cells = int(df.isna().sum().sum())
    missing_percentage = round((missing_cells / total_cells) * 100, 2) if total_cells else 0

    kpis.append(
        {
            "id": "missing_percentage",
            "title": "Dados ausentes",
            "value": missing_percentage,
            "type": "quality",
            "suffix": "%",
            "description": "Percentual geral de células vazias no dataset.",
        }
    )

    numeric_columns = df.select_dtypes(include=["number"]).columns

    for column in numeric_columns[:5]:
        series = df[column].dropna()

        if series.empty:
            continue

        kpis.append(
            {
                "id": f"sum_{column}",
                "title": f"Soma de {column}",
                "value": float(series.sum()),
                "type": "metric",
                "source_column": str(column),
                "description": f"Soma automática da coluna numérica '{column}'.",
            }
        )

        kpis.append(
            {
                "id": f"avg_{column}",
                "title": f"Média de {column}",
                "value": float(series.mean()),
                "type": "metric",
                "source_column": str(column),
                "description": f"Média automática da coluna numérica '{column}'.",
            }
        )

    return kpis