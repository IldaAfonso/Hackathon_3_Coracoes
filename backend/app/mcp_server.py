"""Servidor MCP: as análises da DNA da Máquina como ferramentas da Cora.

Por que MCP
-----------
A Cora (plataforma corporativa de IA do Grupo 3corações) conversa com
sistemas externos por **conectores MCP** (Model Context Protocol). O
administrador da Cora cadastra a URL deste servidor uma única vez; daí
em diante, o modelo da Cora enxerga as ferramentas abaixo e decide
sozinho quando chamá-las. Quem pode usar o conector é decidido pelo
RBAC da Cora (role ``connector:dna-da-maquina`` concedida a um grupo).

O que este módulo garante
-------------------------
* **Números do código, não do modelo.** Cada ferramenta chama uma função
  já testada de :class:`dna_maquina.assistant.Toolbox` e devolve JSON.
* **Privacidade na saída.** As ferramentas leem a base MASCARADA
  (``state.masked()``) e todo texto do resultado passa de novo por
  :func:`app.privacy.mask_text` antes de sair para a Cora.
* **Somente leitura.** Nenhuma ferramenta altera base, catálogo ou
  arquivos: o pior que um prompt malicioso consegue é ler análises.
* **Sem bloquear a API.** As análises (pandas/scikit-learn) rodam numa
  thread de trabalho; o laço de eventos continua atendendo a interface.

Transporte
----------
*Streamable HTTP* sem estado (``stateless_http=True``): cada chamada é
independente, então o backend pode reiniciar sem quebrar a conversa.
Rota: ``/mcp`` (o nginx do frontend repassa ``/mcp`` para cá).

Segurança de rede
-----------------
O servidor não tem autenticação própria — é o que permite à Cora
cadastrá-lo como ``auth_type='none'``. Por isso ele deve ficar só na
rede local/do evento. A proteção contra *DNS rebinding* do SDK fica
ligada e aceita apenas os hosts de ``DNA_MCP_ALLOWED_HOSTS``.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from app.privacy import mask_text
from app.state import state
from dna_maquina.assistant import TOOL_GUIDE, Toolbox, memo_template

logger = logging.getLogger("dna.mcp")

MCP_PATH = "/mcp"
"""Rota pública do MCP (a URL cadastrada na Cora termina aqui)."""

DEFAULT_ALLOWED_HOSTS = (
    "localhost:*,127.0.0.1:*,host.docker.internal:*,"
    "frontend:*,backend:*,dna-frontend:*"
)
"""Hosts aceitos por padrão: máquina local e nomes da rede Docker."""

MAX_RESULT_CHARS = 60_000
"""Teto do JSON devolvido: protege o contexto do modelo da Cora."""

MAX_ROWS = 50
"""Teto de linhas pedidas nas ferramentas com parâmetro ``n``."""


def _allowed_hosts() -> list[str]:
    """Lê ``DNA_MCP_ALLOWED_HOSTS`` (lista separada por vírgulas)."""
    raw = os.getenv("DNA_MCP_ALLOWED_HOSTS") or DEFAULT_ALLOWED_HOSTS
    return [host.strip() for host in raw.split(",") if host.strip()]


def _mask_deep(value: Any) -> Any:
    """Aplica a máscara de privacidade em todo texto, em todo nível."""
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, dict):
        return {key: _mask_deep(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_deep(item) for item in value]
    return value


def _toolbox() -> Toolbox:
    """Uma caixa de ferramentas por base carregada.

    Fica no cache do ``state``: ao importar uma planilha nova o cache é
    limpo e a próxima chamada já usa a base nova. O cache interno da
    caixa (modos de falha, o cálculo mais caro) é aproveitado entre
    chamadas.
    """
    return state.memo("mcp_toolbox", lambda: Toolbox(state.masked()))


def _to_json(result: Any) -> str:
    """Resultado mascarado em JSON compacto, com teto de tamanho."""
    text = json.dumps(_mask_deep(result), ensure_ascii=False,
                      separators=(",", ":"))
    if len(text) > MAX_RESULT_CHARS:
        return json.dumps({"erro": "resultado grande demais; refine os "
                                   "filtros da pergunta"},
                          ensure_ascii=False)
    return text


async def _run(name: str, arguments: dict | None = None) -> str:
    """Executa uma ferramenta do :class:`Toolbox` fora do event loop.

    Erros não derrubam a conversa: voltam como ``{"erro": ...}`` para o
    modelo da Cora ler e, se for o caso, tentar de novo.
    """
    args = {key: value for key, value in (arguments or {}).items()
            if value is not None}
    logger.info("ferramenta %s %s", name, sorted(args))
    result = await anyio.to_thread.run_sync(
        lambda: _toolbox().run(name, args))
    return _to_json(result)


def _clamp(n: int) -> int:
    """Mantém ``n`` entre 1 e :data:`MAX_ROWS`."""
    return max(1, min(int(n), MAX_ROWS))


mcp = FastMCP(
    "DNA da Máquina",
    instructions=TOOL_GUIDE,
    stateless_http=True,
    streamable_http_path=MCP_PATH,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_allowed_hosts(),
        allowed_origins=[],
    ),
)


# ---------------------------------------------------------------------------
# Ferramentas (o nome começa com ``dna_`` para não colidir com outros
# conectores da Cora; a docstring é a descrição que o modelo lê)
# ---------------------------------------------------------------------------
@mcp.tool()
async def dna_listar_melhorias() -> str:
    """Lista as melhorias de engenharia cadastradas pelo P&D das
    máquinas TRES (boletins técnicos), com id, título, modelo, data e
    objetivo. Use antes de dna_avaliar_melhoria para descobrir o id."""
    return await _run("listar_melhorias")


@mcp.tool()
async def dna_listar_sintomas() -> str:
    """Lista os sintomas relatados pelo consumidor, com a grafia exata
    e o número de chamados. Use antes das ferramentas que filtram por
    sintoma (dna_contar_chamados, dna_duas_vozes)."""
    return await _run("listar_sintomas")


@mcp.tool()
async def dna_avaliar_melhoria(id_melhoria: str) -> str:
    """Mede se uma melhoria de engenharia funcionou em campo: compara as
    máquinas antes x depois da melhoria (pelo número de série ou pela
    aplicação do kit), com taxa, intervalo de confiança de 95%, redução
    relativa, p-valor e as premissas da análise. O indicador é de MIX
    (fatia de um sintoma nos chamados), não taxa de falha por máquina
    instalada — cite essa ressalva."""
    return await _run("avaliar_melhoria", {"id_melhoria": id_melhoria})


@mcp.tool()
async def dna_historico_maquina(serie: str) -> str:
    """DNA de uma máquina: linha do tempo de chamados, sintomas, peças
    trocadas, reincidências e melhorias que se aplicam a ela, a partir
    do número de série (ex.: G5PS000220465809)."""
    return await _run("historico_maquina", {"serie": serie})


@mcp.tool()
async def dna_contar_chamados(
    modelo: Literal["Passione", "Luna"] | None = None,
    sintoma: str | None = None,
    ano_fabricacao: int | None = None,
    mes_inicio: str | None = None,
    mes_fim: str | None = None,
) -> str:
    """Conta chamados de assistência técnica com filtros opcionais:
    modelo (Passione = G5, Luna = G4), sintoma (grafia exata de
    dna_listar_sintomas), ano de fabricação e meses no formato
    AAAA-MM-01. Devolve total, máquinas distintas, fração da base,
    evolução dos últimos 12 meses e as 5 causas mais frequentes."""
    return await _run("contar_chamados", {
        "modelo": modelo, "sintoma": sintoma,
        "ano_fabricacao": ano_fabricacao,
        "mes_inicio": mes_inicio, "mes_fim": mes_fim,
    })


@mcp.tool()
async def dna_duas_vozes(sintoma: str) -> str:
    """Duas vozes: para um sintoma relatado pelo consumidor (grafia
    exata de dna_listar_sintomas), mostra o que o técnico de fato
    encontrou na visita e a concordância entre as duas versões."""
    return await _run("duas_vozes", {"sintoma": sintoma})


@mcp.tool()
async def dna_radar(n: int = 5) -> str:
    """Radar de problemas: combinações modelo x sintoma x causa que mais
    cresceram nos últimos 3 meses em relação à média anterior."""
    return await _run("radar", {"n": _clamp(n)})


@mcp.tool()
async def dna_modos_de_falha() -> str:
    """Modos de falha descobertos por IA (TF-IDF + NMF) no texto livre
    dos técnicos: temas, fatia por modelo, temas em alta e boletins
    técnicos citados no texto. A primeira chamada pode levar alguns
    segundos."""
    return await _run("modos_de_falha")


@mcp.tool()
async def dna_maquinas_cronicas(n: int = 10) -> str:
    """Máquinas crônicas (3 ou mais chamados): total e as n com mais
    chamados, vazamentos e reincidências."""
    return await _run("maquinas_cronicas", {"n": _clamp(n)})


@mcp.tool()
async def dna_qualidade_dos_dados() -> str:
    """Confiabilidade da base: séries inválidas, chamados sem laudo
    técnico e nota média (0 a 100) do DNA das máquinas. Use quando a
    pergunta for sobre o quanto se pode confiar nos números."""
    return await _run("qualidade_dos_dados")


@mcp.tool()
async def dna_parecer_tecnico(id_melhoria: str) -> str:
    """Fatos para um parecer técnico de uma página para o P&D sobre uma
    melhoria: devolve os números da avaliação e um rascunho por regras
    (decisão, evidência, ressalvas e próximo passo). Redija o parecer
    final usando SOMENTE esses fatos."""
    def build() -> dict:
        facts = _toolbox().run("avaliar_melhoria",
                               {"id_melhoria": id_melhoria})
        return {"fatos": facts, "rascunho_por_regras": memo_template(facts)}

    return _to_json(await anyio.to_thread.run_sync(build))


# ---------------------------------------------------------------------------
# Transporte HTTP (rota /mcp + ciclo de vida)
# ---------------------------------------------------------------------------
class McpEndpoint:
    """Aplicação ASGI da rota ``/mcp``.

    O gerenciador de sessões do SDK só pode ser ligado UMA vez. Em vez
    de usar o que o FastMCP cria uma única vez, este endpoint recebe um
    gerenciador novo a cada partida do backend (:func:`lifespan`) —
    assim reinícios do servidor e os testes, que sobem o app várias
    vezes no mesmo processo, funcionam igual.
    """

    def __init__(self) -> None:
        self.manager: StreamableHTTPSessionManager | None = None

    async def __call__(self, scope: Scope, receive: Receive,
                       send: Send) -> None:
        if self.manager is None:
            raise RuntimeError("servidor MCP fora do ciclo de vida do app")
        await self.manager.handle_request(scope, receive, send)


endpoint = McpEndpoint()
route = Route(MCP_PATH, endpoint=endpoint,
              methods=["GET", "POST", "DELETE"])
"""Rota que o ``app.main`` acrescenta ao FastAPI."""


@asynccontextmanager
async def lifespan() -> AsyncIterator[None]:
    """Liga o servidor MCP enquanto o backend estiver no ar."""
    endpoint.manager = StreamableHTTPSessionManager(
        app=mcp._mcp_server,
        json_response=False,
        stateless=True,
        security_settings=mcp.settings.transport_security,
    )
    async with endpoint.manager.run():
        logger.info("servidor MCP da Cora em %s (%d ferramentas)",
                    MCP_PATH, len(tool_names()))
        try:
            yield
        finally:
            endpoint.manager = None


def tool_names() -> list[str]:
    """Nomes publicados (usado nos testes e no diagnóstico)."""
    return sorted(tool.name for tool in mcp._tool_manager.list_tools())
