import re
from typing import Any

import pandas as pd


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?\d?[\d\s().-]{8,}$")
CURRENCY_PATTERN = re.compile(r"^\s*(R\$|\$|€|£)?\s*-?\d{1,3}([.,]\d{3})*([.,]\d{2})?\s*$")
PERCENTAGE_PATTERN = re.compile(r"^\s*-?\d+([.,]\d+)?\s*%\s*$")


def _safe_sample(series: pd.Series, limit: int = 100) -> pd.Series:
    """Retorna uma amostra segura sem valores nulos."""

    return series.dropna().astype(str).str.strip().head(limit)


def _ratio(matches: int, total: int) -> float:
    """Calcula proporção evitando divisão por zero."""

    if total == 0:
        return 0.0

    return matches / total


def detect_column_type(series: pd.Series) -> dict[str, Any]:
    """Detecta o tipo semântico provável de uma coluna."""

    sample = _safe_sample(series)
    total = len(sample)

    if total == 0:
        return {
            "semantic_type": "empty",
            "confidence": 1.0,
            "reason": "A coluna não possui valores preenchidos na amostra.",
        }

    original_dtype = str(series.dtype)

    if pd.api.types.is_bool_dtype(series):
        return {
            "semantic_type": "boolean",
            "confidence": 0.95,
            "reason": "A coluna possui tipo booleano nativo.",
        }

    if pd.api.types.is_integer_dtype(series):
        unique_ratio = series.nunique(dropna=True) / max(len(series.dropna()), 1)

        if unique_ratio > 0.9:
            return {
                "semantic_type": "possible_id",
                "confidence": 0.75,
                "reason": "A coluna é numérica inteira e possui muitos valores únicos.",
            }

        return {
            "semantic_type": "integer",
            "confidence": 0.9,
            "reason": "A coluna possui tipo inteiro nativo.",
        }

    if pd.api.types.is_float_dtype(series):
        return {
            "semantic_type": "decimal",
            "confidence": 0.9,
            "reason": "A coluna possui tipo decimal nativo.",
        }

    date_values = pd.to_datetime(sample, errors="coerce", dayfirst=True)
    date_ratio = float(date_values.notna().sum()) / total

    if date_ratio >= 0.8:
        return {
            "semantic_type": "date",
            "confidence": round(date_ratio, 2),
            "reason": "A maioria dos valores parece representar datas.",
        }

    percentage_matches = sum(bool(PERCENTAGE_PATTERN.match(value)) for value in sample)

    if _ratio(percentage_matches, total) >= 0.8:
        return {
            "semantic_type": "percentage",
            "confidence": round(_ratio(percentage_matches, total), 2),
            "reason": "A maioria dos valores possui formato de porcentagem.",
        }

    email_matches = sum(bool(EMAIL_PATTERN.match(value)) for value in sample)

    if _ratio(email_matches, total) >= 0.8:
        return {
            "semantic_type": "email",
            "confidence": round(_ratio(email_matches, total), 2),
            "reason": "A maioria dos valores possui formato de e-mail.",
        }

    phone_matches = sum(bool(PHONE_PATTERN.match(value)) for value in sample)

    if _ratio(phone_matches, total) >= 0.8:
        return {
            "semantic_type": "phone",
            "confidence": round(_ratio(phone_matches, total), 2),
            "reason": "A maioria dos valores parece representar telefone.",
        }

    currency_matches = sum(bool(CURRENCY_PATTERN.match(value)) for value in sample)

    if _ratio(currency_matches, total) >= 0.8:
        return {
            "semantic_type": "currency",
            "confidence": round(_ratio(currency_matches, total), 2),
            "reason": "A maioria dos valores possui formato monetário.",
        }

    normalized = sample.str.lower()
    boolean_words = {"true", "false", "sim", "não", "nao", "yes", "no", "0", "1"}
    boolean_matches = sum(value in boolean_words for value in normalized)

    if _ratio(boolean_matches, total) >= 0.8:
        return {
            "semantic_type": "boolean",
            "confidence": round(_ratio(boolean_matches, total), 2),
            "reason": "A maioria dos valores parece representar verdadeiro/falso.",
        }

    unique_count = series.nunique(dropna=True)
    non_null_count = len(series.dropna())

    if non_null_count > 0:
        unique_ratio = unique_count / non_null_count

        if unique_count <= 30 and unique_ratio <= 0.5:
            return {
                "semantic_type": "category",
                "confidence": 0.8,
                "reason": "A coluna possui baixa cardinalidade e parece categórica.",
            }

    return {
        "semantic_type": "text",
        "confidence": 0.6,
        "reason": f"Tipo original '{original_dtype}' tratado como texto genérico.",
    }