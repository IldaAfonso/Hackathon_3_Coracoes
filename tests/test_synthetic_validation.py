"""Base sintética: o protótipo acha o que foi plantado?"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from dna_maquina import impact
from dna_maquina.ingest import clean_complaints
from dna_maquina.pipeline import enrich

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def synthetic():
    spec = importlib.util.spec_from_file_location(
        "make_synthetic", ROOT / "scripts" / "make_synthetic_base.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["make_synthetic"] = module
    spec.loader.exec_module(module)
    raw, truth = module.build()
    items = [impact.Improvement(**i) for i in module.catalog()]
    return enrich(clean_complaints(raw)), truth, items, module


def test_factory_change_planted_effect_is_found(synthetic):
    df, _truth, items, _m = synthetic
    result = impact.evaluate(df, items[0])
    assert result.reducao_relativa > 0.3
    assert result.p_valor < 0.001


def test_kit_without_effect_is_not_declared_a_win(synthetic):
    df, _truth, items, _m = synthetic
    result = impact.evaluate(df, items[1])
    assert result.p_valor > 0.05


def test_registered_code_links_exactly_the_kit_cases(synthetic):
    df, _truth, items, _m = synthetic
    flagged = impact.with_evidence(df, items[1])[items[1].flag_evidencia]
    assert int(flagged.sum()) == int(df["codigo_melhoria"].eq(
        items[1].codigo).sum()) > 100


def test_without_the_column_it_falls_back_to_text(synthetic):
    df, _truth, items, _m = synthetic
    item = items[1]
    item.flag_evidencia = "evid_teste"
    plain = df.drop(columns=["codigo_melhoria"])
    flagged = impact.with_evidence(plain, item)["evid_teste"]
    registered = df["codigo_melhoria"].eq(item.codigo)
    assert int((flagged & registered).sum()) == int(registered.sum())


def test_planted_quality_problems_are_reported(synthetic):
    df, truth, _items, _m = synthetic
    assert 0.03 < df["dq_serie_invalida"].mean() < 0.07
    assert int(df["conclusao"].fillna("").str.contains(
        truth["telefone_falso"], regex=False).sum()) == 1


def test_chronic_machines_are_found(synthetic):
    df, truth, _items, _m = synthetic
    per = df[~df["dq_serie_invalida"]].groupby("serie").size()
    assert int((per >= 5).sum()) >= truth["cronicas_planejadas"] * 0.8


def test_synthetic_bulletins_are_read_with_the_right_type(synthetic):
    from app import boletim

    *_rest, module = synthetic
    kinds = {}
    for name, text in module.BULLETINS.items():
        pdf = module.bulletin_pdf(text)
        kinds[name] = boletim.parse_bulletin(boletim.extract_text(pdf))
    assert kinds["boletim_sintetico_kit.pdf"]["tipo"] == "retrofit_campo"
    serie = kinds["boletim_sintetico_serie.pdf"]
    assert serie["tipo"] == "corte_serie"
    assert serie["serie_inicial"] == "G5PS000210224033"


def test_ground_truth_file_matches_generator(synthetic):
    _df, truth, _items, _m = synthetic
    saved = json.loads((ROOT / "data" / "synthetic"
                        / "ground_truth.json").read_text(encoding="utf-8"))
    assert saved == truth
