"""Regressão: comparar antes × depois quando falta um dos grupos.

Achado pelos testes da API: uma base sem chamados de uma das coortes
(ex.: importação parcial) derrubava a tela com
``ValueError: cannot convert float NaN to integer``. A resposta correta
é "amostra insuficiente", não um erro.
"""

from __future__ import annotations

import math

import pandas as pd

from dna_maquina import impact
from dna_maquina.serial import serial_order_key

CUTOFF = "G5PS000210224033"


def _cutoff_item() -> impact.Improvement:
    return impact.Improvement(
        id="T-1",
        titulo="Teste",
        documento="t",
        modelo="Passione",
        data_documento="2022-04-22",
        tipo="corte_serie",
        sintoma_alvo="Máquina vazando",
        componentes_alvo=[],
        flag_evidencia="mexeu_bandeja",
        objetivo="t",
        serie_inicial=CUTOFF,
    )


def test_cutoff_with_only_cases_after_the_cutoff_does_not_crash(sample_frame):
    cutoff = serial_order_key(CUTOFF)
    only_after = sample_frame[sample_frame["chave_ordem"] >= cutoff]
    assert (only_after["modelo_serie"] == "Passione").any()

    result = impact.serial_cutoff_impact(only_after, _cutoff_item())

    assert math.isnan(result.p_valor)
    assert math.isnan(result.reducao_relativa)
    assert result.tabela.loc["Antes", "n"] == 0
    assert result.tabela["n"].min() < 100  # vira "amostra insuficiente"


def test_retrofit_without_any_case_with_the_kit_does_not_crash(sample_frame):
    item = impact.Improvement(
        id="T-2",
        titulo="Kit",
        documento="t",
        modelo="Passione",
        data_documento="2022-10-11",
        tipo="retrofit_campo",
        sintoma_alvo="Máquina vazando",
        componentes_alvo=[],
        flag_evidencia="fez_adaptacao_hidraulica",
        objetivo="t",
    )
    without_kit = sample_frame.assign(fez_adaptacao_hidraulica=False)

    result = impact.retrofit_impact(without_kit, item)

    assert isinstance(result.tabela, pd.DataFrame)
    assert math.isnan(result.p_valor)
    assert result.tabela.loc["Com kit", "n"] == 0
