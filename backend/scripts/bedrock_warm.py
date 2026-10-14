"""Aquece o cache do Bedrock com os resumos que a demonstração mostra.

Uso (com os serviços no ar e o Bedrock funcionando)::

    make bedrock-warm

Chama a própria API (que mascara dado pessoal antes de enviar ao modelo)
para as máquinas da demo. As respostas ficam no cache do volume: se a
rede da AWS falhar no palco, a demonstração continua, porque tudo sai do
cache. Só biblioteca padrão.

O assistente de conversa não passa mais por aqui: ele é a Cora, que
chama as análises pelo servidor MCP (``/mcp``). Sobrou para o Bedrock
apenas o resumo em texto da página DNA, que é opcional.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api"
STORY_SERIAL = "G5PS000220465809"
EXTRA_MACHINES = 5
GOOD_SOURCES = {"bedrock", "cache"}


def call(path: str, payload: dict | None = None):
    """GET ou POST na API; devolve o JSON (ou None se falhar)."""
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as reply:
            return json.loads(reply.read())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def warmed(source: str | None) -> bool:
    """A resposta veio do Bedrock ou do cache (e não do plano B)?"""
    return source in GOOD_SOURCES


def plan() -> list[tuple[str, str, str]]:
    """Lista (tipo, rótulo, chave) do que será aquecido."""
    chronic = call(f"/machines/chronic?limit={EXTRA_MACHINES}") or {}
    serials = [STORY_SERIAL] + [
        m["serie"]
        for m in chronic.get("maquinas", [])
        if m["serie"] != STORY_SERIAL
    ]
    return [("resumo", f"resumo da máquina {s}", s) for s in serials]


def run_one(kind: str, key: str) -> str | None:
    """Executa um item e devolve a fonte (bedrock, cache, regras...)."""
    if kind != "resumo":
        return None
    body = call(f"/machines/{key}")
    return body["resumo"]["fonte"] if body else None


def main() -> int:
    """Aquece tudo; saída 1 se algo não veio do Bedrock/cache."""
    items = plan()
    if not items:
        print("FALHA não consegui ler o plano na API (backend no ar?)")
        return 1
    failures = 0
    for kind, label, key in items:
        source = run_one(kind, key)
        ok = warmed(source)
        failures += 0 if ok else 1
        print(f"{'OK   ' if ok else 'FALHA'} {label[:60]:60s} {source}")
    done = len(items) - failures
    print(
        f"\n{done} de {len(items)} no cache"
        + (
            ""
            if not failures
            else " | o que falhou saiu pelo plano B (regras/offline); "
            "rode make bedrock-check para o diagnóstico"
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
