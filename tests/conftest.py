"""Fixtures compartilhadas: base pequena, realista e isolada.

A fixture `client` troca a base do backend por uma amostra e redireciona
TODA escrita (modelos de ML, cache de LLM, catálogo) para uma
pasta temporária. Sem isso, um teste poderia gravar um modelo com
poucas linhas no volume real e o app passaria a usá-lo.
"""

from __future__ import annotations

import shutil

import numpy as np
import pandas as pd
import pytest

from dna_maquina import config, llm, reliability, risk
from dna_maquina.ingest import clean_complaints
from dna_maquina.pipeline import enrich

PHONE_NOTE = (
    "Corrigir o telefone para o número (11) 91234-5678 que é o correto"
)
PHONE_SERIAL = "G5PS000210224033"
SYMPTOMS = ["Máquina vazando", "Botões piscando/Luz acesa", "Não extrai"]
CONCLUSIONS = [
    "Realizado desentupimento do bico e teste de vazamento",
    "Trocado o oring do suporte do anel",
    "Feita adaptação hidráulica conforme boletim",
    "Orientado o consumidor",
]


def _serials(rng: np.random.Generator, count: int = 36) -> list[str]:
    """Séries nos três formatos reais (legado G5, novo G5 e Luna)."""
    serials = [PHONE_SERIAL]
    while len(serials) < count:
        kind = rng.integers(0, 3)
        week, number = rng.integers(1, 53), rng.integers(1, 99999)
        if kind == 0:
            year = rng.integers(21, 24)
            serials.append(f"G5PS000{year}{week:02d}{number:05d}")
        elif kind == 1:
            year = rng.integers(24, 26)
            serials.append(f"G5PS127{year}{week:02d}{number:05d}")
        else:
            year = rng.integers(23, 26)
            serials.append(f"G4LN127{year}{week:02d}{number:05d}")
    return serials


def sample_raw(first_case_id: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Planilha crua no layout do Salesforce (colunas originais)."""
    rng = np.random.default_rng(seed)
    rows, case_id = [], first_case_id
    for serial in _serials(rng):
        opened = pd.Timestamp("2025-01-10")
        for _ in range(int(rng.integers(1, 5))):
            opened += pd.Timedelta(days=int(rng.integers(5, 140)))
            if opened > pd.Timestamp("2026-08-31"):
                break
            conclusion = rng.choice(CONCLUSIONS + [None])
            if serial == PHONE_SERIAL and case_id == first_case_id:
                conclusion = PHONE_NOTE
            rows.append(
                {
                    "Número do caso": case_id,
                    "Classificação do Atendimento": "RECLAMAÇÃO",
                    "Assunto CS": "MÁQUINA COM DEFEITO",
                    "Detalhamento CS": rng.choice(SYMPTOMS),
                    "Tipo de registro do caso": "TRES",
                    "Data de abertura": opened,
                    "Nome do produto": "MAQUINA TRES PT 127V",
                    "Número de série": serial,
                    "Data da instalação": pd.Timestamp("2022-06-01"),
                    "Modelo da Máquina": "Luna"
                    if serial.startswith("G4")
                    else "Passione",
                    "Atendimento": "Externo",
                    "Laudo Técnico": None if conclusion is None else "Reparo",
                    "Motivo Técnico": None
                    if conclusion is None
                    else "Defeito",
                    "Conclusão Técnica": conclusion,
                }
            )
            case_id += 1
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def sample_frame() -> pd.DataFrame:
    """Base enriquecida de amostra (calculada uma vez por sessão)."""
    return enrich(clean_complaints(sample_raw()))


@pytest.fixture()
def client(monkeypatch, tmp_path, sample_frame):
    """Cliente HTTP do backend sobre a amostra, sem tocar o disco."""
    from fastapi.testclient import TestClient

    from app import bootstrap
    from app import state as state_module
    from app.main import app

    catalog = tmp_path / "melhorias.json"
    shutil.copy(config.PROJECT_ROOT / "data" / "melhorias.json", catalog)
    monkeypatch.setattr(bootstrap, "IMPROVEMENTS_PATH", catalog)
    for module, name in [
        (risk, "MODEL_FILE"),
        (risk, "METRICS_FILE"),
        (reliability, "CAUSE_MODEL_FILE"),
        (reliability, "CAUSE_METRICS_FILE"),
        (llm, "CACHE_FILE"),
    ]:
        monkeypatch.setattr(module, name, tmp_path / f"{name}.out")
    monkeypatch.setattr(state_module, "save", lambda *_a, **_k: None)
    st = state_module.state
    monkeypatch.setattr(st, "_df", sample_frame.copy())
    st._cache.clear()
    yield TestClient(app)
    st._cache.clear()
