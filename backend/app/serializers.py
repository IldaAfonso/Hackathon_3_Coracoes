"""Conversão de dados do pandas em JSON limpo.

NaN vira ``null``, datas viram texto ISO e tipos numpy viram tipos
nativos do Python.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def df_json(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Lista de registros seguros para JSON."""
    return json.loads(
        df.to_json(orient="records", date_format="iso", force_ascii=False)
    )


def value_json(value: Any) -> Any:
    """Um valor isolado (escalar, dict ou lista) seguro para JSON."""
    series = pd.Series([value], dtype=object)
    text = series.to_json(
        orient="values", date_format="iso", force_ascii=False
    )
    return json.loads(text)[0]
