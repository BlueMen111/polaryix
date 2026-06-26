from typing import Any

import pandas as pd

from app.data_processing.profiling.column_type_detector import detect_column_type


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Gera um perfil inicial e seguro do dataset."""

    total_rows = len(df)
    total_columns = len(df.columns)

    columns: list[dict[str, Any]] = []

    for column_name in df.columns:
        series = df[column_name]

        missing_count = int(series.isna().sum())
        missing_percentage = round((missing_count / total_rows) * 100, 2) if total_rows else 0
        detected_type = detect_column_type(series)

        columns.append(
            {
                "name": str(column_name),
                "dtype": str(series.dtype),
                "semantic_type": detected_type["semantic_type"],
                "type_confidence": detected_type["confidence"],
                "type_reason": detected_type["reason"],
                "missing_count": missing_count,
                "missing_percentage": missing_percentage,
                "unique_count": int(series.nunique(dropna=True)),
                "sample_values": [
                    str(value)
                    for value in series.dropna().head(5).tolist()
                ],
            }
        )

    duplicate_rows = int(df.duplicated().sum())

    return {
        "rows": total_rows,
        "columns": total_columns,
        "duplicate_rows": duplicate_rows,
        "column_profiles": columns,
    }