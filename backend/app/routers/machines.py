"""DNA da máquina: a linha do tempo de uma série.

É a tela que o técnico consulta antes de sair e o CS durante a ligação:
a história inteira da máquina, de quem ouviu a quem resolveu.
"""

from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.common import improvements
from app.privacy import mask_frame, mask_text
from app.serializers import df_json
from app.settings import TEXT_COLUMNS
from app.state import state
from dna_maquina import history, llm, reliability
from dna_maquina.serial import parse_serial, serial_order_key

router = APIRouter(tags=["máquinas"])
logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 12
SUMMARY_COLUMNS = ("serie", "modelo", "chamados", "reincidencias", "cronica")
CHRONIC_COLUMNS = (
    "serie",
    "modelo",
    "chamados",
    "reincidencias",
    "vazamentos",
)


def _pick(df: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    """Seleciona só as colunas que existem na base."""
    return df[[c for c in columns if c in df.columns]]


@router.get("/machines/search")
def search_machines(q: str = "", limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Busca por prefixo da série (aceita minúsculas e espaços)."""
    summary = state.summary()
    key = "".join(ch for ch in q.upper() if ch.isalnum())
    if key:
        found = summary[summary.index.str.startswith(key)]
        found = found.sort_values("chamados", ascending=False)
    else:
        found = summary.sort_values(
            ["reincidencias", "chamados"], ascending=False
        )
    found = found.head(limit).reset_index(names="serie")
    return df_json(_pick(found, SUMMARY_COLUMNS))


@router.get("/machines/chronic")
def chronic_machines(limit: int = 10) -> dict:
    """Máquinas crônicas (3 ou mais chamados), as mais reincidentes."""
    summary = state.summary()
    chronic = summary[summary["cronica"]]
    top = chronic.sort_values(
        ["reincidencias", "chamados"], ascending=False
    ).head(limit)
    top = top.reset_index(names="serie")
    return {
        "total": int(len(chronic)),
        "maquinas": df_json(_pick(top, CHRONIC_COLUMNS)),
    }


def _improvement_status(serie: str, df: pd.DataFrame) -> list[dict]:
    """Quais melhorias a máquina 'nasceu' com ou recebeu em campo."""
    key = serial_order_key(serie)
    model = df.loc[df["serie"] == serie, "modelo_serie"].iat[0]
    out = []
    for item in improvements():
        if item.modelo != model:
            continue
        if item.tipo == "corte_serie":
            cutoff = serial_order_key(item.serie_inicial or "")
            has_it = key is not None and cutoff is not None and key >= cutoff
            status = "de_fabrica" if has_it else "antes_da_melhoria"
            text = "de fábrica" if has_it else "fabricada ANTES da melhoria"
        else:
            applied = bool(
                df.loc[df["serie"] == serie, item.flag_evidencia].any()
            )
            status = "aplicada_em_campo" if applied else "sem_registro"
            text = (
                "aplicada em campo" if applied else "sem registro de aplicação"
            )
        out.append(
            {
                "id": item.id,
                "titulo": item.titulo,
                "tipo": item.tipo,
                "status": status,
                "texto": text,
            }
        )
    return out


def _ml_layer(df: pd.DataFrame, serie: str) -> dict:
    """Causa provável e risco de retorno, ou aviso de indisponível.

    A ficha continua útil sem a camada de ML; por isso a falha é
    registrada no log e devolvida de forma explícita, não escondida.
    """
    rows = df[df["serie"] == serie]
    missing = rows[~rows["tem_reparo_registrado"]]
    layer: dict = {
        "disponivel": True,
        "causas_provaveis": [],
        "risco_ultimo_chamado": None,
        "acerto_top3": None,
    }
    try:
        if len(missing):
            guesses = state.probable_causes().loc[missing.index]
            layer["causas_provaveis"] = df_json(
                pd.DataFrame(
                    {
                        "abertura": missing["data_abertura"],
                        "consumidor": missing["sintoma_cs"].map(mask_text),
                        "causa_provavel": guesses["causa_provavel_ia"],
                    }
                )
            )
            layer["acerto_top3"] = float(state.cause_model()[1]["acerto_top3"])
        last = rows.sort_values("data_abertura").index[-1]
        scores = state.risk_scores()
        if last in scores.index:
            layer["risco_ultimo_chamado"] = float(scores[last])
    except Exception as error:  # noqa: BLE001
        logger.exception("camada de ML indisponível para %s", serie)
        return {
            "disponivel": False,
            "motivo": type(error).__name__,
            "causas_provaveis": [],
            "risco_ultimo_chamado": None,
            "acerto_top3": None,
        }
    return layer


def _events(timeline: pd.DataFrame) -> list[dict]:
    """Linha do tempo com as vozes do consumidor e do técnico."""
    masked = mask_frame(timeline, list(TEXT_COLUMNS)).assign(
        data_abertura=timeline["data_abertura"].dt.strftime("%Y-%m-%d")
    )
    events = []
    for row in df_json(masked):
        agree = row.get("vozes_concordam")
        events.append(
            {
                "data": row["data_abertura"],
                "caso": row.get("case_id"),
                "consumidor": row.get("sintoma_cs"),
                "tecnico": {
                    "laudo": row.get("laudo"),
                    "motivo": row.get("motivo"),
                    "causa": row.get("causa_label"),
                    "conclusao": row.get("conclusao"),
                },
                "dias_desde_anterior": row.get("dias_desde_anterior"),
                "voltou_em_90_dias": bool(row.get("reincidente")),
                "vozes_concordam": None if agree is None else bool(agree),
                "adaptacao_hidraulica": bool(
                    row.get("fez_adaptacao_hidraulica")
                ),
            }
        )
    return events


@router.get("/machines/{serie}")
def machine(serie: str) -> dict:
    """DNA de uma máquina: ficha, melhorias, confiança e história."""
    df = state.df
    timeline = history.machine_timeline(df, serie)
    if timeline.empty:
        raise HTTPException(404, "Série não encontrada na base.")
    info = parse_serial(serie)
    row = state.summary().loc[info.serie]
    # O prompt do LLM leva texto de técnico: só a base mascarada vai.
    summary = llm.summarize(state.masked(), info.serie, improvements())
    score = state.machine_confidence().get(info.serie)
    return {
        "ficha": {
            "serie": info.serie,
            "modelo": row["modelo"],
            "ano_fabricacao": int(row["ano_fab"]),
            "semana_fabricacao": int(row["semana_fab"]),
            "chamados": int(row["chamados"]),
            "voltas_em_90_dias": int(row["reincidencias"]),
            "recebeu_adaptacao_hidraulica": bool(row["recebeu_adaptacao"]),
            "cronica": bool(row["cronica"]),
        },
        "melhorias": _improvement_status(info.serie, df),
        "resumo": {"texto": mask_text(summary.texto), "fonte": summary.fonte},
        "confiabilidade": None
        if score is None
        else {
            "nota": float(score),
            "rotulo": reliability.confidence_label(score),
        },
        "ia": _ml_layer(df, info.serie),
        "linha_do_tempo": _events(timeline),
    }
