"""
Histórico por máquina — o "DNA" propriamente dito.

Responde à Dor 07 do P&D ("não existe um histórico de cada máquina") e às
personas Carlos (técnico) e Rafael (Customer Success), que precisam saber,
ANTES do atendimento, o que já aconteceu com aquela máquina.

Conceitos calculados
--------------------
* **Ordem do chamado na máquina** (1º, 2º, 3º ...).
* **Dias desde o chamado anterior** da mesma máquina.
* **Reincidência**: o chamado é uma volta do problema quando a mesma
  máquina já teve outro chamado nos últimos
  :data:`config.REINCIDENCE_WINDOW_DAYS` dias. É o indicador da persona
  Juliana: "Já consertaram uma vez. Por que vazou de novo?".
* **Mesmo sintoma**: a reincidência repete o mesmo sintoma relatado.
* **Reparo efetivo**: um atendimento cujo problema NÃO voltou na janela.

Limitação importante (documentada no README): a base cobre só chamados
abertos entre jan/2025 e set/2026; o histórico anterior não está disponível,
então o "1º chamado" é o primeiro DENTRO DA JANELA observada.
"""

from __future__ import annotations

import pandas as pd

from dna_maquina import config


def add_machine_sequence(df: pd.DataFrame,
                         window_days: int = config.REINCIDENCE_WINDOW_DAYS
                         ) -> pd.DataFrame:
    """Adiciona a sequência temporal de cada máquina a cada chamado.

    Só séries válidas entram no encadeamento; registros com série inválida
    recebem valores nulos (não é possível saber a que máquina pertencem).

    Args:
        df: Base canônica com ``serie``, ``valida``, ``data_abertura``,
            ``sintoma_cs`` e ``tem_reparo_registrado``.
        window_days: Janela de reincidência em dias.

    Returns:
        Cópia com ``ordem_na_maquina``, ``dias_desde_anterior``,
        ``reincidente``, ``reincidente_mesmo_sintoma``,
        ``dias_ate_proximo`` e ``problema_voltou``.
    """
    out = df.sort_values(["serie", "data_abertura", "case_id"]).copy()
    valid = out["valida"].fillna(False).astype(bool)
    grouped = out[valid].groupby("serie", sort=False)

    out.loc[valid, "ordem_na_maquina"] = grouped.cumcount() + 1
    prev_date = grouped["data_abertura"].shift(1)
    next_date = grouped["data_abertura"].shift(-1)
    prev_symptom = grouped["sintoma_cs"].shift(1)

    out.loc[valid, "dias_desde_anterior"] = (
        out.loc[valid, "data_abertura"] - prev_date
    ).dt.days
    out.loc[valid, "dias_ate_proximo"] = (
        next_date - out.loc[valid, "data_abertura"]
    ).dt.days

    out["reincidente"] = out["dias_desde_anterior"].le(window_days)
    out["reincidente_mesmo_sintoma"] = out["reincidente"] & (
        out["sintoma_cs"] == prev_symptom.reindex(out.index)
    )
    # Visão "para frente": depois DESTE atendimento, a máquina voltou?
    out["problema_voltou"] = out["dias_ate_proximo"].le(window_days)
    return out.sort_index()


def _most_frequent(df: pd.DataFrame, column: str) -> pd.Series:
    """Valor mais frequente de ``column`` por série (moda vetorizada)."""
    counts = (df.groupby(["serie", column]).size().reset_index(name="n")
              .sort_values(["serie", "n"]))
    return counts.drop_duplicates("serie", keep="last").set_index(
        "serie")[column]


def machine_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por máquina: a "ficha" resumida do DNA.

    Args:
        df: Base enriquecida (após :func:`add_machine_sequence`).

    Returns:
        DataFrame indexado por ``serie`` com modelo, ano de fabricação,
        total de chamados, reincidências, sintomas e causas mais comuns,
        e se a máquina já recebeu a adaptação hidráulica.
    """
    valid = df[df["valida"].fillna(False).astype(bool)].assign(
        vazamento=lambda d: d["sintoma_cs"].eq(config.LEAK_SYMPTOM))
    summary = valid.groupby("serie").agg(
        modelo=("modelo", "first"),
        ano_fab=("ano_fab", "first"),
        semana_fab=("semana_fab", "first"),
        data_instalacao=("data_instalacao", "first"),
        chamados=("case_id", "size"),
        primeiro=("data_abertura", "min"),
        ultimo=("data_abertura", "max"),
        reincidencias=("reincidente", "sum"),
        vazamentos=("vazamento", "sum"),
        recebeu_adaptacao=("fez_adaptacao_hidraulica", "any"),
    )
    # Moda vetorizada (muito mais rápida que .mode() em 20 mil grupos).
    summary["sintoma_mais_comum"] = _most_frequent(valid, "sintoma_cs")
    summary["causa_mais_comum"] = _most_frequent(valid, "causa_label")
    summary["cronica"] = summary["chamados"] >= 3
    return summary.sort_values("chamados", ascending=False)


def machine_timeline(df: pd.DataFrame, serial: str) -> pd.DataFrame:
    """Linha do tempo completa de uma máquina, pronta para exibição.

    Args:
        df: Base enriquecida.
        serial: Número de série (aceita minúsculas/espaços; é normalizado).

    Returns:
        Chamados da máquina em ordem cronológica (vazio se não existir).
    """
    from dna_maquina.serial import normalize_serial  # evita ciclo de import

    key = normalize_serial(serial)
    columns = ["data_abertura", "case_id", "sintoma_cs", "laudo", "motivo",
               "causa_label", "conclusao", "dias_desde_anterior",
               "reincidente", "vozes_concordam", "fez_adaptacao_hidraulica"]
    timeline = df.loc[df["serie"] == key, columns]
    return timeline.sort_values("data_abertura").reset_index(drop=True)
