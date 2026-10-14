"""Smoke test da API contra a base REAL, rodando dentro do container.

Uso::

    docker compose exec backend python backend/scripts/smoke_api.py

Chama cada rota, confere o status e as chaves essenciais, mede o tempo
e verifica que nenhum dado pessoal da base sai pela API. Só biblioteca
padrão do Python, para rodar em qualquer lugar.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

BASE_URL = "http://localhost:8000/api"
SLOW_SECONDS = 20.0


def call(path: str, payload: dict | None = None) -> tuple[int, Any, float]:
    """Chama a API; devolve (status, corpo JSON, segundos)."""
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read()
    elapsed = time.perf_counter() - start
    return status, json.loads(body or "null"), elapsed


def has_keys(*keys: str) -> Callable[[Any], bool]:
    """Verificador: o corpo é um dict com todas as chaves dadas."""
    return lambda body: (
        isinstance(body, dict) and all(key in body for key in keys)
    )


def non_empty_list(body: Any) -> bool:
    """Verificador: lista com pelo menos um item."""
    return isinstance(body, list) and len(body) > 0


CHECKS: list[tuple[str, str, Callable[[Any], bool]]] = [
    ("/health", "saúde", has_keys("status", "chamados")),
    ("/meta", "metadados", has_keys("periodo", "modelos")),
    (
        "/diagnostico",
        "diagnóstico do histórico",
        has_keys("sintomas", "melhorias_a_implantar"),
    ),
    ("/times", "três times ligados pela série", has_keys("times", "ligacao")),
    ("/overview", "visão geral", has_keys("totais", "mensal")),
    ("/machines/chronic", "máquinas crônicas", has_keys("total", "maquinas")),
    ("/machines/search?q=G5PS", "busca de série", non_empty_list),
    ("/impact", "catálogo de melhorias", non_empty_list),
    ("/voices", "duas vozes", has_keys("sintomas", "valores")),
    ("/radar", "radar", has_keys("alertas")),
    ("/patterns", "padrões no texto (IA)", has_keys("temas", "boletins")),
    ("/risk", "risco de retorno (ML)", has_keys("metricas", "acompanhar")),
    ("/quality", "qualidade dos dados", has_keys("itens")),
    ("/assistant/presets", "perguntas prontas", non_empty_list),
    ("/boletins/cadastrados", "boletins com código do projeto",
     non_empty_list),
    ("/estoque", "posição de estoque", has_keys("em_estoque", "melhorias")),
    ("/estoque/melhoria/G5-ADAPT-HIDR-2022", "estoque × melhoria",
     has_keys("pendentes", "maquinas")),
]


def check_routes() -> int:
    """Roda as verificações de rota; devolve o total de falhas."""
    failures = 0
    for path, label, verify in CHECKS:
        status, body, seconds = call(path)
        ok = status == 200 and verify(body)
        slow = " (LENTO)" if seconds > SLOW_SECONDS else ""
        print(
            f"{'OK  ' if ok else 'FALHA'} {seconds:5.1f}s {path:28s}"
            f" {label}{slow}"
        )
        failures += 0 if ok else 1
    return failures


def check_improvements() -> int:
    """Avalia cada melhoria do catálogo; nenhuma pode dar erro."""
    failures = 0
    _, catalog, _ = call("/impact")
    for item in catalog:
        status, body, seconds = call(f"/impact/{item['id']}")
        ok = status == 200 and "veredito" in body
        verdict = body.get("veredito") if ok else body
        print(
            f"{'OK  ' if ok else 'FALHA'} {seconds:5.1f}s melhoria "
            f"{item['id']}: {verdict}"
        )
        failures += 0 if ok else 1
    return failures


def check_privacy() -> int:
    """O telefone real da base não pode sair pela API.

    Acha, na base processada, os chamados cujo texto livre contém dado
    pessoal e confere a ficha de cada máquina envolvida.
    """
    from app.privacy import mask_text
    from app.state import state

    df = state.df
    risky = df[
        df["conclusao"].fillna("").map(lambda text: mask_text(text) != text)
    ]
    print(f"chamados com possível dado pessoal no texto: {len(risky)}")
    failures = 0
    for serial in risky["serie"].dropna().unique()[:20]:
        status, body, _ = call(f"/machines/{serial}")
        raw_texts = risky.loc[risky["serie"] == serial, "conclusao"]
        leaked = [
            t
            for t in raw_texts
            if t and t in json.dumps(body, ensure_ascii=False)
        ]
        ok = status == 200 and not leaked
        print(f"{'OK  ' if ok else 'FALHA'} privacidade na ficha {serial}")
        failures += 0 if ok else 1
    return failures


def main() -> int:
    """Executa tudo; o código de saída é 1 se algo falhar."""
    failures = check_routes() + check_improvements() + check_privacy()
    print(f"\n{'TUDO OK' if not failures else f'{failures} FALHA(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
