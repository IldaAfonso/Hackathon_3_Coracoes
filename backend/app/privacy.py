"""Privacidade: nenhum dado pessoal sai pela API.

O briefing diz que a base é anonimizada, mas a conferência achou, em
texto digitado à mão pelo técnico, ao menos um telefone real. Dado
digitado à mão vaza; por isso toda string livre passa por aqui antes de
ir ao navegador.

Limite honesto: expressões regulares pegam telefone, e-mail, CPF e CEP.
Nomes próprios e endereços por extenso NÃO são detectados; para isso
seria preciso um modelo de reconhecimento de entidades (ver
docs/ARQUITETURA.md).
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Telefone BR: (DDD) 9xxxx-xxxx, DDD 9xxxx xxxx, +55..., com ou sem
# separadores. Não casa número de série (12 ou mais dígitos seguidos).
_PHONE = r"(?<!\d)(?:\+?55[\s.-]?)?\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}(?!\d)"
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[e-mail]"),
    (re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)"), "[CPF]"),
    (re.compile(_PHONE), "[telefone]"),
    (re.compile(r"(?<!\d)\d{5}-\d{3}(?!\d)"), "[CEP]"),
]


def mask_text(value: Any) -> Any:
    """Troca telefone, e-mail, CPF e CEP por marcadores.

    Valores que não são texto voltam intactos.
    """
    if not isinstance(value, str) or not value:
        return value
    masked = value
    for pattern, token in _PATTERNS:
        masked = pattern.sub(token, masked)
    return masked


def mask_frame(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Mascara as colunas indicadas (as que existirem), sem mutar."""
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = out[column].map(mask_text)
    return out


def count_matches(series: pd.Series) -> int:
    """Quantas células de texto têm algum padrão de dado pessoal."""
    texts = series.dropna().astype(str)
    return int(texts.map(lambda s: mask_text(s) != s).sum())
