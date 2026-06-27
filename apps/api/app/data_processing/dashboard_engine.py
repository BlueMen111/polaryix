from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from app.core.config.settings import settings
from app.data_processing.readers import read_dataset


MAX_GROUP_ROWS = 250_000


def _safe_name(value: Any) -> str:
    return str(value) if value is not None and str(value) != "nan" else "-"


def _money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _widget(widget_type: str, title: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": uuid4().hex,
        "type": widget_type,
        "title": title,
        "config": config,
    }


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {column.lower(): column for column in columns}

    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]

    for column in columns:
        lower = column.lower()

        if any(candidate in lower for candidate in candidates):
            return column

    return None


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]


def _metric_column(df: pd.DataFrame) -> str | None:
    preferred = [
        "price",
        "payment_value",
        "total",
        "amount",
        "value",
        "valor",
        "receita",
        "vendas",
        "revenue",
        "sales",
    ]
    found = _find_column(list(df.columns), preferred)

    if found and pd.api.types.is_numeric_dtype(df[found]):
        return found

    numerics = [
        column
        for column in _numeric_columns(df)
        if not column.lower().endswith("_id")
        and "zip" not in column.lower()
        and "prefix" not in column.lower()
        and "lat" not in column.lower()
        and "lng" not in column.lower()
    ]

    return numerics[0] if numerics else None


def _date_column(df: pd.DataFrame) -> str | None:
    preferred = [
        "order_purchase_timestamp",
        "created_at",
        "date",
        "data",
        "timestamp",
        "purchase",
        "approved",
    ]

    return _find_column(list(df.columns), preferred)


