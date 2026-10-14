"""Pré-voo da demonstração: rode 10 minutos antes de subir ao palco.

Uso (na raiz do projeto, com ``make up`` já feito)::

    make demo-check

Roda DENTRO do container do backend (funciona em qualquer sistema). Com
``DEMO_REQUIRE_BEDROCK=1`` exige que o resumo da demo venha do
Bedrock ou do cache.

Confere que os serviços estão no ar, que os números que o roteiro cita
são os que a tela vai mostrar, que cada página responde rápido, que
nenhum dado pessoal aparece na máquina-história e que a demo funciona
sem internet (fonte, gráficos e logos vêm do próprio servidor).
Só biblioteca padrão do Python.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("DEMO_BASE_URL", "http://localhost:8080")
STORY_SERIAL = "G5PS000220465809"  # a "Juliana": 10 chamados, 8 voltas
SLOW_SECONDS = 5.0
OFFLINE_ASSETS = (
    "/",
    "/css/styles.css",
    "/js/main.js",
    "/vendor/chart.umd.js",
    "/assets/fonts/jost-latin.woff2",
    "/assets/brand/mercafe-logo.svg",
    "/assets/brand/3coracoes.png",
    "/assets/brand/tres.png",
    "/assets/modelos/passione-ilustracao.svg",
    "/assets/modelos/luna-ilustracao.svg",
)
BACKUP_DIR = Path(__file__).resolve().parents[2] / "demo-offline"
# Mesmas fronteiras do backend: série (12 dígitos seguidos) e decimal
# não são telefone.
PHONE = re.compile(r"(?<![\d.])\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}(?!\d)")

# Os números que o roteiro fala em voz alta. Se a base mudar (nova
# importação), o pré-voo avisa para você reler o roteiro.
EXPECTED = {
    "chamados": 30481,
    "cronicas": 2019,
    "reincidencia": (0.22, 0.01),
    "sem_conclusao": (0.208, 0.005),
}

results: list[tuple[bool, str]] = []


def record(ok: bool, text: str) -> None:
    """Guarda e imprime o resultado de uma verificação."""
    results.append((ok, text))
    print(f"{'OK   ' if ok else 'FALHA'} {text}")


def fetch(path: str) -> tuple[int, bytes, float]:
    """GET; devolve (status, corpo, segundos)."""
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as reply:
            return reply.status, reply.read(), time.perf_counter() - start
    except urllib.error.HTTPError as error:
        return error.code, error.read(), time.perf_counter() - start
    except (urllib.error.URLError, OSError):
        return 0, b"", time.perf_counter() - start


def api(path: str) -> dict | list | None:
    """GET na API; None se falhar."""
    status, body, _ = fetch(f"/api{path}")
    return json.loads(body) if status == 200 else None


def check_services() -> bool:
    """Frontend e backend (pelo proxy) respondem."""
    front, _, _ = fetch("/healthz")
    health = api("/health")
    record(front == 200, "frontend no ar (nginx)")
    record(health is not None, "backend no ar (via /api)")
    return front == 200 and health is not None


def check_numbers() -> None:
    """Os números do roteiro batem com a tela."""
    diag = api("/diagnostico")
    health = api("/health")
    if not diag or not health:
        record(False, "não consegui ler os números do diagnóstico")
        return
    value = {s["id"]: s["valor"] for s in diag["sintomas"]}
    record(
        health["chamados"] == EXPECTED["chamados"],
        f"chamados na base: {health['chamados']:,}".replace(",", "."),
    )
    record(
        value["cronicas"] == EXPECTED["cronicas"],
        f"máquinas crônicas: {value['cronicas']}",
    )
    for key in ("reincidencia", "sem_conclusao"):
        target, tolerance = EXPECTED[key]
        ok = abs(value[key] - target) <= tolerance
        record(ok, f"{key}: {value[key]:.1%} (roteiro cita ~{target:.1%})")


def check_story() -> None:
    """A máquina-história existe e o caso ponta a ponta dá veredito."""
    machine = api(f"/machines/{STORY_SERIAL}")
    if machine:
        sheet = machine["ficha"]
        record(
            sheet["chamados"] == 10 and sheet["voltas_em_90_dias"] == 8,
            f"máquina-história {STORY_SERIAL}: {sheet['chamados']} "
            f"chamados, {sheet['voltas_em_90_dias']} voltas",
        )
        leaked = PHONE.search(json.dumps(machine, ensure_ascii=False))
        record(leaked is None, "nenhum telefone na máquina-história")
    else:
        record(False, f"máquina-história {STORY_SERIAL} não encontrada")
    for item, expected in (
        ("G5-BANDEJA-2022", "Funcionou"),
        ("G5-ADAPT-HIDR-2022", "Sem efeito mensurável"),
    ):
        result = api(f"/impact/{item}")
        got = result["veredito"] if result else None
        record(got == expected, f"{item}: {got} (roteiro cita '{expected}')")


def check_pages() -> None:
    """Cada tela responde rápido (o 1º acesso ao ML treina na hora)."""
    quoted = urllib.parse.quote("Não extrai")
    for path in (
        "/overview",
        "/times",
        "/voices",
        "/radar",
        "/patterns",
        "/risk",
        "/quality",
        "/assistant/presets",
        "/assistant/cora",
        "/boletins/cadastrados",
        "/estoque",
        "/estoque/melhoria/G5-ADAPT-HIDR-2022",
        f"/radar/serie?modelo=Luna&sintoma={quoted}",
    ):
        status, _, seconds = fetch(f"/api{path}")
        ok = status == 200 and seconds < SLOW_SECONDS
        record(ok, f"{path.split('?')[0]:20s} {seconds:4.1f}s")


def check_offline() -> None:
    """Tudo que a página usa vem do próprio servidor (sem internet)."""
    missing = [p for p in OFFLINE_ASSETS if fetch(p)[0] != 200]
    record(
        not missing,
        "fonte, gráficos e logos servidos localmente"
        + (f" (faltam: {missing})" if missing else ""),
    )
    if BACKUP_DIR.is_dir():
        shots = sorted(BACKUP_DIR.glob("*.png"))
        record(
            len(shots) >= 9,
            f"{len(shots)} imagens de reserva em demo-offline/",
        )
    else:
        print("INFO  imagens de reserva (demo-offline/) não conferidas aqui")


def check_ai() -> None:
    """O Bedrock responde, ou a demo está no plano B (regras)?"""
    meta = api("/meta")
    machine = api(f"/machines/{STORY_SERIAL}")
    source = machine["resumo"]["fonte"] if machine else None
    print(f"INFO  IA generativa: {meta['ia_generativa'] if meta else '?'}")
    if os.environ.get("DEMO_REQUIRE_BEDROCK") == "1":
        record(
            source in {"bedrock", "cache"},
            "resumo da máquina-história vem do Bedrock ou do cache "
            f"(fonte: {source})",
        )
    else:
        print(f"INFO  fonte do resumo da máquina-história: {source}")


def mcp_tools() -> list[str]:
    """Lista as ferramentas do /mcp como a Cora faria (via nginx)."""
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                          "params": {}}).encode()
    request = urllib.request.Request(
        f"{BASE}/mcp", data=payload, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            text = reply.read().decode("utf-8")
    except (urllib.error.URLError, OSError):
        return []
    data = [line[5:] for line in text.splitlines() if line.startswith("data:")]
    body = json.loads(data[-1] if data else text)
    return [tool["name"] for tool in body.get("result", {}).get("tools", [])]


def check_cora() -> None:
    """A Cora acha as ferramentas (/mcp) e a página acha a Cora?"""
    tools = mcp_tools()
    record(len(tools) >= 10,
           f"servidor MCP para a Cora: {len(tools)} ferramentas em /mcp")
    cora = api("/assistant/cora") or {}
    if cora.get("configurada"):
        print(f"INFO  Cora incorporada a partir de {cora['origem']}")
    else:
        print("INFO  DNA_CORA_URL vazio: a página Assistente mostra só o "
              "plano B (regras). Veja docs/CORA.md")


def main() -> int:
    """Roda tudo; código de saída 1 se algo falhar."""
    if check_services():
        check_numbers()
        check_story()
        check_pages()
        check_ai()
        check_cora()
        check_offline()
    failures = sum(1 for ok, _ in results if not ok)
    print(
        "\n"
        + (
            "PRONTO PARA O PALCO"
            if not failures
            else f"{failures} PROBLEMA(S): resolva antes de apresentar"
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
