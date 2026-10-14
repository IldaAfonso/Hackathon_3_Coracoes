"""Ponto de entrada da API da DNA da Máquina.

O número de série liga os três times (Customer Success, Pós-vendas e
P&D) que cuidam da mesma máquina. Cada rota devolve uma análise sobre
essa história, com os números calculados no código e a IA só lendo,
agrupando ou redigindo.

A conversa com IA é da Cora: ela chama as análises daqui pelo servidor
MCP montado em ``/mcp``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import mcp_server, settings
from app.routers import (
    analysis,
    assistant,
    boletins,
    data,
    health,
    improvements,
    machines,
    narrative,
    overview,
    stock,
)
from app.state import state

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("dna.api")

ROUTERS = (
    health.router,
    narrative.router,
    overview.router,
    machines.router,
    improvements.router,
    boletins.router,
    stock.router,
    analysis.router,
    assistant.router,
    data.router,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Carrega a base na partida e liga o servidor MCP da Cora.

    Se a base estiver quebrada, falha cedo. O gerenciador de sessões do
    MCP só funciona dentro deste contexto (montado num FastAPI, o
    lifespan próprio dele não roda sozinho).
    """
    logger.info("base carregada: %s chamados", f"{len(state.df):,}")
    async with mcp_server.lifespan():
        yield


app = FastAPI(
    title="DNA da Máquina · API",
    version="1.0.0",
    description=__doc__,
    lifespan=lifespan,
)
for router in ROUTERS:
    app.include_router(router, prefix="/api")
# Rota /mcp: ferramentas da DNA da Máquina para a Cora (backend/app/
# mcp_server.py). Entra depois das rotas /api, sem prefixo.
app.router.routes.append(mcp_server.route)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception):
    """Erro inesperado: loga o detalhe, devolve mensagem neutra."""
    logger.exception("erro em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno. Veja os logs do servidor."},
    )
