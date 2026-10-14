"""
Normalização e decodificação do número de série das máquinas TRES.

Por que este módulo existe
--------------------------
O número de série é a "identidade" da máquina: é a única chave que liga os
chamados de uma mesma máquina ao longo do tempo (o DNA) e que diz de qual
versão de engenharia ela é (antes ou depois de uma melhoria).

Na base real ele é digitado à mão e chega com problemas como letras
minúsculas, espaços, a letra ``S`` trocada pelo dígito ``5`` (``G5P50002``)
e até textos como ``G5PS000DUPLICADO``. Este módulo limpa e valida.

Estrutura inferida dos dados (premissa documentada no README)
------------------------------------------------------------
Analisando ~30 mil chamados e cruzando com a data de instalação, foram
identificados dois formatos de 16 caracteres:

* **Legado** (G5 Passione até 2024): ``G5PS000 YY WW NNNNN``
  - ``YY``  = ano de fabricação (20 -> 2020, 21 -> 2021, ...)
  - ``WW``  = semana de fabricação (01..53)
  - ``NNNNN`` = sequencial
  Ex.: ``G5PS000210224033`` = fabricada em 2021, semana 02, seq. 24033.
  (Este é exatamente o número de corte do Informativo Técnico da bandeja.)

* **Novo** (G5 a partir de 2024 e todo o G4 Luna): ``MMMM VVV YY WW NNNNN``
  - ``MMMM`` = modelo (G5PS ou G4LN)
  - ``VVV``  = tensão (127 ou 220)
  Ex.: ``G4LN127232802098`` = Luna 127 V, 2023, semana 28.

A evidência para ``YY WW``: 99,95 % dos valores de ``WW`` estão entre 01 e
53, e a mediana da data de instalação cresce monotonicamente com ``YY``.
Isso é uma INFERÊNCIA a ser confirmada com o P&D da 3corações.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

# Correções de digitação observadas na base (ordem importa).
_TYPO_FIXES: tuple[tuple[str, str], ...] = (
    ("G5P5", "G5PS"),  # dígito 5 digitado no lugar da letra S
    ("G4L N", "G4LN"),
)

_LEGACY_PATTERN = re.compile(r"^(G5PS)000(\d{2})(\d{2})(\d{5})$")
_NEW_PATTERN = re.compile(r"^(G5PS|G4LN)(127|220)(\d{2})(\d{2})(\d{5})$")

_MODEL_BY_PREFIX: dict[str, str] = {"G5PS": "Passione", "G4LN": "Luna"}


@dataclass(frozen=True)
class SerialInfo:
    """Resultado da decodificação de um número de série.

    Attributes:
        serie: Série normalizada (maiúsculas, sem espaços).
        valida: ``True`` se a série casou com um dos formatos conhecidos.
        formato: ``"legado"``, ``"novo"`` ou ``"invalido"``.
        modelo_serie: Modelo inferido pelo prefixo (Passione/Luna).
        ano_fab: Ano de fabricação (ex.: 2021) ou ``None``.
        semana_fab: Semana de fabricação (1..53) ou ``None``.
        sequencial: Número sequencial de produção ou ``None``.
        chave_ordem: Inteiro ``AAAASSNNNNN`` que permite comparar séries
            ("a partir da série X") independentemente do formato.
    """

    serie: str
    valida: bool
    formato: str
    modelo_serie: str | None = None
    ano_fab: int | None = None
    semana_fab: int | None = None
    sequencial: int | None = None
    chave_ordem: int | None = None


def normalize_serial(raw: object) -> str:
    """Padroniza a série digitada: maiúsculas, sem espaços e com erros
    de digitação conhecidos corrigidos.

    Args:
        raw: Valor bruto vindo da planilha (pode ser ``NaN`` ou número).

    Returns:
        Série normalizada, ou string vazia se o valor for nulo.
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    text = re.sub(r"\s+", "", str(raw).upper().strip())
    for wrong, right in _TYPO_FIXES:
        if text.startswith(wrong):
            text = right + text[len(wrong):]
    return text


def _order_key(year: int, week: int, seq: int) -> int:
    """Cria uma chave inteira ordenável AAAASSNNNNN (ano, semana, seq)."""
    return year * 10_000_000 + week * 100_000 + seq


def parse_serial(raw: object) -> SerialInfo:
    """Decodifica uma série nos campos de fabricação.

    A validação é deliberadamente conservadora: semanas fora de 1..53 ou
    anos fora de 2018..2035 tornam a série inválida, porque nesses casos a
    comparação "antes/depois" de uma melhoria não seria confiável.

    Args:
        raw: Valor bruto da coluna "Número de série".

    Returns:
        ``SerialInfo`` preenchido; ``valida=False`` quando não decodificável.
    """
    serie = normalize_serial(raw)
    match = _LEGACY_PATTERN.match(serie)
    formato = "legado"
    if match:
        prefix, yy, ww, seq = match.groups()
    else:
        match = _NEW_PATTERN.match(serie)
        formato = "novo"
        if not match:
            return SerialInfo(serie=serie, valida=False, formato="invalido")
        prefix, _voltage, yy, ww, seq = match.groups()

    year, week, sequence = 2000 + int(yy), int(ww), int(seq)
    if not (1 <= week <= 53 and 2018 <= year <= 2035):
        return SerialInfo(serie=serie, valida=False, formato="invalido")

    return SerialInfo(
        serie=serie,
        valida=True,
        formato=formato,
        modelo_serie=_MODEL_BY_PREFIX[prefix],
        ano_fab=year,
        semana_fab=week,
        sequencial=sequence,
        chave_ordem=_order_key(year, week, sequence),
    )


def serial_order_key(serial: str) -> int | None:
    """Atalho: devolve apenas a chave de ordenação de uma série.

    Usado para comparar uma máquina com o "número de série de corte" de
    uma melhoria (ex.: bandeja de cápsulas a partir de G5PS000210224033).
    """
    return parse_serial(serial).chave_ordem


def decode_serial_column(series: pd.Series) -> pd.DataFrame:
    """Aplica :func:`parse_serial` a uma coluna inteira de forma eficiente.

    Como há muitas séries repetidas (a mesma máquina abre vários chamados),
    a decodificação é feita uma vez por valor único e depois mapeada.

    Args:
        series: Coluna com as séries brutas.

    Returns:
        DataFrame com as colunas de :class:`SerialInfo`, mesmo índice.
    """
    # A chave é o texto normalizado: evita o problema de NaN != NaN em dict.
    normalized = series.map(normalize_serial)
    decoded = {s: parse_serial(s).__dict__ for s in normalized.unique()}
    return pd.DataFrame([decoded[s] for s in normalized], index=series.index)
