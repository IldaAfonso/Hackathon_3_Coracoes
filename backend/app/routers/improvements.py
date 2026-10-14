"""Melhoria × impacto: a pergunta que nunca voltava para a engenharia.

Funcionou? Compara os chamados antes e depois de cada melhoria, com
intervalo de confiança, e permite ao P&D cadastrar a próxima.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import boletim, bootstrap
from app.common import (
    as_number,
    evidence_origin,
    improvements,
    verdict,
)
from app.serializers import df_json
from app.state import state
from dna_maquina import config
from dna_maquina import impact as impact_core
from dna_maquina.serial import parse_serial

router = APIRouter(tags=["melhorias"])


@router.get("/impact")
def list_improvements() -> list[dict]:
    """Catálogo de melhorias cadastradas pelo P&D."""
    return [
        {
            "id": i.id,
            "codigo": i.codigo,
            "titulo": i.titulo,
            "ano": i.data_documento[:4],
            "modelo": i.modelo,
            "tipo": i.tipo,
            "documento": i.documento,
            "objetivo": i.objetivo,
        }
        for i in improvements()
    ]


@router.get("/impact/{improvement_id}")
def evaluate_improvement(improvement_id: str) -> dict:
    """Antes × depois de uma melhoria, com estatística e veredito."""
    item = next((i for i in improvements() if i.id == improvement_id), None)
    if item is None:
        raise HTTPException(404, "Melhoria não encontrada.")
    result = impact_core.evaluate(state.df, item)
    table = result.tabela.reset_index()
    table = table.rename(columns={table.columns[0]: "grupo"})
    return {
        "evidencia": evidence_origin(item),
        "melhoria": {
            "id": item.id,
            "codigo": item.codigo,
            "titulo": item.titulo,
            "documento": item.documento,
            "objetivo": item.objetivo,
            "tipo": item.tipo,
        },
        "indicador": result.indicador,
        "tabela": df_json(table),
        "p_valor": as_number(result.p_valor),
        "reducao_relativa": as_number(result.reducao_relativa),
        "veredito": verdict(result),
        "serie_temporal": df_json(result.serie_temporal),
        "notas": result.notas,
    }


class ImprovementIn(BaseModel):
    """Corpo do cadastro de uma nova melhoria."""

    titulo: str = Field(min_length=3, max_length=120)
    modelo: Literal["Passione", "Luna"]
    tipo: Literal["corte_serie", "retrofit_campo"]
    serie_inicial: str | None = None
    sintoma_alvo: str = config.LEAK_SYMPTOM
    data_documento: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    documento: str = Field(default="Cadastro via API", max_length=160)
    pecas: list[str] = Field(default_factory=list, max_length=30)
    termos_evidencia: list[str] = Field(default_factory=list, max_length=8)


@router.post("/improvements", status_code=201)
def register_improvement(body: ImprovementIn) -> dict:
    """O P&D cadastra uma melhoria e a próxima análise já a mede."""
    start = parse_serial(body.serie_inicial) if body.serie_inicial else None
    if body.tipo == "corte_serie" and (start is None or not start.valida):
        raise HTTPException(
            422, "Para mudança de fábrica, informe uma série inicial válida."
        )
    items = improvements()
    code = boletim.make_code(body.modelo, body.tipo,
                             [i.codigo for i in items])
    terms = body.termos_evidencia or boletim.suggest_terms(body.titulo)
    new = impact_core.Improvement(
        id=f"{body.modelo[:2].upper()}-{len(items) + 1:03d}",
        titulo=body.titulo,
        documento=body.documento,
        modelo=body.modelo,
        data_documento=body.data_documento,
        tipo=body.tipo,
        sintoma_alvo=body.sintoma_alvo,
        componentes_alvo=[],
        flag_evidencia="evid_" + code.replace("-", "_").lower(),
        objetivo="—",
        serie_inicial=start.serie if start else None,
        pecas=body.pecas,
        codigo=code,
        termos_evidencia=terms,
    )
    items.append(new)
    impact_core.save_improvements(items, bootstrap.IMPROVEMENTS_PATH)
    return {"id": new.id, "codigo": code, "titulo": new.titulo}
