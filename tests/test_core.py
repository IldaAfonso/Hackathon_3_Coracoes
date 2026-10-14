"""
Testes unitários do núcleo analítico (rodar com ``pytest`` na raiz).

Cada teste documenta uma premissa de negócio — se a premissa mudar
(ex.: novo formato de série), o teste correspondente deve ser revisto.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from dna_maquina.history import add_machine_sequence
from dna_maquina.impact import two_proportion_test, wilson_interval
from dna_maquina.ingest import SchemaError, clean_complaints, merge_bases
from dna_maquina.serial import normalize_serial, parse_serial, serial_order_key
from dna_maquina.taxonomy import find_components, strip_accents, voices_agree


# --------------------------------------------------------------------------
# Número de série
# --------------------------------------------------------------------------
def test_legacy_serial_is_decoded_as_year_and_week():
    info = parse_serial("G5PS000210224033")  # série de corte da bandeja
    assert info.valida and info.formato == "legado"
    assert (info.ano_fab, info.semana_fab, info.sequencial) == (2021, 2, 24033)


def test_new_serial_format_with_voltage():
    info = parse_serial("G4LN127232802098")
    assert info.modelo_serie == "Luna"
    assert (info.ano_fab, info.semana_fab) == (2023, 28)


@pytest.mark.parametrize("raw, expected", [
    ("g5ps000210224033", "G5PS000210224033"),   # minúsculas
    (" G5PS 000210224033 ", "G5PS000210224033"),  # espaços
    ("G5P5000210224033", "G5PS000210224033"),   # 5 no lugar de S
])
def test_serial_typos_are_normalized(raw, expected):
    assert normalize_serial(raw) == expected


def test_garbage_serial_is_invalid():
    assert not parse_serial("G5PS000DUPLICADO").valida
    assert not parse_serial(float("nan")).valida


def test_order_key_respects_production_order():
    cutoff = serial_order_key("G5PS000210224033")
    assert serial_order_key("G5PS000210124033") < cutoff   # semana 01
    assert serial_order_key("G5PS127241004388") > cutoff   # formato novo 2024


# --------------------------------------------------------------------------
# Taxonomia (voz do técnico)
# --------------------------------------------------------------------------
def test_strip_accents_handles_handwritten_text():
    assert strip_accents("HIGIENIZAÇÃO") == "higienizacao"
    assert strip_accents(None) == ""


def test_replacement_part_outranks_cleaning():
    text = strip_accents("Troca da unidade de extração, higienização")
    assert find_components(text)[0] == "unidade_extracao"


def test_voices_agreement_rules():
    assert voices_agree("Máquina vazando", ["vedacao_oring"]) is True
    assert voices_agree("Máquina não liga", ["bico_saida"]) is False
    assert voices_agree("Sintoma sem regra", ["bomba"]) is None


# --------------------------------------------------------------------------
# Estatística
# --------------------------------------------------------------------------
def test_wilson_interval_contains_point_estimate():
    low, high = wilson_interval(20, 100)
    assert low < 0.20 < high


def test_two_proportion_test_detects_clear_difference():
    assert two_proportion_test(200, 1000, 100, 1000) < 0.001
    assert math.isclose(two_proportion_test(10, 100, 10, 100), 1.0)


# --------------------------------------------------------------------------
# Ingestão e DNA
# --------------------------------------------------------------------------
def _raw_sheet(rows: list[dict]) -> pd.DataFrame:
    """Monta um DataFrame com o layout original da planilha."""
    base = {"Número do caso": 1, "Detalhamento CS": "Máquina vazando",
            "Data de abertura": "2025-01-01",
            "Número de série": "G5PS000210224033",
            "Modelo da Máquina": "Passione",
            "Data da instalação": "2022-01-01",
            "Conclusão Técnica": "troca do oring", "Laudo Técnico": None,
            "Motivo Técnico": None}
    return pd.DataFrame([{**base, **row} for row in rows])


def test_missing_required_column_raises_clear_error():
    raw = _raw_sheet([{}]).drop(columns=["Número de série"])
    with pytest.raises(SchemaError, match="Número de série"):
        clean_complaints(raw)


def test_merge_keeps_latest_version_of_same_case():
    old = clean_complaints(_raw_sheet([{"Conclusão Técnica": None}]))
    new = clean_complaints(_raw_sheet([{"Conclusão Técnica": "troca bomba"}]))
    merged = merge_bases(old, new)
    assert len(merged) == 1
    assert merged["conclusao"].iat[0] == "troca bomba"


def test_reincidence_within_90_days():
    clean = clean_complaints(_raw_sheet([
        {"Número do caso": 1, "Data de abertura": "2025-01-01"},
        {"Número do caso": 2, "Data de abertura": "2025-02-15"},
        {"Número do caso": 3, "Data de abertura": "2025-12-01"},
    ]))
    seq = add_machine_sequence(clean).sort_values("case_id")
    assert seq["reincidente"].tolist() == [False, True, False]
    assert seq["ordem_na_maquina"].tolist() == [1, 2, 3]
