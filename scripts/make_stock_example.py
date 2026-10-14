"""Gera a posição de estoque de EXEMPLO (fictícia) para a tela Estoque.

Uso::

    PYTHONPATH=src python scripts/make_stock_example.py

Por que existe
--------------
A posição de estoque por número de série é uma fonte NOVA, que a
empresa ainda não forneceu no desafio. Para a tela funcionar e ser
validada, este script cria um arquivo no MESMO formato que o ERP/WMS
exportaria (``data/synthetic/estoque_exemplo.csv``), com séries válidas
pelas regras reais (``serial.py``) e uma mistura pensada para a demo:

* lotes antigos de Passione (2021–2022) parados em assistência ou
  devolução: são os que ainda precisam das melhorias de 2022;
* produção recente de Passione e Luna nos centros de distribuição;
* algumas máquinas já com o código da melhoria aplicado, algumas
  vendidas (saem do levantamento) e duas séries ilegíveis.

Tudo é FICTÍCIO: nenhum número aqui descreve o estoque real da empresa.
A tela avisa isso enquanto a base de exemplo estiver em uso.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from dna_maquina.serial import parse_serial
from dna_maquina.stock import STOCK_COLUMN_MAP

OUT = Path(__file__).resolve().parents[1] / "data" / "synthetic" / \
    "estoque_exemplo.csv"
SEED = 2026
TODAY = date(2026, 10, 14)
PLACES_NEW = ("CD Sudeste", "CD Nordeste", "CD Sul")
PLACES_OLD = ("Assistência · recondicionadas", "Devoluções · triagem")

# (modelo, anos de fabricação, quantidade, locais, formato)
LOTS = (
    ("Passione", (2021,), 18, PLACES_OLD, "legado"),
    ("Passione", (2022,), 46, PLACES_OLD + ("CD Sudeste",), "legado"),
    ("Passione", (2023,), 60, PLACES_NEW, "legado"),
    ("Passione", (2025, 2026), 230, PLACES_NEW, "novo"),
    ("Luna", (2024, 2025, 2026), 210, PLACES_NEW, "novo"),
)


def make_serial(rng: random.Random, model: str, year: int,
                kind: str, week: int | None = None) -> str:
    """Série válida pelas regras de ``serial.py`` (legado ou novo)."""
    week = week or rng.randint(1, 52)
    seq = rng.randint(1, 99_999)
    yy = f"{year % 100:02d}"
    if kind == "legado":
        return f"G5PS000{yy}{week:02d}{seq:05d}"
    prefix = "G5PS" if model == "Passione" else "G4LN"
    return f"{prefix}{rng.choice(('127', '220'))}{yy}{week:02d}{seq:05d}"


def main() -> None:
    """Escreve o CSV (separador ``;``, UTF-8 com BOM, abre no Excel)."""
    rng = random.Random(SEED)
    rows: list[dict[str, str]] = []
    for model, years, count, places, kind in LOTS:
        for index in range(count):
            # Os 6 primeiros de 2021 são da semana 01: antes do
            # corte da bandeja (G5PS000210224033), para a demo
            # mostrar o caso.
            early = 1 if years == (2021,) and index < 6 else None
            serial = make_serial(rng, model, rng.choice(years), kind, early)
            info = parse_serial(serial)
            made = date.fromisocalendar(info.ano_fab, min(info.semana_fab,
                                                          52), 3)
            entry = min(TODAY - timedelta(days=3),
                        made + timedelta(days=rng.randint(10, 120)))
            if info.ano_fab <= 2022:  # lote antigo: voltou ao estoque
                entry = TODAY - timedelta(days=rng.randint(20, 400))
            rows.append({
                "Número de série": serial, "Modelo": model,
                "Local": rng.choice(places),
                "Data de entrada no estoque": entry.isoformat(),
                "Situação": rng.choices(
                    ("em estoque", "reservada", "vendida"),
                    weights=(80, 12, 8))[0],
                "Melhorias aplicadas": "",
            })
    # Algumas antigas já receberam o kit no estoque (código do projeto).
    old = [r for r in rows if r["Local"] in PLACES_OLD]
    for row in rng.sample(old, 9):
        row["Melhorias aplicadas"] = "MEL-G5-RF-0002-R"
    # Duas séries ilegíveis, como na base real de chamados.
    for bad, model in (("G5PS000DUPLICADO", "Passione"), ("G4LN12", "Luna")):
        rows.append({"Número de série": bad, "Modelo": model,
                     "Local": "CD Sul", "Situação": "em estoque",
                     "Data de entrada no estoque": "2026-09-30",
                     "Melhorias aplicadas": ""})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(STOCK_COLUMN_MAP),
                                delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} linhas fictícias em {OUT}")


if __name__ == "__main__":
    main()
