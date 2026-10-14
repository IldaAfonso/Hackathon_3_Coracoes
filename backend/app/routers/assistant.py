"""Assistente de engenharia: a conversa é da Cora, os números são daqui.

A Cora (plataforma corporativa de IA do Grupo 3corações) é incorporada
na página Assistente e chama as análises deste projeto pelo servidor
MCP (``/mcp``). Estas rotas só dizem à interface ONDE está a Cora e
mantêm o plano B sem IA: perguntas prontas e parecer por regras.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import settings
from app.common import improvements
from app.privacy import mask_text
from app.serializers import value_json
from app.state import state
from dna_maquina import agent, llm
from dna_maquina import assistant as assistant_core

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistente"])


class AskIn(BaseModel):
    """Pergunta em português."""

    pergunta: str = Field(min_length=3, max_length=500)


class MemoIn(BaseModel):
    """Melhoria para a qual gerar o parecer técnico."""

    id_melhoria: str


def _origin(url: str) -> str | None:
    """Origem (esquema://host:porta) de uma URL http(s), ou ``None``.

    A interface usa a origem para conferir de quem vêm as mensagens do
    iframe da Cora e para quem envia o contexto da tela.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


@router.get("/cora")
def cora() -> dict:
    """Onde a interface encontra a Cora e como o conector se chama."""
    origin = _origin(settings.CORA_URL)
    return {
        "configurada": origin is not None,
        "embed_url": f"{settings.CORA_URL}/embed" if origin else None,
        "app_url": settings.CORA_URL or None,
        "origem": origin,
        "conector": settings.CORA_CONNECTOR_NAME,
        "perguntas_sugeridas": list(assistant_core.PRESETS),
    }


class ChatIn(BaseModel):
    """Pergunta livre para o assistente com Bedrock."""

    pergunta: str = Field(min_length=3, max_length=500)
    serie: str | None = Field(default=None, max_length=40)


@router.get("/bedrock")
def bedrock_status() -> dict:
    """A interface mostra o chat com Bedrock só quando ele está ligado."""
    return {"ligado": llm.bedrock_enabled()}


@router.post("/perguntar")
def ask_bedrock(body: ChatIn) -> dict:
    """Pergunta livre: o Bedrock escolhe as ferramentas e redige."""
    if not llm.bedrock_enabled():
        raise HTTPException(503, "Bedrock desligado neste ambiente (DNA_USE_BEDROCK=1).")
    try:
        reply = agent.ask(state.masked(), body.pergunta, body.serie)
    except Exception as error:  # noqa: BLE001 - erro vira mensagem na tela
        logger.warning("Bedrock indisponível no assistente: %s", error)
        raise HTTPException(502, "O Bedrock não respondeu agora. Use as respostas prontas abaixo.") from error
    return {"texto": mask_text(reply["texto"]), "ferramentas": reply["ferramentas"],
            "fonte": reply["fonte"]}


@router.get("/presets")
def presets() -> list[str]:
    """Perguntas prontas, respondidas por regras (sem IA)."""
    return list(assistant_core.PRESETS)


@router.post("/preset")
def answer_preset(body: AskIn) -> dict:
    """Responde uma das perguntas prontas, sem IA."""
    if body.pergunta not in assistant_core.PRESETS:
        raise HTTPException(404, "Pergunta pronta não encontrada.")
    text, raw = assistant_core.answer_preset(state.masked(), body.pergunta)
    return {"texto": mask_text(text), "dados": value_json(raw)}


@router.post("/parecer")
def memo(body: MemoIn) -> dict:
    """Parecer técnico para o P&D por regras, pronto para baixar."""
    if not any(i.id == body.id_melhoria for i in improvements()):
        raise HTTPException(404, "Melhoria não encontrada.")
    text = assistant_core.decision_memo(state.masked(), body.id_melhoria)
    return {"texto": mask_text(text), "fonte": "regras"}
