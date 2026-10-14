"""Saúde e metadados."""

from __future__ import annotations

from fastapi import APIRouter

from app.state import state
from dna_maquina import config, llm

router = APIRouter(tags=["saúde"])


@router.get("/health")
def health() -> dict:
    """Serviço vivo e base carregada."""
    return {"status": "ok", "chamados": int(len(state.df))}


@router.get("/meta")
def meta() -> dict:
    """Retrato da base e do modo de IA, para o rodapé da interface."""
    df = state.df
    generative = (
        "assistente e resumos com Amazon Bedrock" if llm.bedrock_enabled()
        else "assistente e resumos por regras (Bedrock desligado)"
    )
    return {
        "chamados": int(len(df)),
        "maquinas": int(df["serie"].nunique()),
        "periodo": {
            "inicio": df["data_abertura"].min().date().isoformat(),
            "fim": df["data_abertura"].max().date().isoformat(),
        },
        "modelos": sorted(df["modelo"].dropna().unique().tolist()),
        "ia_generativa": generative,
        "janela_reincidencia_dias": config.REINCIDENCE_WINDOW_DAYS,
    }
