"""Boletim técnico: PDF, tipo por série e código de melhoria."""

from __future__ import annotations

import pytest

from app import boletim

KIT = ("Boletim Técnico Modelo: G5 Passione Número de Série: Indiferente "
       "Data:11/10/2022 Assunto: Adaptação Hidráulica Revisão: 21/09/2023 "
       "Itens 3002832 - TUBO SILIC G1 LOV 201051330 4CM "
       "3002821 - CONECTOR TUBO G1 LOV 02021900 "
       "3000053 - JUNÇÃO T Passo: 1 Link https://exemplo")
FACTORY = KIT.replace("Indiferente", "G5PS000210224033")


def make_pdf(text: str) -> bytes:
    """PDF mínimo de uma página, montado à mão (sem depender de lib)."""
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


def test_serial_indifferent_is_a_field_kit():
    got = boletim.parse_bulletin(KIT)
    assert got["tipo"] == "retrofit_campo" and got["serie_inicial"] is None
    assert got["modelo"] == "Passione"
    assert got["data_documento"] == "2022-10-11"
    assert got["revisao"] == "2023-09-21"
    assert [p.split(" - ")[0] for p in got["pecas"]] == [
        "3002832", "3002821", "3000053"]
    assert "201051330" not in " ".join(got["pecas"])


def test_serial_given_is_a_factory_cut():
    got = boletim.parse_bulletin(FACTORY)
    assert got["tipo"] == "corte_serie"
    assert got["serie_inicial"] == "G5PS000210224033"


def test_unreadable_serial_asks_for_manual_input():
    got = boletim.parse_bulletin(KIT.replace("Indiferente", "a partir de X"))
    assert got["tipo"] == "corte_serie" and got["serie_inicial"] is None
    assert got["avisos"]


def test_code_is_sequential_and_checked():
    first = boletim.make_code("Passione", "retrofit_campo", [])
    second = boletim.make_code("Passione", "retrofit_campo", [first])
    assert first.startswith("MEL-G5-RF-0001-")
    assert second.startswith("MEL-G5-RF-0002-")
    assert boletim.valid_code(first)
    assert not boletim.valid_code(first[:-1] + "Z" if first[-1] != "Z"
                                  else first[:-1] + "A")


@pytest.mark.parametrize("content", [b"nao sou pdf", b""])
def test_non_pdf_is_rejected(content):
    with pytest.raises(boletim.PdfError):
        boletim.extract_text(content)


def test_oversized_pdf_is_rejected():
    with pytest.raises(boletim.PdfError):
        boletim.extract_text(b"%PDF" + b"0" * boletim.MAX_BYTES)


def test_pdf_text_roundtrip():
    text = boletim.extract_text(make_pdf(KIT))
    assert "Adaptação" in text or "Adapta" in text
    assert boletim.parse_bulletin(text)["tipo"] == "retrofit_campo"


def test_api_reads_pdf_and_registers_with_code(client):
    pdf = make_pdf(KIT)
    read = client.post("/api/boletins/analisar",
                       files={"file": ("b.pdf", pdf, "application/pdf")})
    assert read.status_code == 200
    got = read.json()
    assert got["tipo"] == "retrofit_campo"
    preview = client.post("/api/boletins/previa", json={
        "modelo": "Passione", "termos": got["termos_sugeridos"],
        "pecas": got["pecas"]})
    assert preview.status_code == 200
    assert preview.json()["origem"] == "inferido"
    assert "conclusao" not in str(preview.json())
    created = client.post("/api/improvements", json={
        "titulo": got["titulo"], "modelo": "Passione",
        "tipo": got["tipo"], "data_documento": got["data_documento"],
        "pecas": got["pecas"], "termos_evidencia": ["adapta"]})
    assert created.status_code == 201
    code = created.json()["codigo"]
    assert boletim.valid_code(code)
    detail = client.get(f"/api/impact/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["melhoria"]["codigo"] == code


def test_api_rejects_non_pdf_upload(client):
    bad = client.post("/api/boletins/analisar",
                      files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert bad.status_code == 422


def test_registered_code_beats_text_inference():
    import pandas as pd

    from dna_maquina import impact

    item = impact.Improvement(
        id="X", titulo="t", documento="d", modelo="Passione",
        data_documento="2026-01-01", tipo="retrofit_campo",
        sintoma_alvo="s", componentes_alvo=[], flag_evidencia="evid_x",
        objetivo="o", codigo="MEL-G5-RF-0009-A", termos_evidencia=["kit"])
    df = pd.DataFrame({
        "conclusao": ["usou o kit", "nada", "outro"],
        "codigo_melhoria": ["MEL-G5-RF-0009-A", None, None]})
    assert impact.with_evidence(df, item)["evid_x"].tolist() == [
        True, False, False]
    df["codigo_melhoria"] = None  # ninguém registrou: cai nas palavras
    assert impact.with_evidence(df, item)["evid_x"].tolist() == [
        True, False, False]
    df["conclusao"] = ["nada", "kit", "x"]
    assert impact.with_evidence(df, item)["evid_x"].tolist() == [
        False, True, False]


def test_import_accepts_code_column(client):
    import io

    from conftest import sample_raw

    raw = sample_raw()
    raw["Código da melhoria"] = "mel-g5-rf-0001-b"
    buffer = io.BytesIO()
    raw.to_excel(buffer, index=False)
    sent = client.post("/api/import", files={"file": (
        "n.xlsx", buffer.getvalue(), "application/octet-stream")})
    assert sent.status_code == 200
    items = {i["controle"]: i for i in client.get("/api/quality").json()[
        "itens"]}
    assert items["Chamados com código de melhoria registrado"][
        "registros"] > 0


def test_impact_reports_evidence_origin(client):
    first = client.get("/api/impact").json()[0]
    body = client.get(f"/api/impact/{first['id']}").json()
    assert body["evidencia"]["origem"] in {"serie", "inferida", "registrada"}
    assert body["melhoria"]["codigo"] == first["codigo"]


def test_old_catalog_gets_codes_on_read(client):
    codes = [i["codigo"] for i in client.get("/api/impact").json()]
    assert all(codes) and len(set(codes)) == len(codes)


def test_every_recommendation_has_evidence_and_prototype_note(client):
    body = client.get("/api/diagnostico").json()
    ids = {s["id"] for s in body["sintomas"]}
    for item in body["melhorias_a_implantar"]:
        assert item["evidencia"] in ids
        assert item["no_prototipo"]


def test_empty_catalog_does_not_break_the_api(client, tmp_path):
    from app import bootstrap

    bootstrap.IMPROVEMENTS_PATH.write_text("[]", encoding="utf-8")
    assert client.get("/api/impact").json() == []
    for route in ["/api/diagnostico", "/api/times", "/api/quality",
                  "/api/overview"]:
        assert client.get(route).status_code == 200, route
