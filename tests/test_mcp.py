"""Testes do servidor MCP: o contrato entre a DNA da Máquina e a Cora.

Cada teste documenta uma garantia:

* a Cora enxerga o catálogo completo, com nomes que não colidem;
* o protocolo funciona por HTTP, do jeito que o cliente da Cora fala;
* nenhum dado pessoal sai pelas ferramentas;
* erro vira mensagem para o modelo, não queda da conversa;
* só hosts conhecidos chegam ao servidor (DNS rebinding).
"""

from __future__ import annotations

import json

import anyio
import pytest
from conftest import PHONE_SERIAL

EXPECTED_TOOLS = {
    "dna_listar_melhorias", "dna_listar_sintomas", "dna_avaliar_melhoria",
    "dna_historico_maquina", "dna_contar_chamados", "dna_duas_vozes",
    "dna_radar", "dna_modos_de_falha", "dna_maquinas_cronicas",
    "dna_qualidade_dos_dados", "dna_parecer_tecnico",
}
MCP_HEADERS = {
    "Host": "localhost:8080",
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def _rpc(http, method: str, params: dict | None = None) -> dict:
    """Uma chamada JSON-RPC no /mcp; lê a resposta JSON ou SSE."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method,
               "params": params or {}}
    response = http.post("/mcp", json=payload, headers=MCP_HEADERS)
    assert response.status_code == 200, response.text
    if response.headers["content-type"].startswith("text/event-stream"):
        data = [line[5:] for line in response.text.splitlines()
                if line.startswith("data:")]
        return json.loads(data[-1])
    return response.json()


@pytest.fixture
def mcp_http(client):
    """Cliente HTTP com o lifespan ligado (o MCP precisa dele)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as http:
        yield http


def test_catalog_has_every_tool_with_prefix():
    from app.mcp_server import tool_names

    assert set(tool_names()) == EXPECTED_TOOLS


def test_cora_lists_tools_over_streamable_http(mcp_http):
    init = _rpc(mcp_http, "initialize", {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "cora-teste", "version": "1"}})
    assert init["result"]["serverInfo"]["name"] == "DNA da Máquina"

    tools = _rpc(mcp_http, "tools/list")["result"]["tools"]
    assert {tool["name"] for tool in tools} == EXPECTED_TOOLS
    assert all(tool["description"] for tool in tools)


def test_tool_call_over_http_returns_numbers(mcp_http):
    result = _rpc(mcp_http, "tools/call", {
        "name": "dna_avaliar_melhoria",
        "arguments": {"id_melhoria": "G5-BANDEJA-2022"}})["result"]
    body = json.loads(result["content"][0]["text"])
    assert {"grupos", "p_valor", "premissas"} <= set(body)


def test_tools_never_leak_personal_data(client):
    from app.mcp_server import dna_historico_maquina

    text = anyio.run(dna_historico_maquina, PHONE_SERIAL)
    assert "91234" not in text and "5678" not in text


def test_bad_arguments_become_a_message_for_the_model(client):
    from app.mcp_server import dna_avaliar_melhoria, dna_duas_vozes

    unknown = json.loads(anyio.run(dna_avaliar_melhoria, "NAO-EXISTE"))
    assert "erro" in unknown and "G5-BANDEJA-2022" in unknown["erro"]
    assert "erro" in json.loads(anyio.run(dna_duas_vozes, "sintoma x"))


def test_memo_tool_brings_facts_and_rule_draft(client):
    from app.mcp_server import dna_parecer_tecnico

    body = json.loads(anyio.run(dna_parecer_tecnico, "G5-BANDEJA-2022"))
    assert body["rascunho_por_regras"].startswith("Decisão de engenharia")
    assert body["fatos"]["grupos"]


def test_unknown_host_is_refused(mcp_http):
    response = mcp_http.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={**MCP_HEADERS, "Host": "atacante.example:80"})
    assert response.status_code in (400, 403, 421)
