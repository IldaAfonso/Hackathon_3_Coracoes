"""
Estoque × melhoria: atualizar as máquinas ANTES de serem vendidas.

Pergunta de negócio
-------------------
Quando o P&D implanta uma melhoria, as máquinas já fabricadas e ainda
paradas no estoque (centros de distribuição, assistência, devoluções)
saem para o consumidor SEM ela, e voltam como chamado. Este módulo faz o
levantamento: para cada melhoria, quais máquinas em estoque precisam
recebê-la antes da venda, onde estão e quantas peças separar.

É outra fonte de dados (a posição de estoque, por número de série), que
se liga ao resto do DNA pela mesma chave: a série.

Regras (premissas documentadas no README, P10 e P11)
----------------------------------------------------
* **Mudança de fábrica** (``corte_serie``): a máquina já sai com a
  melhoria quando a série é igual ou posterior à série de corte
  (comparação pela chave ``AAAASSNNNNN``). Antes do corte: pendente.
* **Kit de campo** (``retrofit_campo``): a data do boletim é o corte de
  fábrica (decisão da equipe com o P&D: "usar a data da ficha de
  melhoria e relacionar com a semana/ano da série"). Fabricada na semana
  do boletim ou depois: já sai com a melhoria. Antes: pendente.
* **Já aplicada**: a coluna "Melhorias aplicadas" do arquivo de estoque
  traz o código do projeto da melhoria, ou alguém marcou na tela.
* **Verificar**: série ilegível; sem ano/semana não dá para decidir.
* Só entra o que está **em estoque** ou **reservado** (vendida sai).
* Melhoria de um modelo não se aplica ao outro (Passione × Luna).

Funções puras: recebem DataFrame e devolvem DataFrame/dict, sem I/O
(o I/O fica em :func:`read_stock_file`).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from dna_maquina.impact import Improvement
from dna_maquina.serial import parse_serial, serial_order_key

# Cabeçalho do arquivo de estoque (como vem do ERP/WMS) -> nome interno.
# Só "Número de série" é obrigatório; o resto enriquece o levantamento.
STOCK_COLUMN_MAP: dict[str, str] = {
    "Número de série": "serie",
    "Modelo": "modelo",
    "Local": "local",
    "Data de entrada no estoque": "data_entrada",
    "Situação": "situacao",
    "Melhorias aplicadas": "melhorias_aplicadas",
}
REQUIRED_STOCK_COLUMNS: tuple[str, ...] = ("Número de série",)

IN_STOCK = ("em estoque", "reservada")
"""Situações que contam como "ainda não vendida"."""

STATUS_LABEL: dict[str, str] = {
    "pendente": "Aplicar antes de vender",
    "aplicada": "Já aplicada no estoque",
    "de_fabrica": "Já sai de fábrica com a melhoria",
    "verificar": "Verificar: série ilegível",
}
"""Rótulo de negócio de cada situação (o que a tela mostra)."""

CODE_SEPARATORS = r"[;,\s]+"
"""Separadores aceitos na coluna "Melhorias aplicadas"."""


class StockSchemaError(ValueError):
    """O arquivo de estoque não tem as colunas mínimas."""


@dataclass(frozen=True)
class StockSurvey:
    """Resultado do levantamento de uma melhoria no estoque.

    Attributes:
        maquinas: Uma linha por máquina do modelo da melhoria, com a
            coluna ``status`` (pendente, aplicada, de_fabrica,
            verificar).
        regra: Texto que explica, em português, o critério usado.
        corte_ordem: Chave ``AAAASSNNNNN`` do corte de fábrica.
    """

    maquinas: pd.DataFrame
    regra: str
    corte_ordem: int


def _parse_dates(values: pd.Series) -> pd.Series:
    """Datas ISO (``2026-08-03``) ou brasileiras (``03/08/2026``).

    Lê primeiro como ISO; o que sobrar tenta como dia/mês/ano, para não
    trocar dia e mês de datas ISO (erro já visto na base de chamados).
    """
    iso = pd.to_datetime(values, errors="coerce", format="ISO8601")
    br = pd.to_datetime(values, errors="coerce", format="%d/%m/%Y")
    return iso.fillna(br)


def clean_stock(raw: pd.DataFrame) -> pd.DataFrame:
    """Padroniza a posição de estoque e decodifica a série.

    Linhas vendidas são mantidas (para o total) mas marcadas; a série
    é decodificada com as mesmas regras dos chamados, então ano e
    semana de fabricação valem igual nas duas fontes.

    Raises:
        StockSchemaError: sem a coluna "Número de série".
    """
    missing = [c for c in REQUIRED_STOCK_COLUMNS if c not in raw.columns]
    if missing:
        raise StockSchemaError(
            "Faltam colunas no arquivo de estoque: " + ", ".join(missing))
    df = raw.rename(columns=STOCK_COLUMN_MAP)
    df = df[[c for c in STOCK_COLUMN_MAP.values() if c in df.columns]].copy()
    for column in STOCK_COLUMN_MAP.values():
        if column not in df.columns:
            df[column] = None
    info = df["serie"].map(parse_serial)
    df["serie"] = info.map(lambda i: i.serie)
    df["serie_valida"] = info.map(lambda i: i.valida)
    df["ano_fab"] = info.map(lambda i: i.ano_fab)
    df["semana_fab"] = info.map(lambda i: i.semana_fab)
    df["chave_ordem"] = info.map(lambda i: i.chave_ordem)
    by_serial = info.map(lambda i: i.modelo_serie)
    df["modelo"] = df["modelo"].where(df["modelo"].notna(), by_serial)
    df["modelo"] = df["modelo"].astype("string").str.strip().str.title()
    df["local"] = df["local"].fillna("Não informado").astype(str).str.strip()
    df["situacao"] = (df["situacao"].fillna("em estoque").astype(str)
                      .str.strip().str.lower())
    df["data_entrada"] = _parse_dates(df["data_entrada"])
    df["melhorias_aplicadas"] = df["melhorias_aplicadas"].fillna("").map(
        lambda text: frozenset(
            code.upper() for code in re.split(CODE_SEPARATORS, str(text))
            if code))
    df["em_estoque"] = df["situacao"].isin(IN_STOCK)
    return df.drop_duplicates(subset="serie", keep="last").reset_index(
        drop=True)


def cutoff_key(item: Improvement) -> int:
    """Chave ``AAAASSNNNNN`` a partir da qual a fábrica já entrega a
    melhoria: a série de corte (mudança de fábrica) ou a semana ISO do
    boletim com sequencial zero (kit de campo)."""
    if item.tipo == "corte_serie" and item.serie_inicial:
        key = serial_order_key(item.serie_inicial)
        if key is not None and key > 0:
            return int(key)
    when = datetime.strptime(item.data_documento, "%Y-%m-%d").date()
    year, week, _ = when.isocalendar()
    return year * 10_000_000 + week * 100_000


def survey(stock: pd.DataFrame, item: Improvement,
           marks: set[tuple[str, str]] | None = None,
           today: date | None = None) -> StockSurvey:
    """Levanta a situação de cada máquina em estoque para a melhoria.

    Args:
        stock: Saída de :func:`clean_stock`.
        item: A melhoria (do catálogo do P&D).
        marks: Pares ``(serie, codigo)`` marcados como aplicados.
        today: Data de referência para "dias em estoque" (testes).

    Returns:
        :class:`StockSurvey` com uma linha por máquina do modelo, em
        estoque, ordenada para o trabalho: pendentes primeiro, e entre
        elas as que entraram há mais tempo (saem antes, pelo FIFO).
    """
    marks = marks or set()
    today = today or date.today()
    code = (item.codigo or "").upper()
    cut = cutoff_key(item)
    df = stock[stock["em_estoque"] & stock["modelo"].eq(item.modelo)].copy()

    applied = df.apply(
        lambda r: code in r["melhorias_aplicadas"]
        or (r["serie"], code) in marks, axis=1) if len(df) else pd.Series(
        dtype=bool)
    factory = df["chave_ordem"].fillna(-1).astype("int64") >= cut
    df["status"] = "pendente"
    df.loc[factory, "status"] = "de_fabrica"
    df.loc[~df["serie_valida"].astype(bool), "status"] = "verificar"
    df.loc[applied.astype(bool), "status"] = "aplicada"
    df["situacao_label"] = df["status"].map(STATUS_LABEL)
    df["dias_em_estoque"] = (
        (pd.Timestamp(today) - df["data_entrada"]).dt.days.astype("Int64"))
    order = {"pendente": 0, "verificar": 1, "aplicada": 2, "de_fabrica": 3}
    df["_ordem"] = df["status"].map(order)
    df = df.sort_values(["_ordem", "data_entrada", "chave_ordem"],
                        na_position="last").drop(columns="_ordem")
    return StockSurvey(maquinas=df.reset_index(drop=True),
                       regra=_rule_text(item, cut), corte_ordem=cut)


def _rule_text(item: Improvement, cut: int) -> str:
    """Explica o critério em linguagem de negócio (aparece na tela)."""
    year, week = cut // 10_000_000, (cut // 100_000) % 100
    if item.tipo == "corte_serie" and item.serie_inicial:
        return (f"Mudança de fábrica a partir da série {item.serie_inicial} "
                f"({year}, semana {week:02d}). Máquinas em estoque com série "
                "anterior saíram da fábrica sem a melhoria: aplicar antes "
                "de vender.")
    return (f"Kit de campo do boletim de {item.data_documento}. Premissa: a "
            f"fábrica incorporou a melhoria a partir da semana {week:02d}/"
            f"{year} (data do boletim × semana da série). Máquinas em "
            "estoque fabricadas antes disso: aplicar o kit antes de vender.")


def summarize(result: StockSurvey, item: Improvement) -> dict:
    """Contagens para o P&D decidir e para o Pós-venda planejar.

    Returns:
        ``por_status``, ``por_local`` (pendentes por local),
        ``pecas_necessarias`` (peça do boletim × máquinas pendentes)
        e ``pendentes``.
    """
    df = result.maquinas
    pending = df[df["status"].eq("pendente")]
    by_status = {key: int(df["status"].eq(key).sum()) for key in STATUS_LABEL}
    by_place = (pending.groupby("local").size().sort_values(ascending=False)
                .rename("pendentes").reset_index().to_dict("records"))
    pieces = [{"peca": piece, "quantidade": int(len(pending))}
              for piece in dict.fromkeys(item.pecas)]
    return {"por_status": by_status, "por_local": by_place,
            "pecas_necessarias": pieces, "pendentes": int(len(pending)),
            "total_do_modelo": int(len(df))}


def stock_overview(stock: pd.DataFrame) -> dict:
    """Retrato da fonte de estoque: quanto há, de que modelo e onde."""
    live = stock[stock["em_estoque"]]
    return {
        "linhas": int(len(stock)),
        "em_estoque": int(len(live)),
        "vendidas_ignoradas": int((~stock["em_estoque"]).sum()),
        "series_ilegiveis": int((~live["serie_valida"].astype(bool)).sum()),
        "por_modelo": {str(k): int(v) for k, v in
                       live["modelo"].value_counts().items()},
        "por_local": {str(k): int(v) for k, v in
                      live["local"].value_counts().items()},
    }


def read_stock_file(content: bytes, filename: str) -> pd.DataFrame:
    """Lê o arquivo enviado (.xlsx ou .csv com ``;`` ou ``,``)."""
    name = filename.lower()
    if name.endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(content), dtype=str)
    if name.endswith(".csv"):
        text = content.decode("utf-8-sig", errors="replace")
        sep = ";" if text.split("\n", 1)[0].count(";") else ","
        return pd.read_csv(io.StringIO(text), sep=sep, dtype=str)
    raise StockSchemaError("Envie um arquivo .xlsx ou .csv.")


def to_csv_text(stock: pd.DataFrame) -> str:
    """Grava a posição de estoque no formato do arquivo de entrada.

    O backend guarda a última importação assim (cabeçalho original,
    ``;`` e UTF-8 com BOM), então o mesmo arquivo abre no Excel.
    """
    out = stock.copy()
    out["melhorias_aplicadas"] = out["melhorias_aplicadas"].map(
        lambda codes: ";".join(sorted(codes)))
    out["data_entrada"] = out["data_entrada"].dt.strftime("%Y-%m-%d")
    reverse = {v: k for k, v in STOCK_COLUMN_MAP.items()}
    out = out[list(reverse)].rename(columns=reverse)
    return "﻿" + out.to_csv(sep=";", index=False)


TEMPLATE_CSV = (
    "﻿" + ";".join(STOCK_COLUMN_MAP) + "\n"
    "G5PS000210112345;Passione;CD Sudeste;2026-08-03;em estoque;\n"
    "G4LN220263400123;Luna;CD Nordeste;2026-09-21;reservada;\n"
)
"""Modelo de arquivo para quem vai exportar o estoque do ERP/WMS."""
