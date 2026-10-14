"""A narrativa do produto, calculada na base real.

O número de série é a chave que liga os três times que cuidam da mesma
máquina: Customer Success (ouve), Pós-vendas (resolve) e P&D (inova).
Hoje cada um registra num lugar e ninguém enxerga a história inteira.
"""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

from app.common import improvements
from app.content import IMPROVEMENTS_TO_DEPLOY
from app.privacy import mask_text
from app.state import state
from dna_maquina import config, patterns

router = APIRouter(tags=["narrativa"])

CHRONIC_MIN_CASES = 3
REPEAT_MIN_CASES = 2
TOP_EXAMPLES = 3


def _symptom(
    sid: str, title: str, value, unit: str, team: str, reading: str
) -> dict:
    """Um sintoma do histórico atual: quem sente e o que significa."""
    return {
        "id": sid,
        "titulo": title,
        "valor": value,
        "unidade": unit,
        "time": team,
        "leitura": reading,
    }


def _chamados_com_pecas(df: pd.DataFrame) -> int:
    """Chamados cuja conclusão cita algum código de peça do catálogo."""
    codes = {
        part.split(" - ")[0].strip()
        for item in improvements()
        for part in item.pecas
    }
    if not codes or "conclusao" not in df:
        return 0
    text = df["conclusao"].fillna("")
    mask = pd.Series(False, index=df.index)
    for code in codes:
        mask |= text.str.contains(code, regex=False)
    return int(mask.sum())


def _symptoms(df: pd.DataFrame) -> list[dict]:
    """Evidências de que o histórico de hoje não atende."""
    # Contagens POR MÁQUINA usam só séries válidas: um agrupamento de
    # séries ilegíveis não é uma máquina e inflaria os números.
    valid = df[~df["dq_serie_invalida"]]
    per_machine = valid.groupby("serie").size()
    window = config.REINCIDENCE_WINDOW_DAYS
    agree = df["vozes_concordam"].dropna()
    mentions = patterns.bulletin_mentions(df)
    repeat_share = per_machine[per_machine >= REPEAT_MIN_CASES].sum()
    return [
        _symptom(
            "sem_conclusao",
            "Chamados sem conclusão do técnico",
            float((~df["tem_reparo_registrado"]).mean()),
            "%",
            "Pós-vendas",
            "O CS registra o problema, mas a resposta do Pós-vendas não "
            "volta para a base: a história fica pela metade.",
        ),
        _symptom(
            "reincidencia",
            f"Chamados que são a mesma máquina voltando em até {window} dias",
            float(df["reincidente"].mean()),
            "%",
            "CS + Pós-vendas",
            "Quem atende não vê o que já foi feito nessa máquina, "
            "então o problema volta.",
        ),
        _symptom(
            "concentracao",
            "Chamados de máquinas com 2 ou mais chamados",
            float(repeat_share / len(valid)),
            "%",
            "P&D",
            "Boa parte da carga vem de máquinas que já apareceram antes: "
            "problema crônico, invisível sem histórico por série.",
        ),
        _symptom(
            "cronicas",
            "Máquinas com 3 ou mais chamados no período",
            int((per_machine >= CHRONIC_MIN_CASES).sum()),
            "máquinas",
            "P&D",
            "Candidatas a análise de causa-raiz; hoje ninguém tem "
            "essa lista pronta.",
        ),
        _symptom(
            "vozes",
            "Chamados em que consumidor e técnico contam a mesma história",
            float(agree.mean()) if len(agree) else None,
            "%",
            "CS × Pós-vendas",
            "Quando as duas vozes divergem, quem analisa "
            "não sabe em qual confiar.",
        ),
        _symptom(
            "serie_invalida",
            "Chamados com série inválida ou ilegível",
            float(df["dq_serie_invalida"].mean()),
            "%",
            "CS",
            "Sem série não há como ligar o chamado à fábrica nem à versão "
            "da máquina. A chave precisa ser validada na entrada.",
        ),
        _symptom(
            "antes_instalacao",
            "Chamados abertos antes da instalação",
            int(df["dq_abertura_antes_instalacao"].sum()),
            "chamados",
            "CS",
            "Datas incoerentes quebram a linha do tempo da máquina.",
        ),
        _symptom(
            "pecas_citadas",
            "Chamados que citam o código de peça de um boletim cadastrado",
            _chamados_com_pecas(df),
            "chamados",
            "Pós-vendas",
            "O código da peça quase nunca é registrado: o efeito do "
            "boletim só pode ser inferido por palavras.",
        ),
        _symptom(
            "boletins",
            "Boletins citados em campo e fora do diretório de melhorias",
            int(len(mentions)),
            "boletins",
            "P&D",
            "Melhorias aplicadas que o P&D não consegue medir porque não "
            "estão cadastradas.",
        ),
    ]


@router.get("/diagnostico")
def diagnostic() -> dict:
    """O histórico de hoje não atende: os números e o que implantar."""
    df = state.df
    no_report = df.loc[~df["tem_reparo_registrado"], "sintoma_cs"]
    return {
        "base": {
            "chamados": int(len(df)),
            "maquinas": int(df["serie"].nunique()),
        },
        "sintomas": _symptoms(df),
        "sintomas_sem_laudo": [
            {"sintoma": mask_text(name), "chamados": int(count)}
            for name, count in no_report.value_counts().head(3).items()
        ],
        "melhorias_a_implantar": list(IMPROVEMENTS_TO_DEPLOY),
    }


def _examples(series: pd.Series) -> list[str]:
    """Os valores mais frequentes de um campo de texto, mascarados."""
    return [
        mask_text(v) for v in series.value_counts().head(TOP_EXAMPLES).index
    ]


@router.get("/times")
def teams() -> dict:
    """O que cada time registra, ligado à mesma série."""
    df = state.df
    catalog = improvements()
    recorded = df[df["tem_reparo_registrado"]]
    valid_rows = df[~df["dq_serie_invalida"]]
    machines = valid_rows["serie"].nunique()
    technical = valid_rows.loc[
        valid_rows["tem_reparo_registrado"], "serie"
    ].nunique()
    return {
        "chave": "número de série",
        "times": [
            {
                "id": "cs",
                "nome": "Customer Success",
                "papel": "Ouve",
                "registra": "o sintoma, com as palavras do consumidor",
                "registros": int(len(df)),
                "campo": "Detalhamento CS",
                "exemplos": _examples(df["sintoma_cs"]),
                "recebe_hoje": "nada: não sabe se já teve o problema",
            },
            {
                "id": "pos",
                "nome": "Pós-vendas",
                "papel": "Resolve",
                "registra": "o que encontrou e o que fez",
                "registros": int(len(recorded)),
                "campo": "Laudo, motivo e conclusão técnica",
                "exemplos": _examples(recorded["causa_label"]),
                "recebe_hoje": "nada: chega sem saber o que já foi feito",
            },
            {
                "id": "pd",
                "nome": "P&D TRES",
                "papel": "Inova",
                "registra": "o que mudou na máquina e quando",
                "registros": len(catalog),
                "campo": "Diretório de melhorias (série de corte ou kit)",
                "exemplos": [i.titulo for i in catalog[:TOP_EXAMPLES]],
                "recebe_hoje": "nada: não sabe se a melhoria funcionou",
            },
        ],
        "ligacao": {
            "maquinas_com_chamado": int(machines),
            "com_registro_tecnico": int(technical),
            "pct_chamados_serie_valida": float(
                1 - df["dq_serie_invalida"].mean()
            ),
            "pct_com_registro_tecnico": float(technical / machines),
        },
    }
