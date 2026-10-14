"""Qualidade dos dados e importação de uma nova base."""

from __future__ import annotations

import io
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.boletim import valid_code
from app.common import improvements
from app.privacy import count_matches
from app.settings import MAX_UPLOAD_BYTES
from app.state import state
from dna_maquina.ingest import SchemaError, clean_complaints, merge_bases
from dna_maquina.pipeline import enrich

router = APIRouter(tags=["dados"])

QUALITY_FLAGS = {
    "Série inválida ou ilegível": "dq_serie_invalida",
    "Instalação com data impossível": "dq_instalacao_suspeita",
    "Chamado aberto antes da instalação": "dq_abertura_antes_instalacao",
    "Sem conclusão técnica": "dq_sem_conclusao",
    "Série ilegível com coorte recuperada (IA)": "coorte_recuperada",
}
PII_LABEL = (
    "Texto livre com possível dado pessoal (telefone, e-mail, "
    "CPF); mascarado na API"
)


@router.get("/quality")
def quality() -> dict:
    """Controles de qualidade da base atual."""
    df = state.df
    items = [
        {
            "controle": label,
            "registros": int(df[flag].sum()),
            "percentual": float(df[flag].mean()),
        }
        for label, flag in QUALITY_FLAGS.items()
        if flag in df
    ]
    personal = count_matches(df["conclusao"]) if "conclusao" in df else 0
    items.append(
        {
            "controle": PII_LABEL,
            "registros": personal,
            "percentual": personal / len(df),
        }
    )
    items += _bulletin_code_items(df)
    return {"itens": items}


def _bulletin_code_items(df: pd.DataFrame) -> list[dict]:
    """Chamados com código de melhoria e códigos que não batem."""
    if "codigo_melhoria" not in df:
        return []
    filled = df["codigo_melhoria"].dropna()
    known = {i.codigo for i in improvements()}
    unknown = ~filled.isin(known) | ~filled.map(valid_code)
    return [
        {"controle": "Chamados com código de melhoria registrado",
         "registros": int(len(filled)),
         "percentual": len(filled) / len(df)},
        {"controle": "Código de melhoria inválido ou fora do catálogo",
         "registros": int(unknown.sum()),
         "percentual": float(unknown.sum()) / len(df)},
    ]


def _read_upload(content: bytes) -> pd.DataFrame:
    """Lê e valida uma planilha enviada, com erros explicáveis (422)."""
    try:
        return clean_complaints(pd.read_excel(io.BytesIO(content)))
    except SchemaError as error:
        raise HTTPException(422, str(error)) from error
    except Exception as error:  # noqa: BLE001 - arquivo corrompido
        raise HTTPException(
            422, f"Não consegui ler a planilha: {error}"
        ) from error


@router.post("/import")
async def import_base(file: Annotated[UploadFile, File()]) -> dict:
    """Importa nova extração .xlsx, sem duplicar o que já existe."""
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(422, "Envie uma planilha .xlsx.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Arquivo acima do limite de tamanho.")
    incoming = _read_upload(content)
    before = len(state.df)
    merged = enrich(merge_bases(state.df, incoming))
    state.replace(merged)
    return {
        "lidos": int(len(incoming)),
        "antes": int(before),
        "depois": int(len(merged)),
    }
