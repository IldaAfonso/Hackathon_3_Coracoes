"""Testes da API: o contrato que a interface web consome.

Cada teste documenta uma garantia do produto. Rodam sobre uma amostra
pequena (ver conftest.py), sem rede e sem tocar o disco real.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest
from conftest import PHONE_SERIAL, sample_raw


def test_health_reports_loaded_base(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["chamados"] > 50


def test_meta_describes_period_and_models(client):
    body = client.get("/api/meta").json()
    assert body["periodo"]["inicio"] < body["periodo"]["fim"]
    assert {"Passione", "Luna"} <= set(body["modelos"])


def test_diagnostic_proves_that_todays_history_falls_short(client):
    body = client.get("/api/diagnostico").json()
    ids = {s["id"] for s in body["sintomas"]}
    assert {"sem_conclusao", "reincidencia", "serie_invalida"} <= ids
    for symptom in body["sintomas"]:
        value = symptom["valor"]
        assert value is None or value >= 0
        assert symptom["time"] and symptom["leitura"]
    priorities = [m["prioridade"] for m in body["melhorias_a_implantar"]]
    assert priorities == sorted(priorities) and len(priorities) >= 3


def test_serial_number_links_the_three_teams(client):
    body = client.get("/api/times").json()
    assert body["chave"] == "número de série"
    assert [t["id"] for t in body["times"]] == ["cs", "pos", "pd"]
    link = body["ligacao"]
    assert 0 <= link["pct_chamados_serie_valida"] <= 1
    assert link["com_registro_tecnico"] <= link["maquinas_com_chamado"]


def test_overview_filters_by_model_and_rejects_empty_result(client):
    body = client.get("/api/overview", params={"modelos": "Luna"}).json()
    assert body["totais"]["chamados"] > 0
    assert (
        client.get(
            "/api/overview", params={"modelos": "Inexistente"}
        ).status_code
        == 404
    )


def test_machine_search_accepts_lowercase_and_spaces(client):
    found = client.get(
        "/api/machines/search", params={"q": "g5ps 0002"}
    ).json()
    assert found and all(m["serie"].startswith("G5PS0002") for m in found)


def test_machine_dna_has_timeline_with_both_voices(client):
    body = client.get(f"/api/machines/{PHONE_SERIAL}").json()
    assert body["ficha"]["serie"] == PHONE_SERIAL
    event = body["linha_do_tempo"][0]
    assert event["consumidor"] and "conclusao" in event["tecnico"]
    assert "disponivel" in body["ia"]  # ML pode faltar numa amostra mínima
    assert {m["status"] for m in body["melhorias"]} <= {
        "de_fabrica",
        "antes_da_melhoria",
        "aplicada_em_campo",
        "sem_registro",
    }


def test_unknown_machine_is_404(client):
    response = client.get("/api/machines/G5PS000999999999")
    assert response.status_code == 404


def test_no_phone_number_leaves_the_api(client):
    """O telefone digitado pelo técnico não chega ao navegador."""
    text = client.get(f"/api/machines/{PHONE_SERIAL}").text
    assert "91234" not in text and "5678" not in text
    assert "[telefone]" in text


def test_improvement_catalog_and_evaluation(client):
    catalog = client.get("/api/impact").json()
    assert catalog and {"id", "titulo", "tipo"} <= set(catalog[0])
    body = client.get(f"/api/impact/{catalog[0]['id']}").json()
    assert body["veredito"] in {
        "Funcionou",
        "Piorou",
        "Sem efeito mensurável",
        "Amostra insuficiente",
    }
    assert client.get("/api/impact/NAO-EXISTE").status_code == 404


def test_small_sample_never_becomes_a_conclusion(client):
    """Poucos chamados: a resposta honesta é 'insuficiente'."""
    first = client.get("/api/impact").json()[0]["id"]
    body = client.get(f"/api/impact/{first}").json()
    assert body["veredito"] == "Amostra insuficiente"


def test_pd_can_register_a_field_improvement(client):
    body = {
        "titulo": "Novo kit de mangueira",
        "modelo": "Passione",
        "tipo": "retrofit_campo",
        "data_documento": "2026-10-13",
    }
    created = client.post("/api/improvements", json=body)
    assert created.status_code == 201
    ids = {i["id"] for i in client.get("/api/impact").json()}
    assert created.json()["id"] in ids


@pytest.mark.parametrize("serial", [None, "lixo", ""])
def test_factory_change_requires_a_valid_start_serial(client, serial):
    body = {
        "titulo": "Mudança de bandeja",
        "modelo": "Passione",
        "tipo": "corte_serie",
        "serie_inicial": serial,
        "data_documento": "2026-10-13",
    }
    assert client.post("/api/improvements", json=body).status_code == 422


def test_improvement_date_must_be_iso(client):
    body = {
        "titulo": "Kit",
        "modelo": "Passione",
        "tipo": "retrofit_campo",
        "data_documento": "13/10/2026",
    }
    assert client.post("/api/improvements", json=body).status_code == 422


def test_quality_report_includes_personal_data_control(client):
    items = client.get("/api/quality").json()["itens"]
    pii = [i for i in items if "dado pessoal" in i["controle"]]
    assert pii and pii[0]["registros"] >= 1  # o telefone da amostra


def _xlsx(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    return buffer.getvalue()


def test_import_merges_new_cases_without_duplicating(client):
    before = client.get("/api/health").json()["chamados"]
    new_cases = sample_raw(first_case_id=50000, seed=7)
    response = client.post(
        "/api/import",
        files={
            "file": ("nova.xlsx", _xlsx(new_cases), "application/octet-stream")
        },
    )
    body = response.json()
    assert response.status_code == 200 and body["antes"] == before
    assert body["depois"] == before + body["lidos"]
    again = client.post(
        "/api/import",
        files={
            "file": ("nova.xlsx", _xlsx(new_cases), "application/octet-stream")
        },
    ).json()
    assert again["depois"] == body["depois"]  # reimportar não duplica


@pytest.mark.parametrize(
    "name, content",
    [
        ("dados.csv", b"a,b"),
        ("quebrado.xlsx", b"nao e excel"),
    ],
)
def test_import_rejects_bad_files(client, name, content):
    response = client.post("/api/import", files={"file": (name, content)})
    assert response.status_code == 422


def test_import_names_the_missing_columns(client):
    wrong = _xlsx(pd.DataFrame({"coluna qualquer": [1, 2]}))
    response = client.post("/api/import", files={"file": ("x.xlsx", wrong)})
    assert response.status_code == 422
    assert "Número de série" in response.json()["detail"]


def test_unexpected_errors_do_not_leak_internals(monkeypatch):
    """500 devolve mensagem neutra; o detalhe vai para o log."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import health

    class Broken:
        @property
        def df(self):
            raise RuntimeError("segredo interno /app/data/raw/arquivo.xlsx")

    monkeypatch.setattr(health, "state", Broken())
    response = TestClient(app, raise_server_exceptions=False).get(
        "/api/health"
    )
    assert response.status_code == 500
    assert "segredo" not in response.text and "/app/" not in response.text


