"""
Testes das camadas de IA: modelo de risco (ML) e resumo com LLM.

Os testes não acessam a AWS: o cliente do Bedrock é substituído por um
"dublê" que devolve uma resposta fixa no mesmo formato da API Converse.
"""

from __future__ import annotations

import pandas as pd
import pytest

from dna_maquina import llm, risk
from dna_maquina.analytics import add_voice_agreement
from dna_maquina.history import add_machine_sequence
from dna_maquina.ingest import clean_complaints
from dna_maquina.taxonomy import classify_repairs


@pytest.fixture()
def small_base() -> pd.DataFrame:
    """Base mínima já enriquecida: uma máquina com 3 chamados."""
    base = {"Detalhamento CS": "Máquina vazando",
            "Número de série": "G5PS000220465809",
            "Modelo da Máquina": "Passione",
            "Data da instalação": "2022-09-02",
            "Laudo Técnico": "HIDRÁULICO",
            "Motivo Técnico": "TROCA DE CONEXOES HIDRAULICAS",
            "Conclusão Técnica": "troca do oring da unidade"}
    raw = pd.DataFrame([
        {**base, "Número do caso": 1, "Data de abertura": "2025-01-10"},
        {**base, "Número do caso": 2, "Data de abertura": "2025-02-01",
         "Conclusão Técnica": None, "Motivo Técnico": None,
         "Laudo Técnico": None},
        {**base, "Número do caso": 3, "Data de abertura": "2025-03-01"},
    ])
    data = add_voice_agreement(classify_repairs(clean_complaints(raw)))
    return add_machine_sequence(data)


class FakeBedrock:
    """Dublê do cliente ``bedrock-runtime``: registra a chamada."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [
            {"text": "Resumo gerado pelo modelo."}]}}}


def test_features_use_only_information_known_at_case_close(small_base):
    features = risk.build_features(small_base)
    assert list(features.columns) == risk.FEATURES
    assert "problema_voltou" not in features.columns  # sem vazamento
    assert features["tem_reparo_registrado"].tolist() == [1, 0, 1]


def test_capture_metric():
    y = pd.Series([1, 0, 1, 0, 0]).to_numpy()
    score = pd.Series([0.9, 0.8, 0.7, 0.1, 0.0]).to_numpy()
    assert risk._capture(y, score, 0.4) == 0.5  # top 2 pega 1 de 2


def test_facts_contain_only_data_from_the_base(small_base):
    facts = llm.build_machine_facts(small_base, "g5ps000220465809")
    assert "Chamados no período: 3" in facts
    assert "sem registro técnico" in facts


def test_offline_summary_when_bedrock_is_off(small_base, monkeypatch,
                                             tmp_path):
    monkeypatch.delenv("DNA_USE_BEDROCK", raising=False)
    monkeypatch.setattr(llm, "CACHE_FILE", tmp_path / "cache.json")
    result = llm.summarize(small_base, "G5PS000220465809")
    assert result.fonte == "regras"
    assert result.texto.startswith("3 chamados")


def test_bedrock_answer_is_cached(small_base, monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE_FILE", tmp_path / "cache.json")
    fake = FakeBedrock()
    first = llm.summarize(small_base, "G5PS000220465809", client=fake)
    second = llm.summarize(small_base, "G5PS000220465809", client=fake)
    assert (first.fonte, second.fonte) == ("bedrock", "cache")
    assert len(fake.calls) == 1
    assert "SOMENTE os fatos" in fake.calls[0]["system"][0]["text"]


# --------------------------------------------------------------------------
# IA para "histórico confiável" (reliability.py)
# --------------------------------------------------------------------------
def test_cohort_is_recovered_from_one_typo():
    from dna_maquina.reliability import recover_cohort

    # um "0" a mais no meio: série de 17 caracteres
    cohort = recover_cohort("G5PS0000220857911", pd.Timestamp("2023-01-10"),
                            "Passione")
    assert cohort == (2022, 8)


def test_ambiguous_or_implausible_serial_is_not_recovered():
    from dna_maquina.reliability import recover_cohort

    assert recover_cohort("G5PS000DUPLICADO", pd.Timestamp("2023-01-10"),
                          "Passione") is None


def test_confidence_score_penalizes_missing_technical_record(small_base):
    from dna_maquina.reliability import record_confidence

    scores = record_confidence(small_base).tolist()
    assert scores[0] == 100 and scores[1] < scores[0]


# --------------------------------------------------------------------------
# Ferramentas que a Cora chama (assistant.py)
# --------------------------------------------------------------------------
def test_unknown_tool_returns_error_instead_of_crashing(small_base):
    from dna_maquina.assistant import Toolbox

    assert "erro" in Toolbox(small_base).run("apagar_tudo", {})