def _read_session_frames(session_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    frames: dict[str, dict[str, Any]] = {}

    for file_data in session_data.get("files", []):
        file_id = file_data.get("file_id")
        extension = f".{file_data.get('format', '')}".replace("..", ".")

        if not file_id or extension == ".":
            continue

        path = settings.quarantine_path / f"{file_id}{extension}"

        if not path.exists():
            continue

        df = read_dataset(path=path, extension=extension)
        frames[file_data["filename"]] = {
            "file": file_data,
            "path": path,
            "df": df,
        }

    return frames


def _score_fact_table(filename: str, df: pd.DataFrame) -> int:
    columns = [column.lower() for column in df.columns]
    joined = " ".join(columns + [filename.lower()])
    score = 0

    for word in ["order", "pedido", "item", "payment", "pagamento", "sale", "venda"]:
        if word in joined:
            score += 8

    if _metric_column(df):
        score += 15

    if "seller_id" in columns:
        score += 15

    if "order_id" in columns:
        score += 12

    if "product_id" in columns:
        score += 8

    score += min(len(df), 100_000) // 20_000

    return score


def _choose_fact(frames: dict[str, dict[str, Any]]) -> tuple[str, pd.DataFrame] | None:
    candidates = [
        (filename, ref["df"], _score_fact_table(filename, ref["df"]))
        for filename, ref in frames.items()
        if "geolocation" not in filename.lower()
    ]

    if not candidates:
        return None

    filename, df, _score = max(candidates, key=lambda item: item[2])

    return filename, df


def _find_frame_with_column(
    frames: dict[str, dict[str, Any]],
    column: str,
    exclude: str | None = None,
) -> tuple[str, pd.DataFrame] | None:
    for filename, ref in frames.items():
        if filename == exclude:
            continue

        if column in ref["df"].columns:
            return filename, ref["df"]

    return None


def _find_frame_with_columns(
    frames: dict[str, dict[str, Any]],
    required_columns: set[str],
    exclude: str | None = None,
) -> tuple[str, pd.DataFrame] | None:
    for filename, ref in frames.items():
        if filename == exclude:
            continue

        if required_columns.issubset(set(ref["df"].columns)):
            return filename, ref["df"]

    return None


def _sample_for_grouping(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) <= MAX_GROUP_ROWS:
        return df

    return df.sample(MAX_GROUP_ROWS, random_state=7)


def _series_items(series: pd.Series, limit: int = 10) -> list[dict[str, Any]]:
    return [
        {
            "label": _safe_name(index),
            "value": round(float(value), 2),
        }
        for index, value in series.head(limit).items()
    ]


def _add_kpis(widgets: list[dict[str, Any]], fact: pd.DataFrame, metric: str | None) -> None:
    widgets.append(
        _widget(
            "kpi",
            "Registros analisados",
            {
                "value": f"{len(fact):,}".replace(",", "."),
                "description": "Linhas usadas como base principal do dashboard.",
            },
        )
    )

    if metric:
        total = float(pd.to_numeric(fact[metric], errors="coerce").fillna(0).sum())
        average = float(pd.to_numeric(fact[metric], errors="coerce").dropna().mean() or 0)

        widgets.append(
            _widget(
                "kpi",
                "Receita total estimada",
                {
                    "value": _money(total),
                    "description": f"Soma da coluna {metric}.",
                },
            )
        )
        widgets.append(
            _widget(
                "kpi",
                "Ticket médio",
                {
                    "value": _money(average),
                    "description": f"Média da coluna {metric}.",
                },
            )
        )


def _bar_from_group(
    widgets: list[dict[str, Any]],
    df: pd.DataFrame,
    group_column: str,
    metric: str,
    title: str,
    description: str,
    limit: int = 10,
) -> None:
    if group_column not in df.columns or metric not in df.columns:
        return

    working = _sample_for_grouping(df[[group_column, metric]].dropna())

    if working.empty:
        return

    values = (
        working.assign(**{metric: pd.to_numeric(working[metric], errors="coerce")})
        .dropna(subset=[metric])
        .groupby(group_column)[metric]
        .sum()
        .sort_values(ascending=False)
    )

    if values.empty:
        return

    widgets.append(
        _widget(
            "bar",
            title,
            {
                "description": description,
                "items": _series_items(values, limit=limit),
                "value_format": "currency",
            },
        )
    )


def _drilldown_city_by_state(
    widgets: list[dict[str, Any]],
    df: pd.DataFrame,
    state_column: str,
    city_column: str,
    metric: str,
) -> None:
    if state_column not in df.columns or city_column not in df.columns or metric not in df.columns:
        return

    working = _sample_for_grouping(df[[state_column, city_column, metric]].dropna())

    if working.empty:
        return

    working = working.assign(**{metric: pd.to_numeric(working[metric], errors="coerce")}).dropna(
        subset=[metric]
    )

    if working.empty:
        return

    grouped = (
        working.groupby([state_column, city_column])[metric]
        .sum()
        .sort_values(ascending=False)
    )
    items_by_parent: dict[str, list[dict[str, Any]]] = {}

    for state in sorted(working[state_column].dropna().unique()):
        state_values = grouped.loc[state] if state in grouped.index.get_level_values(0) else pd.Series(dtype=float)
        items_by_parent[_safe_name(state)] = _series_items(state_values.sort_values(ascending=False), limit=12)

    default_values = (
        working.groupby(city_column)[metric]
        .sum()
        .sort_values(ascending=False)
    )

    widgets.append(
        _widget(
            "drilldown_bar",
            "Vendas por cidade",
            {
                "description": f"Selecione um estado para ver as cidades com maior venda.",
                "parent_column": state_column,
                "child_column": city_column,
                "items": _series_items(default_values, limit=12),
                "items_by_parent": items_by_parent,
                "value_format": "currency",
            },
        )
    )


def _line_by_month(
    widgets: list[dict[str, Any]],
    df: pd.DataFrame,
    date_column: str,
    metric: str,
) -> None:
    if date_column not in df.columns or metric not in df.columns:
        return

    working = _sample_for_grouping(df[[date_column, metric]].dropna())
    dates = pd.to_datetime(working[date_column], errors="coerce")
    values = pd.to_numeric(working[metric], errors="coerce")
    grouped = (
        pd.DataFrame({"date": dates, "value": values})
        .dropna()
        .assign(month=lambda frame: frame["date"].dt.to_period("M").astype(str))
        .groupby("month")["value"]
        .sum()
        .sort_index()
    )

    if grouped.empty:
        return

    widgets.append(
        _widget(
            "line",
            "Evolução mensal",
            {
                "description": f"Soma de {metric} por mês usando {date_column}.",
                "items": _series_items(grouped, limit=18),
                "value_format": "currency",
            },
        )
    )


def _relationships(frames: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    result = []
    filenames = list(frames.keys())

    for index, left_name in enumerate(filenames):
        left_columns = set(frames[left_name]["df"].columns)

        for right_name in filenames[index + 1 :]:
            right_columns = set(frames[right_name]["df"].columns)

            for column in sorted(left_columns & right_columns):
                if column.endswith("_id") or column in {"order_id", "seller_id", "product_id", "customer_id"}:
                    result.append(
                        {
                            "left_file": left_name,
                            "right_file": right_name,
                            "column": column,
                        }
                    )

    return result[:30]


def build_automatic_dashboard(session_data: dict[str, Any]) -> dict[str, Any] | None:
    frames = _read_session_frames(session_data)
    fact_choice = _choose_fact(frames)

    if not fact_choice:
        return None

    fact_name, fact = fact_choice
    metric = _metric_column(fact)
    widgets: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []

    _add_kpis(widgets, fact, metric)

    working_fact = fact.copy()

    if metric:
        seller_col = _find_column(list(working_fact.columns), ["seller_id", "vendedor_id", "vendedor"])

        if seller_col:
            seller_ref = _find_frame_with_column(frames, seller_col, exclude=fact_name)

            if seller_ref:
                _seller_name, sellers = seller_ref
                seller_columns = [
                    column
                    for column in [seller_col, "seller_state", "seller_city", "vendedor", "seller_name"]
                    if column in sellers.columns
                ]
                working_fact = working_fact.merge(
                    sellers[seller_columns].drop_duplicates(subset=[seller_col]),
                    on=seller_col,
                    how="left",
                )

            seller_group = "seller_state" if "seller_state" in working_fact.columns else seller_col
            _bar_from_group(
                widgets,
                working_fact,
                seller_group,
                metric,
                "Vendas por vendedor",
                f"Ranking calculado por {seller_group} somando {metric}.",
            )

            filters.append(
                {
                    "column": seller_group,
                    "role": "seller",
                    "label": "Vendedor",
                    "options": sorted([_safe_name(value) for value in working_fact[seller_group].dropna().unique()[:20]]),
                    "filename": fact_name,
                }
            )

        product_col = _find_column(list(working_fact.columns), ["product_id", "produto_id", "produto"])

        if product_col:
            product_ref = _find_frame_with_column(frames, product_col, exclude=fact_name)

            if product_ref:
                _product_name, products = product_ref
                product_columns = [
                    column
                    for column in [product_col, "product_category_name", "category", "categoria"]
                    if column in products.columns
                ]
                working_fact = working_fact.merge(
                    products[product_columns].drop_duplicates(subset=[product_col]),
                    on=product_col,
                    how="left",
                )

                category_col = _find_column(list(working_fact.columns), ["product_category_name", "category", "categoria"])

                translation_ref = _find_frame_with_column(frames, "product_category_name_english")
                if category_col and translation_ref and "product_category_name" in translation_ref[1].columns:
                    translations = translation_ref[1]
                    working_fact = working_fact.merge(
                        translations[["product_category_name", "product_category_name_english"]].drop_duplicates(
                            subset=["product_category_name"]
                        ),
                        left_on=category_col,
                        right_on="product_category_name",
                        how="left",
                    )
                    category_col = "product_category_name_english"

                _bar_from_group(
                    widgets,
                    working_fact,
                    category_col or product_col,
                    metric,
                    "Itens mais vendidos",
                    f"Ranking por {'categoria' if category_col else product_col} somando {metric}.",
                )

                filters.append(
                    {
                        "column": category_col or product_col,
                        "role": "product",
                        "label": "Produto / categoria",
                        "options": sorted(
                            [_safe_name(value) for value in working_fact[category_col or product_col].dropna().unique()[:20]]
                        ),
                        "filename": fact_name,
                    }
                )

        order_col = _find_column(list(working_fact.columns), ["order_id", "pedido_id", "pedido"])

        if order_col:
            orders_ref = _find_frame_with_columns(
                frames,
                {order_col, "customer_id"},
                exclude=fact_name,
            ) or _find_frame_with_column(frames, order_col, exclude=fact_name)

            if orders_ref:
                _orders_name, orders = orders_ref
                order_columns = [column for column in orders.columns if column in {order_col, "customer_id", "order_purchase_timestamp", "order_status"}]
                working_fact = working_fact.merge(
                    orders[order_columns].drop_duplicates(subset=[order_col]),
                    on=order_col,
                    how="left",
                )

                date_col = _date_column(working_fact)
                if date_col:
                    _line_by_month(widgets, working_fact, date_col, metric)
                    filters.append(
                        {
                            "column": date_col,
                            "role": "date",
                            "label": "Período",
                            "options": ["Dia", "Mês", "Ano"],
                            "filename": fact_name,
                        }
                    )

                if "customer_id" in working_fact.columns:
                    customer_ref = _find_frame_with_columns(
                        frames,
                        {"customer_id", "customer_state"},
                        exclude=fact_name,
                    ) or _find_frame_with_columns(
                        frames,
                        {"customer_id", "customer_city"},
                        exclude=fact_name,
                    ) or _find_frame_with_column(frames, "customer_id", exclude=fact_name)

                    if customer_ref:
                        _customer_name, customers = customer_ref
                        customer_columns = [
                            column
                            for column in ["customer_id", "customer_state", "customer_city"]
                            if column in customers.columns
                        ]
                        working_fact = working_fact.merge(
                            customers[customer_columns].drop_duplicates(subset=["customer_id"]),
                            on="customer_id",
                            how="left",
                        )

                        state_col = "customer_state" if "customer_state" in working_fact.columns else None
                        if state_col:
                            _bar_from_group(
                                widgets,
                                working_fact,
                                state_col,
                                metric,
                                "Vendas por estado",
                                f"Receita por {state_col}, conectando pedidos e clientes.",
                            )
                            filters.append(
                                {
                                    "column": state_col,
                                    "role": "location",
                                    "label": "Estado",
                                    "options": sorted([_safe_name(value) for value in working_fact[state_col].dropna().unique()[:27]]),
                                    "filename": fact_name,
                                }
                            )

                            if "customer_city" in working_fact.columns:
                                _drilldown_city_by_state(
                                    widgets,
                                    working_fact,
                                    state_col,
                                    "customer_city",
                                    metric,
                                )

    payment_frame = next(
        ((name, ref["df"]) for name, ref in frames.items() if "payment" in name.lower() or "pagamento" in name.lower()),
        None,
    )

    if payment_frame:
        payment_name, payments = payment_frame
        payment_metric = _metric_column(payments)
        payment_type = _find_column(list(payments.columns), ["payment_type", "tipo_pagamento", "pagamento"])

        if payment_metric and payment_type:
            _bar_from_group(
                widgets,
                payments,
                payment_type,
                payment_metric,
                "Receita por forma de pagamento",
                f"Soma de {payment_metric} por {payment_type}.",
            )
            filters.append(
                {
                    "column": payment_type,
                    "role": "payment",
                    "label": "Pagamento",
                    "options": sorted([_safe_name(value) for value in payments[payment_type].dropna().unique()[:20]]),
                    "filename": payment_name,
                }
            )

    return {
        "primary_file": fact_name,
        "metric_column": metric,
        "widgets": widgets,
        "filters": filters,
        "relationships": _relationships(frames),
    }
