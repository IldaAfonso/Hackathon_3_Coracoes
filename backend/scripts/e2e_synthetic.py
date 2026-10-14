"""Demonstração ponta a ponta automatizada, na pilha SINTÉTICA.

Faz o que a pessoa faz na tela: importa o complemento da base, lê os
dois boletins em PDF, registra as melhorias e confere os vereditos.
Roda dentro do container do backend (``make sintetico-e2e``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

BASE = os.getenv("DNA_API", "http://localhost:8000") + "/api"
DATA = Path(os.getenv("DNA_SYNTHETIC", "/app/data/synthetic"))


def step(text: str) -> None:
    print(f"\n== {text}")


def check(condition: bool, message: str) -> None:
    print(("OK   " if condition else "FALHA ") + message)
    if not condition:
        sys.exit(1)


def upload(client: httpx.Client, path: str, file: Path, mime: str):
    with file.open("rb") as handle:
        return client.post(path, files={"file": (file.name, handle, mime)})


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=180)

    step("1. Estado inicial: base parcial e nenhuma melhoria")
    first = client.get("/diagnostico").json()["base"]["chamados"]
    check(client.get("/impact").json() == [], "catálogo de melhorias vazio")
    print(f"     {first} chamados")

    step("2. Dados > Importar: complemento (com 3 meses repetidos)")
    sent = upload(client, "/import", DATA / "complemento"
                  / "base_complemento.xlsx", "application/octet-stream")
    done = sent.json()
    check(sent.status_code == 200, "importação aceita")
    grew = done["depois"] - done["antes"]
    check(0 < grew < done["lidos"], "repetidos atualizados, não duplicados "
          f"(lidos {done['lidos']}, novos {grew})")

    codes = {}
    for pdf, kind in [("boletim_sintetico_kit.pdf", "retrofit_campo"),
                      ("boletim_sintetico_serie.pdf", "corte_serie")]:
        step(f"3. Boletins > ler {pdf}")
        read = upload(client, "/boletins/analisar", DATA / pdf,
                      "application/pdf").json()
        check(read["tipo"] == kind, f"tipo reconhecido: {read['tipo']}")
        preview = client.post("/boletins/previa", json={
            "modelo": read["modelo"], "termos": read["termos_sugeridos"],
            "pecas": read["pecas"]}).json()
        print(f"     {preview['chamados_relacionados']} chamados "
              f"relacionados (inferido)")
        created = client.post("/improvements", json={
            "titulo": read["titulo"], "modelo": read["modelo"],
            "tipo": read["tipo"], "serie_inicial": read["serie_inicial"],
            "data_documento": read["data_documento"],
            "pecas": read["pecas"],
            "termos_evidencia": read["termos_sugeridos"]})
        check(created.status_code == 201, "melhoria registrada "
              f"com o código {created.json().get('codigo')}")
        codes[kind] = created.json()

    step("4. Melhorias: o que os dados mostram")
    bandeja = client.get(f"/impact/{codes['corte_serie']['id']}").json()
    kit = client.get(f"/impact/{codes['retrofit_campo']['id']}").json()
    check(bandeja["veredito"] == "Funcionou",
          f"bandeja: {bandeja['veredito']}")
    check(kit["veredito"] == "Sem efeito mensurável",
          f"kit: {kit['veredito']}")
    check(kit["evidencia"]["origem"] == "registrada",
          f"kit com vínculo registrado "
          f"({kit['evidencia']['chamados_com_codigo']} chamados)")

    step("5. Dados: qualidade")
    items = {i["controle"]: i["registros"]
             for i in client.get("/quality").json()["itens"]}
    check(items["Chamados com código de melhoria registrado"] > 0,
          "chamados com código contados")
    print("\nTUDO OK")


if __name__ == "__main__":
    main()
