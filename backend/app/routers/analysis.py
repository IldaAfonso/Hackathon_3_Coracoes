"""Análises: duas vozes, radar, padrões no texto e risco de retorno."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

from app.privacy import mask_frame, mask_text
from app.serializers import df_json, value_json
from app.state import state
from dna_maquina import analytics, config, patterns

router = APIRouter(tags=["análises"])

AGREEMENT_ROWS = 12
RADAR_ROWS = 15
COHORT_ROWS = 20
RISING_TOPICS = 5
BULLETIN_ROWS = 12
FOLLOW_UP_ROWS = 50
FOLLOW_UP_COLUMNS = [
    "data_abertura",
    "serie",
    "modelo",
    "sintoma_cs",
    "causa_label",
    "ordem_na_maquina",
    "risco",
]


@router.get("/voices")
def voices() -> dict:
    """O que o consumidor relatou × o que o técnico encontrou."""
    df = state.df
    matrix = analytics.voices_matrix(df)
    agreement = analytics.agreement_by_symptom(df).head(AGREEMENT_ROWS)
    agreement = agreement.reset_index()
    text_cols = [c for c in agreement.columns if agreement[c].dtype == object]
    return {
        "sintomas": [mask_text(s) for s in matrix.index.tolist()],
        "causas": matrix.columns.tolist(),
        "valores": value_json(matrix.round(4).values.tolist()),
        "concordancia": df_json(mask_frame(agreement, text_cols)),
    }


@router.get("/radar")
def radar() -> dict:
    """O que cresceu nos últimos 3 meses sem ninguém ter perguntado."""
    alerts = state.radar()
    cohorts = analytics.chronic_cohorts(state.df).head(COHORT_ROWS)
    alerts_json = (
        []
        if alerts.empty
        else df_json(mask_frame(alerts.head(RADAR_ROWS), ["sintoma_cs"]))
    )
    return {"alertas": alerts_json, "lotes_anomalos": df_json(cohorts)}


@router.get("/radar/serie")
def radar_series(modelo: str, sintoma: str) -> list[dict]:
    """Evolução mensal de um par modelo × sintoma."""
    df = state.df
    rows = df[(df["modelo"] == modelo) & (df["sintoma_cs"] == sintoma)]
    return df_json(rows.groupby("mes").size().reset_index(name="n"))


@router.get("/patterns")
def failure_patterns() -> dict:
    """Modos de falha descobertos no texto livre dos técnicos."""
    modes = state.failure_modes()
    rising = patterns.emerging_topics(modes).head(RISING_TOPICS)
    share = modes.por_modelo
    bulletins = patterns.bulletin_mentions(state.df).head(BULLETIN_ROWS)
    return {
        "temas": df_json(mask_frame(modes.temas, ["nome", "termos"])),
        "por_modelo": {
            "temas": [mask_text(str(t)) for t in share.index],
            "modelos": share.columns.tolist(),
            "valores": value_json(share.round(4).values.tolist()),
        },
        "em_alta": df_json(mask_frame(rising.reset_index(), ["tema"])),
        "boletins": df_json(bulletins),
    }


@router.get("/risk")
def return_risk() -> dict:
    """Chance de a máquina voltar em 90 dias e chamados a acompanhar."""
    df = state.df
    _, metrics = state.risk_model()
    scores = state.risk_scores()
    window = pd.Timedelta(days=config.REINCIDENCE_WINDOW_DAYS)
    recent = df.loc[scores.index].assign(risco=scores)
    recent = recent[
        recent["data_abertura"] > df["data_abertura"].max() - window
    ]
    top = recent.sort_values("risco", ascending=False)
    top = top.head(FOLLOW_UP_ROWS)[FOLLOW_UP_COLUMNS]
    top = mask_frame(top, ["sintoma_cs", "causa_label"]).assign(
        data_abertura=top["data_abertura"].dt.strftime("%Y-%m-%d")
    )
    return {"metricas": value_json(metrics), "acompanhar": df_json(top)}
