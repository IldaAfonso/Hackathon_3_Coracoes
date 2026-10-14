"""Estoque × melhoria: cada teste documenta uma regra do levantamento.

* série anterior ao corte de fábrica -> aplicar antes de vender;
* kit de campo: fabricada antes da semana do boletim -> pendente;
* código do projeto já registrado no estoque -> aplicada;
* vendida e outro modelo não entram; série ilegível -> verificar;
* a API troca a base pelo arquivo importado e grava as marcações.
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd
import pytest

from dna_maquina import stock
from dna_maquina.impact import Improvement

SERIES_CUT = "G5PS000210224033"  # corte da bandeja (2021, semana 02)


def _item(**extra) -> Improvement:
    base = dict(
        id="X", titulo="Teste", documento="BT", modelo="Passione",
        data_documento="2022-10-11", tipo="retrofit_campo",
        sintoma_alvo="Máquina vazando", componentes_alvo=[],
        flag_evidencia="", objetivo="", pecas=["3000053 - JUNÇÃO"],
        codigo="MEL-G5-RF-0002-R")
    base.update(extra)
    return Improvement(**base)


def _stock(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    return stock.clean_stock(frame.rename(columns={
        v: k for k, v in stock.STOCK_COLUMN_MAP.items()}))


def _status(result: stock.StockSurvey) -> dict[str, str]:
    """Série -> situação, para ler o resultado nos testes."""
    return result.maquinas.set_index("serie")["status"].to_dict()


@pytest.fixture
def sample() -> pd.DataFrame:
    return _stock([
        {"serie": "G5PS000210112345", "local": "CD Sul",
         "data_entrada": "2026-01-10"},                      # 2021 S01
        {"serie": "G5PS000224012345", "local": "CD Sul",
         "data_entrada": "2026-02-10"},                      # 2022 S40
        {"serie": "G5PS000224212345", "local": "CD Sul",
         "data_entrada": "2026-03-10"},                      # 2022 S42
        {"serie": "G5PS000220100001", "local": "CD Sul",
         "melhorias_aplicadas": "MEL-G5-RF-0002-R"},         # já aplicada
        {"serie": "G5PS000220100002", "situacao": "vendida"},
        {"serie": "G4LN127230100001", "local": "CD Sul"},    # Luna
        {"serie": "G5PS000DUPLICADO", "modelo": "Passione"},
    ])


def test_factory_change_flags_serials_before_the_cut(sample):
    result = stock.survey(sample, _item(tipo="corte_serie",
                                        serie_inicial=SERIES_CUT))
    status = _status(result)
    assert status["G5PS000210112345"] == "pendente"
    assert status["G5PS000224012345"] == "de_fabrica"


def test_field_kit_uses_the_bulletin_week_as_factory_cut(sample):
    status = _status(stock.survey(sample, _item()))
    assert status["G5PS000224012345"] == "pendente"      # S40 < S41
    assert status["G5PS000224212345"] == "de_fabrica"    # S42 >= S41
    assert status["G5PS000220100001"] == "aplicada"
    assert status["G5PS000DUPLICADO"] == "verificar"


def test_sold_and_other_model_are_left_out(sample):
    series = set(stock.survey(sample, _item()).maquinas["serie"])
    assert "G5PS000220100002" not in series      # vendida
    assert "G4LN127230100001" not in series      # Luna x melhoria Passione


def test_marks_from_the_screen_count_as_applied(sample):
    marks = {("G5PS000224012345", "MEL-G5-RF-0002-R")}
    result = stock.survey(sample, _item(), marks)
    row = result.maquinas.set_index("serie").loc["G5PS000224012345"]
    assert row["status"] == "aplicada"


def test_pending_first_oldest_entry_first_and_pieces(sample):
    result = stock.survey(sample, _item(), today=date(2026, 10, 14))
    assert result.maquinas["status"].iloc[0] == "pendente"
    summary = stock.summarize(result, _item())
    assert summary["pendentes"] == 2
    assert summary["pecas_necessarias"] == [
        {"peca": "3000053 - JUNÇÃO", "quantidade": 2}]


def test_missing_serial_column_is_a_clear_error():
    with pytest.raises(stock.StockSchemaError):
        stock.clean_stock(pd.DataFrame({"Local": ["CD"]}))


def test_brazilian_dates_are_read_day_first():
    df = _stock([{"serie": "G5PS000210112345",
                  "data_entrada": "03/08/2026"}])
    assert df["data_entrada"].iloc[0] == pd.Timestamp("2026-08-03")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@pytest.fixture
def api(client, tmp_path, monkeypatch):
    """Cliente com estoque e marcações em pasta temporária."""
    from app.routers import stock as router

    monkeypatch.setattr(router, "STOCK_FILE", tmp_path / "estoque.csv")
    monkeypatch.setattr(router, "MARKS_FILE", tmp_path / "marcas.json")
    monkeypatch.setattr(router, "cache", router._StockCache())
    return client


def test_api_uses_the_example_until_a_file_is_imported(api):
    body = api.get("/api/estoque").json()
    assert body["fonte"] == "exemplo" and body["aviso"]
    csv = stock.TEMPLATE_CSV.encode("utf-8")
    reply = api.post("/api/estoque/importar",
                     files={"file": ("estoque.csv", io.BytesIO(csv))})
    assert reply.status_code == 200, reply.text
    body = api.get("/api/estoque").json()
    assert body["fonte"] == "importada" and body["em_estoque"] == 2


def test_api_survey_and_mark_applied(api):
    found = api.get("/api/estoque/melhoria/G5-ADAPT-HIDR-2022").json()
    pending = [m for m in found["maquinas"] if m["status"] == "pendente"]
    assert pending and found["pendentes"] == len(pending)
    serial = pending[0]["serie"]
    mark = api.post("/api/estoque/aplicacoes", json={
        "serie": serial, "codigo": "MEL-G5-RF-0002-R"})
    assert mark.status_code == 200
    again = api.get("/api/estoque/melhoria/G5-ADAPT-HIDR-2022").json()
    assert again["pendentes"] == found["pendentes"] - 1
    undo = api.post("/api/estoque/aplicacoes", json={
        "serie": serial, "codigo": "MEL-G5-RF-0002-R", "aplicada": False})
    assert undo.status_code == 200
    assert api.get("/api/estoque/melhoria/G5-ADAPT-HIDR-2022").json()[
        "pendentes"] == found["pendentes"]


def test_api_rejects_unknown_serial_and_bad_file(api):
    assert api.post("/api/estoque/aplicacoes", json={
        "serie": "G5PS000299999999", "codigo": "MEL-G5-RF-0002-R"}
    ).status_code == 404
    bad = api.post("/api/estoque/importar",
                   files={"file": ("x.csv", io.BytesIO(b"Local\nCD"))})
    assert bad.status_code == 422