def test_assistant_lists_offline_presets(client):
    presets = client.get("/api/assistant/presets").json()
    assert len(presets) >= 3
    assert (
        client.post(
            "/api/assistant/preset",
            json={"pergunta": "pergunta que não existe"},
        ).status_code
        == 404
    )


def test_machine_counts_ignore_unreadable_serials(client, sample_frame):
    """Série ilegível não é máquina: não pode inflar a contagem."""
    from app.state import state

    broken = sample_frame.copy()
    broken["dq_serie_invalida"] = False
    broken.loc[broken.index[:12], "dq_serie_invalida"] = True
    broken.loc[broken.index[:12], "serie"] = "ILEGIVEL"  # vira 1 "máquina"
    state._df = broken
    state._cache.clear()

    link = client.get("/api/times").json()["ligacao"]
    expected = broken.loc[~broken["dq_serie_invalida"], "serie"].nunique()
    assert link["maquinas_com_chamado"] == expected


def test_text_sent_to_the_llm_has_no_personal_data(client, monkeypatch):
    """O que vai para a AWS também é mascarado, não só o que volta.

    O prompt do resumo leva o texto digitado pelo técnico; o telefone
    real da base não pode sair da máquina rumo ao Bedrock.
    """
    from dna_maquina import llm

    sent = []

    def fake_bedrock(facts, client=None):
        sent.append(facts)
        return "Resumo de teste."

    monkeypatch.setenv("DNA_USE_BEDROCK", "1")
    monkeypatch.setattr(llm, "call_bedrock", fake_bedrock)
    body = client.get(f"/api/machines/{PHONE_SERIAL}").json()

    assert body["resumo"]["fonte"] == "bedrock" and sent
    assert "91234" not in sent[0] and "5678" not in sent[0]
    assert "[telefone]" in sent[0]


def test_assistant_points_to_cora(client, monkeypatch):
    """A página Assistente acha a Cora pela API (nada fixo no JS)."""
    from app import settings

    monkeypatch.setattr(settings, "CORA_URL", "http://localhost:8000")
    body = client.get("/api/assistant/cora").json()
    assert body["configurada"] is True
    assert body["embed_url"] == "http://localhost:8000/embed"
    assert body["origem"] == "http://localhost:8000"

    monkeypatch.setattr(settings, "CORA_URL", "javascript:alert(1)")
    assert client.get("/api/assistant/cora").json()["configurada"] is False


def test_bedrock_assistant_route_is_gone(client):
    """A conversa livre agora é da Cora: o MVP não chama mais LLM."""
    response = client.post("/api/assistant/ask", json={"pergunta": "oi?"})
    assert response.status_code in (404, 405)


def test_memo_by_rules_needs_no_ai(client):
    body = client.post(
        "/api/assistant/parecer", json={"id_melhoria": "G5-BANDEJA-2022"}
    ).json()
    assert body["fonte"] == "regras"
    assert body["texto"].startswith("Decisão de engenharia")


def test_registered_bulletins_always_carry_the_project_code(client):
    """Boletim sem código não serve: o técnico não o acharia."""
    rows = client.get("/api/boletins/cadastrados").json()
    assert rows and all(r["codigo"].startswith("MEL-") for r in rows)
    dates = [r["data_documento"] for r in rows]
    assert dates == sorted(dates, reverse=True)
    assert {"pecas", "vinculo", "tipo"} <= set(rows[0])
