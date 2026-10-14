"""Diagnóstico do servidor MCP da Cora: lista e chama ferramentas.

Uso (com ``make up`` feito)::

    make mcp-check

Faz o mesmo caminho da Cora: ``initialize`` → ``tools/list`` →
``tools/call`` em ``/mcp``, por HTTP (streamable HTTP, respostas SSE).
Se passar aqui e a Cora não enxergar as ferramentas, o problema está na
URL cadastrada no conector (rede entre os containers) ou no acesso
(role ``connector:dna-da-maquina`` sem grupo). Só biblioteca padrão.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("DNA_MCP_CHECK_URL", "http://localhost:8000/mcp")
EXPECTED_TOOLS = 11


def rpc(method: str, params: dict | None = None) -> dict:
    """Uma chamada JSON-RPC; devolve o ``result`` (ou levanta erro)."""
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                          "params": params or {}}).encode()
    request = urllib.request.Request(
        URL, data=payload, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(request, timeout=180) as reply:
        text = reply.read().decode("utf-8")
    data = [line[5:] for line in text.splitlines() if line.startswith("data:")]
    body = json.loads(data[-1] if data else text)
    if "error" in body:
        raise RuntimeError(body["error"].get("message", body["error"]))
    return body["result"]


def main() -> int:
    """Roda as três etapas e diz o que consertar."""
    try:
        info = rpc("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "mcp-check", "version": "1"}})
        tools = [tool["name"] for tool in rpc("tools/list")["tools"]]
        radar = rpc("tools/call", {"name": "dna_radar",
                                   "arguments": {"n": 1}})
    except (urllib.error.URLError, OSError, RuntimeError) as error:
        print(f"FALHA {URL}: {error}")
        print("      O backend está no ar? Host fora de "
              "DNA_MCP_ALLOWED_HOSTS responde 421.")
        return 1
    print(f"OK    servidor: {info['serverInfo']['name']}")
    print(f"OK    {len(tools)} ferramentas: {', '.join(sorted(tools))}")
    print(f"OK    dna_radar: {radar['content'][0]['text'][:120]}…")
    return 0 if len(tools) >= EXPECTED_TOOLS else 1


if __name__ == "__main__":
    sys.exit(main())
