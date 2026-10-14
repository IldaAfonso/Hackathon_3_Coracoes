"""Boletins técnicos: ler o PDF e mostrar os dados relacionados."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import boletim
from app.common import evidence_origin, improvements
from app.privacy import mask_text
from app.state import state
from dna_maquina import impact as impact_core

router = APIRouter(prefix="/boletins", tags=["boletins"])


@router.get("/cadastrados")
def registered() -> list[dict]:
    """Boletins já cadastrados, do mais recente ao mais antigo.

    Cada boletim cadastrado vira uma melhoria com o seu **código do
    projeto da melhoria** (``MEL-<modelo>-<RF|CS>-<seq>-<letra>``): é o
    código que o técnico escolhe no chamado e que o P&D usa para medir
    o efeito. A lista é a mesma para o P&D e o Pós-venda; só o P&D
    cadastra novos.
    """
    items = sorted(improvements(), key=lambda i: i.data_documento,
                   reverse=True)
    return [
        {
            "id": item.id,
            "codigo": item.codigo,
            "titulo": mask_text(item.titulo),
            "modelo": item.modelo,
            "tipo": item.tipo,
            "data_documento": item.data_documento,
            "documento": mask_text(item.documento),
            "serie_inicial": item.serie_inicial,
            "pecas": list(item.pecas),
            "objetivo": mask_text(item.objetivo),
            "vinculo": evidence_origin(item),
        }
        for item in items
    ]


@router.post("/analisar")
async def read_bulletin(file: UploadFile) -> dict:
    """Lê o PDF em memória e sugere os campos. Nada é gravado."""
    content = await file.read(boletim.MAX_BYTES + 1)
    try:
        text = boletim.extract_text(content)
    except boletim.PdfError as error:
        raise HTTPException(422, str(error)) from error
    result = boletim.parse_bulletin(text)
    if not result["titulo"] and not result["pecas"]:
        raise HTTPException(
            422, "Não reconheci um boletim técnico neste PDF.")
    return result


class PreviewIn(BaseModel):
    """Modelo e termos a procurar no texto livre dos técnicos."""

    modelo: str
    termos: list[str] = Field(min_length=1, max_length=8)
    pecas: list[str] = Field(default_factory=list, max_length=30)


@router.post("/previa")
def preview(body: PreviewIn) -> dict:
    """Quantos chamados e máquinas se relacionam (só contagens)."""
    terms = [t.strip() for t in body.termos if len(t.strip()) >= 3]
    if not terms:
        raise HTTPException(422, "Informe ao menos um termo (3+ letras).")
    df = state.df
    df = df[df["modelo"] == body.modelo]
    mask = impact_core.text_mentions(df, terms)
    hit = df[mask]
    monthly = (hit.groupby("mes").size().rename("chamados")
               .reset_index().astype({"mes": str}))
    codes = {c.split(" - ")[0].strip(): c for c in body.pecas}
    part_counts = {
        code: int(df["conclusao"].fillna("").str.contains(
            code, regex=False).sum())
        for code in codes
    }
    return {
        "chamados_modelo": int(len(df)),
        "chamados_relacionados": int(len(hit)),
        "maquinas": int(hit.loc[hit["valida"], "serie"].nunique()),
        "mensal": monthly.to_dict("records"),
        "pecas_citadas": [
            {"peca": codes[c], "chamados": n}
            for c, n in part_counts.items()
        ],
        "origem": "inferido",
        "aviso": ("Contagem por palavras no texto livre (inferido). "
                  "Só o código registrado no chamado é evidência exata."),
    }
