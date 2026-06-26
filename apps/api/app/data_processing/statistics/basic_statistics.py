from typing import Any

import pandas as pd


def generate_basic_statistics(df: pd.DataFrame) -> dict[str, Any]:
    """Gera estatísticas básicas para colunas numéricas e categóricas."""

    numeric_stats: dict[str, Any] = {}
    categorical_stats: dict[str, Any] = {}

    numeric_columns = df.select_dtypes(include=["number"]).columns

    for column in numeric_columns:
        series = df[column].dropna()

        if series.empty:
            continue

        numeric_stats[str(column)] = {
            "count": int(series.count()),
            "sum": float(series.sum()),
            "mean": float(series.mean()),
            "median": float(series.median()),
            "min": float(series.min()),
            "max": float(series.max()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
        }

    non_numeric_columns = df.select_dtypes(exclude=["number"]).columns

    for column in non_numeric_columns:
        series = df[column].dropna().astype(str)

        if series.empty:
            continue

        top_values = series.value_counts().head(10)

        categorical_stats[str(column)] = {
            "count": int(series.count()),
            "unique_count": int(series.nunique()),
            "top_values": [
                {"value": str(index), "count": int(value)}
                for index, value in top_values.items()
            ],
        }

    return {
        "numeric": numeric_stats,
        "categorical": categorical_stats,
    }