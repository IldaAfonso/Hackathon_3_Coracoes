"""Funções pequenas compartilhadas pelas rotas."""

from __future__ import annotations

import pandas as pd

from app import bootstrap
from app.boletim import make_code
from app.settings import MIN_GROUP_SIZE, SIGNIFICANCE_LEVEL
from app.state import state
from dna_maquina import impact


def improvements() -> list[impact.Improvement]:
    """Catálogo de melhorias do P&D (arquivo gravável no volume).

    Melhorias antigas, sem código, recebem um na leitura (pela ordem
    do catálogo); o arquivo só muda quando o P&D registra.
    """
    items = impact.load_improvements(bootstrap.IMPROVEMENTS_PATH)
    taken = [i.codigo for i in items]
    for item in items:
        if not item.codigo:
            item.codigo = make_code(item.modelo, item.tipo, taken)
            taken.append(item.codigo)
    return items


def as_number(value: float) -> float | None:
    """Converte NaN em None, para o JSON sair como `null`."""
    return None if pd.isna(value) else float(value)


def verdict(result: impact.CohortResult) -> str:
    """Traduz a estatística em um veredito direto para o P&D.

    Amostra pequena nunca vira conclusão: abaixo de ``MIN_GROUP_SIZE``
    chamados num dos grupos, a resposta honesta é "insuficiente".
    """
    too_small = result.tabela["n"].min() < MIN_GROUP_SIZE
    if pd.isna(result.p_valor) or too_small:
        return "Amostra insuficiente"
    if result.p_valor < SIGNIFICANCE_LEVEL:
        return "Funcionou" if result.reducao_relativa > 0 else "Piorou"
    return "Sem efeito mensurável"


def evidence_origin(item: impact.Improvement) -> dict:
    """De onde vem o vínculo entre chamado e melhoria.

    Mudança de fábrica é ligada pela série (não depende de texto). Kit
    de campo é "registrado" quando chamados trazem o código da melhoria
    na coluna ``codigo_melhoria`` e "inferido" (por palavras do técnico)
    quando nenhum traz.
    """
    if item.tipo == "corte_serie":
        return {"origem": "serie", "chamados_com_codigo": 0}
    df = state.df
    sent = 0
    if item.codigo and "codigo_melhoria" in df:
        sent = int(df["codigo_melhoria"].eq(item.codigo).sum())
    origin = "registrada" if sent else "inferida"
    return {"origem": origin, "chamados_com_codigo": sent}
