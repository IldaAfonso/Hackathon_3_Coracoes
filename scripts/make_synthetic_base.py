"""Gera a base SINTÉTICA de validação (sem dado real, sem dado pessoal).

A base tem o mesmo layout da extração do Salesforce e efeitos plantados,
com a verdade conhecida em ``ground_truth.json``. Se o protótipo recupera
o que foi plantado, o pipeline, a estatística e a API estão corretos.

Efeitos plantados
-----------------
* Bandeja (corte na série G5PS000210224033): vazamento cai de 32% para
  16% dos chamados. Esperado: veredito "Funcionou".
* Kit hidráulico (retrofit): a taxa de retorno em 90 dias é igual com e
  sem o kit. Esperado: "Sem efeito mensurável".
* 25 máquinas crônicas (6 chamados cada) e 5% de séries ilegíveis.
* Coluna "Código da melhoria" preenchida nos atendimentos com o kit.
* Base partida em ``inicial/`` e ``complemento/`` (com 3 meses repetidos)
  para demonstrar a importação sem duplicar, mais um catálogo vazio.
* Catálogo de melhorias e 2 boletins em PDF (kit "Indiferente" e com
  série), para exercitar a tela Boletins.
* 1 telefone FALSO em texto livre, para provar o mascaramento.

Uso: ``python scripts/make_synthetic_base.py [pasta de saída]``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
KIT_CODE = "MEL-G5-RF-0001-B"  # 1º kit registrado pela tela Boletins
CUT_SERIAL = "G5PS000210224033"
FAKE_PHONE = "(11) 90000-0000"
SPLIT_END = pd.Timestamp("2025-10-01")      # base inicial: antes disso
SPLIT_OVERLAP = pd.Timestamp("2025-07-01")  # complemento repete 3 meses
SYMPTOMS = ["Botões piscando/Luz acesa", "Não extrai", "Voltagem errada",
            "Ruído excessivo"]
LEAK = "Máquina vazando"
CAUSES = [
    "Realizado desentupimento do bico e teste de vazamento",
    "Trocado o oring do suporte do anel",
    "Substituída a bandeja de cápsulas",
    "Orientado o consumidor sobre a limpeza",
    "Contador volumétrico com defeito, trocado",
]
KIT_TEXT = "Feita adaptação hidráulica conforme boletim técnico"


def _fab_date(year: int, week: int) -> pd.Timestamp:
    return pd.Timestamp.fromisocalendar(2000 + year, week, 1)


def _legacy(year: int, week: int, number: int) -> str:
    return f"G5PS000{year:02d}{week:02d}{number:05d}"


def _machines(rng: np.random.Generator) -> list[dict]:
    """Máquinas por coorte; cada uma com série, modelo e fabricação."""
    out = []

    def add(count, make, model, cohort):
        for _ in range(count):
            serial, year, week = make()
            out.append({"serie": serial, "modelo": model, "coorte": cohort,
                        "fab": _fab_date(year, week)})

    def pre():
        if rng.random() < 0.9:
            year, week = 20, int(rng.integers(3, 53))
        else:
            year, week = 21, 1
        return _legacy(year, week, int(rng.integers(1, 99999))), year, week

    def post():
        if rng.random() < 0.9:
            year, week = 21, int(rng.integers(3, 53))
        else:
            year, week = 22, 1
        return _legacy(year, week, int(rng.integers(1, 99999))), year, week

    def late():
        year, week = int(rng.integers(24, 26)), int(rng.integers(1, 40))
        number = int(rng.integers(1, 99999))
        return f"G5PS127{year:02d}{week:02d}{number:05d}", year, week

    def luna():
        year, week = int(rng.integers(23, 26)), int(rng.integers(1, 50))
        number = int(rng.integers(1, 99999))
        return f"G4LN127{year:02d}{week:02d}{number:05d}", year, week

    add(2600, pre, "Passione", "antes")
    add(2600, post, "Passione", "depois")
    add(900, late, "Passione", "fora")
    add(1100, luna, "Luna", "luna")
    return out


def build(seed: int = SEED) -> tuple[pd.DataFrame, dict]:
    """Devolve a planilha sintética e a verdade plantada."""
    rng = np.random.default_rng(seed)
    machines = _machines(rng)
    chronic = {m["serie"] for m in machines if m["modelo"] == "Passione"
               and m["coorte"] == "fora"}
    chronic = set(sorted(chronic)[:25])
    rows, case_id = [], 100000
    start = pd.Timestamp("2025-01-06")
    span_days = 540

    for machine in machines:
        leak_share = {"antes": 0.32, "depois": 0.16}.get(machine["coorte"],
                                                          0.22)
        count = 6 if machine["serie"] in chronic else (
            1 + int(rng.random() < 0.30) + int(rng.random() < 0.08))
        is_chronic = machine["serie"] in chronic
        opened = start + pd.Timedelta(
            days=int(rng.integers(0, 60 if is_chronic else span_days)))
        for index in range(count):
            if index:
                gap = int(rng.integers(8, 60)) if (
                    is_chronic or rng.random() < 0.7
                ) else int(rng.integers(100, 200))
                opened += pd.Timedelta(days=gap)
            if opened > pd.Timestamp("2026-08-31"):
                break
            leak = rng.random() < leak_share
            symptom = LEAK if leak else str(rng.choice(SYMPTOMS))
            kit, code, conclusion = False, None, None
            if rng.random() > 0.20:  # 20% sem conclusão do técnico
                if (leak and machine["modelo"] == "Passione"
                        and rng.random() < 0.25):
                    kit, code = True, KIT_CODE
                    conclusion = KIT_TEXT
                else:
                    conclusion = str(rng.choice(CAUSES))
            if case_id == 100000:
                conclusion = f"Ligar para o cliente no {FAKE_PHONE}"
            serial = machine["serie"]
            if rng.random() < 0.05:  # série ilegível
                serial = str(rng.choice(["G5PS000DUPLICADO", "sem serie",
                                         "G5PS00021"]))
            rows.append({
                "Número do caso": case_id,
                "Classificação do Atendimento": "RECLAMAÇÃO",
                "Assunto CS": "MÁQUINA COM DEFEITO",
                "Detalhamento CS": symptom,
                "Tipo de registro do caso": "TRES",
                "Data de abertura": opened,
                "Nome do produto": "MAQUINA TRES PT 127V",
                "Número de série": serial,
                "Data da instalação": machine["fab"] + pd.Timedelta(days=60),
                "Modelo da Máquina": machine["modelo"],
                "Atendimento": "Externo",
                "Laudo Técnico": None if conclusion is None else "Reparo",
                "Motivo Técnico": None if conclusion is None else "Defeito",
                "Conclusão Técnica": conclusion,
                "Código da melhoria": code,
            })
            case_id += 1
    frame = pd.DataFrame(rows)
    truth = {
        "bandeja": {"serie_corte": CUT_SERIAL, "vazamento_antes": 0.32,
                    "vazamento_depois": 0.16, "veredito": "Funcionou"},
        "kit": {"codigo": KIT_CODE, "veredito": "Sem efeito mensurável"},
        "cronicas_planejadas": len(chronic),
        "telefone_falso": FAKE_PHONE,
        "chamados": int(len(frame)),
    }
    return frame, truth


def catalog() -> list[dict]:
    """Diretório de melhorias sintético (mesmo formato do real)."""
    base = {"modelo": "Passione", "sintoma_alvo": LEAK, "pecas": [],
            "termos_evidencia": [], "serie_inicial": None}
    return [
        {**base, "id": "SINT-BANDEJA", "codigo": "MEL-G5-CS-0001-Y",
         "titulo": "Bandeja de cápsulas (sintética)",
         "documento": "Boletim sintético 01", "data_documento": "2022-04-22",
         "tipo": "corte_serie", "serie_inicial": CUT_SERIAL,
         "componentes_alvo": ["bandeja"], "flag_evidencia": "mexeu_bandeja",
         "objetivo": "Efeito plantado: vazamento 32% para 16%."},
        {**base, "id": "SINT-KIT", "codigo": KIT_CODE,
         "titulo": "Adaptação hidráulica (sintética)",
         "documento": "Boletim sintético 02", "data_documento": "2022-10-11",
         "tipo": "retrofit_campo", "componentes_alvo": ["conexoes"],
         "flag_evidencia": "fez_adaptacao_hidraulica",
         "pecas": ["9000001 - TUBO SINTETICO"],
         "termos_evidencia": ["adapta"],
         "objetivo": "Efeito plantado: nenhum."},
    ]


def bulletin_pdf(text: str) -> bytes:
    """PDF mínimo de uma página, montado à mão."""
    safe = text.replace("(", "").replace(")", "")
    stream = f"BT /F1 10 Tf 10 700 Td ({safe}) Tj ET".encode(
        "latin-1", "ignore")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
            % (len(objs) + 1, xref))
    return out


BULLETINS = {
    "boletim_sintetico_kit.pdf": (
        "Boletim Tecnico Modelo: G5 Passione Numero de Serie: Indiferente "
        "Data:11/10/2022 Assunto: Adaptacao Hidraulica Revisao: 21/09/2023 "
        "9000001 - TUBO SINTETICO 9000002 - CONECTOR SINTETICO"),
    "boletim_sintetico_serie.pdf": (
        "Boletim Tecnico Modelo: G5 Passione Numero de Serie: "
        "G5PS000210224033 Data:22/04/2022 Assunto: Bandeja de capsulas "
        "Revisao: 01/01/2023 9000003 - BANDEJA SINTETICA"),
}


def main(out: Path) -> None:
    """Grava a planilha, a verdade plantada e o boletim sintético."""
    out.mkdir(parents=True, exist_ok=True)
    frame, truth = build()
    frame.to_excel(out / "base_sintetica.xlsx", index=False)
    opened = frame["Data de abertura"]
    for folder, name, part in [
        ("inicial", "base_inicial.xlsx", frame[opened < SPLIT_END]),
        ("complemento", "base_complemento.xlsx",
         frame[opened >= SPLIT_OVERLAP]),
    ]:
        (out / folder).mkdir(exist_ok=True)
        part.to_excel(out / folder / name, index=False)
    (out / "melhorias_vazia.json").write_text("[]\n", encoding="utf-8")
    (out / "ground_truth.json").write_text(
        json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "melhorias_sintetica.json").write_text(
        json.dumps(catalog(), ensure_ascii=False, indent=2),
        encoding="utf-8")
    for name, text in BULLETINS.items():
        (out / name).write_bytes(bulletin_pdf(text))
    print(f"{len(frame)} chamados em {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/synthetic"))
