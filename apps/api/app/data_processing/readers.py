from pathlib import Path

import pandas as pd


class DatasetReadError(ValueError):
    """Erro lançado quando o dataset não pode ser lido com segurança."""


def read_dataset(path: Path, extension: str) -> pd.DataFrame:
    """Lê datasets suportados e retorna um DataFrame."""

    try:
        if extension == ".csv":
            return pd.read_csv(path)

        if extension == ".txt":
            return pd.read_csv(path, sep=None, engine="python")

        if extension == ".json":
            return pd.read_json(path)

        if extension in {".xls", ".xlsx"}:
            return pd.read_excel(path)

        if extension == ".parquet":
            return pd.read_parquet(path)

    except Exception as exc:
        raise DatasetReadError("Não foi possível ler o dataset enviado.") from exc

    raise DatasetReadError(f"Formato não suportado: {extension}")