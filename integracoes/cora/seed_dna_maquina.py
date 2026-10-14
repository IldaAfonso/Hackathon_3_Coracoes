"""Seed da Cora: cadastra o conector "DNA da Máquina" e libera o uso.

Roda DENTRO do backend da Cora (usa o banco e os módulos dela). É
idempotente: pode rodar a cada subida, sem duplicar nada.

    # 1) copie para a pasta scripts/ do cora-backend (uma vez)
    cp integracoes/cora/seed_dna_maquina.py <kit>/cora-backend/scripts/
    # 2) rode no container da Cora, apontando para o /mcp do MVP
    docker compose exec \\
        -e DNA_MCP_URL=http://host.docker.internal:8080/mcp \\
        backend python scripts/seed_dna_maquina.py

O que faz (o mesmo que o administrador faria na tela Conectores +
Acesso, mas sem cliques e sem esquecer passo):

1. Cria ou atualiza o conector da ORGANIZAÇÃO (``created_by_user_id``
   nulo) com a URL de ``DNA_MCP_URL`` e ``auth_type='none'``: o
   servidor MCP do MVP não tem login próprio; quem decide o acesso é
   o RBAC da Cora.
2. Garante a role ``connector:dna-da-maquina`` (a Cora cria uma por
   conector, sem concessão).
3. Concede a role ao grupo de ``DNA_CORA_GRUPO`` (padrão ``default`` =
   todo usuário). Em produção, troque por um grupo do P&D
   (ex.: ``custom:engenharia-pd``).
4. Sonda o servidor e grava as ferramentas descobertas (a tela de
   funcionalidades da Cora já mostra as 11 ``dna_*``). Se o MVP estiver
   fora do ar, avisa e segue: a Cora redescobre a cada conversa.

Variáveis:
    DNA_MCP_URL      URL do /mcp como a CORA enxerga o MVP; padrão
                     http://host.docker.internal:8080/mcp
    DNA_CORA_GRUPO   slug do grupo que recebe o acesso (padrão: default)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text  # noqa: E402, I001  (módulos da Cora abaixo)

import mcp_runtime  # noqa: E402
import rbac  # noqa: E402
from db import db_session  # noqa: E402
from models import McpServer  # noqa: E402

CONNECTOR_NAME = "DNA da Máquina"
CONNECTOR_DESCRIPTION = (
    "Dados de campo das máquinas de café TRES (G5 Passione e G4 Luna): "
    "DNA de cada máquina pelo número de série, impacto das melhorias de "
    "engenharia (antes x depois), duas vozes (consumidor x técnico), "
    "radar de problemas, modos de falha no texto dos técnicos, máquinas "
    "crônicas e parecer técnico para o P&D. Números calculados pelo "
    "projeto; o modelo só lê e redige."
)
DEFAULT_MCP_URL = "http://host.docker.internal:8080/mcp"


def env(name: str, default: str = "") -> str:
    """Variável de ambiente sem espaços (vazia = padrão)."""
    return (os.environ.get(name) or default).strip()


def upsert_connector(db, url: str) -> McpServer:
    """Conector da organização, sem OAuth, apontando para ``url``."""
    server = db.scalar(
        select(McpServer).where(McpServer.name == CONNECTOR_NAME)
    )
    if server is None:
        server = McpServer(name=CONNECTOR_NAME)
        db.add(server)
    server.url = url
    server.description = CONNECTOR_DESCRIPTION
    server.auth_type = "none"
    server.enabled = True
    server.created_by_user_id = None
    db.flush()
    return server


def grant_to_group(db, role_id, group_slug: str) -> bool:
    """Concede a role ao grupo; ``False`` se o grupo não existir."""
    group_id = db.execute(
        text("SELECT id FROM groups WHERE slug = :s"), {"s": group_slug}
    ).scalar()
    if group_id is None:
        return False
    db.execute(
        text(
            "INSERT INTO group_roles (group_id, role_id) "
            "VALUES (:g, :r) ON CONFLICT DO NOTHING"
        ),
        {"g": group_id, "r": role_id},
    )
    return True


def discover(db, server: McpServer) -> int | None:
    """Lista as ferramentas no MVP e grava no catálogo da Cora."""
    try:
        tools = mcp_runtime.discover_tools_once(server, None)
    except Exception as error:  # noqa: BLE001 — aviso, não falha
        print(
            "[seed-dna] AVISO: não alcancei o MVP em "
            f"{server.url} ({mcp_runtime.root_cause_message(error)}). "
            "Suba o MVP (make up) e confira DNA_MCP_URL; a Cora "
            "redescobre as ferramentas a cada conversa."
        )
        return None
    mcp_runtime.sync_server_tools(db, server, tools)
    return len(tools)


def main() -> None:
    """Executa os quatro passos e imprime um resumo."""
    url = env("DNA_MCP_URL", DEFAULT_MCP_URL)
    group = env("DNA_CORA_GRUPO", "default")
    with db_session() as db:
        server = upsert_connector(db, url)
        role = rbac.ensure_connector_role(db, server)
        if not grant_to_group(db, role.id, group):
            raise SystemExit(f"[seed-dna] grupo {group!r} não existe")
        found = discover(db, server)
        role_slug = role.slug  # lido antes de a sessão fechar
    tools = "?" if found is None else str(found)
    print(
        f"[seed-dna] ok — conector {CONNECTOR_NAME!r} em {url}, "
        f"role {role_slug} concedida a {group!r}, {tools} ferramentas"
    )


if __name__ == "__main__":
    main()
