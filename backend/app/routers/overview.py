"""Visão geral da base."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.common import as_number
from app.privacy import mask_text
from app.serializers import df_json
from app.state import state

router = APIRouter(tags=["visão geral"])

DEFAULT_MODELS = "Passione,Luna"
TOP_SYMPTOMS = 10
TOP_CAUSES = 12


@router.get("/overview")
def overview(modelos: str = DEFAULT_MODELS) -> dict:
    """Retrato da base, filtrável por modelo."""
    chosen = [m for m in modelos.split(",") if m]
    data = state.df[state.df["modelo"].isin(chosen)]
    if data.empty:
        raise HTTPException(404, "Nenhum chamado para os modelos pedidos.")
    monthly = data.groupby(["mes", "modelo"]).size().reset_index(name="n")
    causes = data[data["tem_reparo_registrado"]]["causa_label"]
    return {
        "totais": {
            "chamados": int(len(data)),
            "maquinas": int(data["serie"].nunique()),
            "reincidencia": as_number(data["reincidente"].mean()),
            "sem_registro_tecnico": as_number(
                (~data["tem_reparo_registrado"]).mean()
            ),
        },
        "mensal": df_json(monthly),
        "top_sintomas": _top(data["sintoma_cs"], TOP_SYMPTOMS),
        "top_causas": _top(causes, TOP_CAUSES),
    }


def _top(series, limit: int) -> list[dict]:
    """Os valores mais frequentes com contagem, textos mascarados."""
    return [
        {"nome": mask_text(name), "n": int(count)}
        for name, count in series.value_counts().head(limit).items()
    ]
