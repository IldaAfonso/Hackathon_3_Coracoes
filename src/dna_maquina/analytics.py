"""
Análises transversais: "Duas vozes" e "Radar" de problemas despercebidos.

* **Duas vozes** (Dor 05 / Ponto 1 do mapa): cruza o sintoma relatado
  pelo consumidor com a causa encontrada pelo técnico, mostrando onde as
  histórias batem e onde divergem. Ex.: "Botões piscando" quase sempre é
  um problema hidráulico — informação valiosa para o roteiro do CS.

* **Radar** (Dor 03 / Ponto 2): o P&D "só vê o que procura". O radar
  varre automaticamente todas as combinações modelo × sintoma × causa e
  aponta as que estão crescendo acima do próprio histórico, sem que
  ninguém precise fazer a pergunta.
"""

from __future__ import annotations

import pandas as pd

from dna_maquina.taxonomy import voices_agree


def add_voice_agreement(df: pd.DataFrame) -> pd.DataFrame:
    """Cria ``vozes_concordam`` (True/False/None) chamado a chamado."""
    out = df.copy()
    out["vozes_concordam"] = [
        voices_agree(symptom, comps)
        for symptom, comps in zip(out["sintoma_cs"], out["componentes"])
    ]
    return out


def voices_matrix(df: pd.DataFrame, top_symptoms: int = 10,
                  normalize: bool = True) -> pd.DataFrame:
    """Matriz sintoma (consumidor) × causa principal (técnico).

    Args:
        df: Base enriquecida.
        top_symptoms: Quantos sintomas mais frequentes exibir.
        normalize: Se ``True``, cada linha soma 100 % (lê-se: "dos chamados
            com este sintoma, X % tinham esta causa").

    Returns:
        Tabela pronta para heatmap.
    """
    data = df[df["tem_reparo_registrado"]]
    top = data["sintoma_cs"].value_counts().head(top_symptoms).index
    data = data[data["sintoma_cs"].isin(top)]
    matrix = pd.crosstab(data["sintoma_cs"], data["causa_label"],
                         normalize="index" if normalize else False)
    ordered_cols = matrix.sum().sort_values(ascending=False).index
    return matrix.loc[top, ordered_cols]


def agreement_by_symptom(df: pd.DataFrame) -> pd.DataFrame:
    """% de concordância entre as duas vozes, por sintoma relatado."""
    data = df[df["vozes_concordam"].notna()]
    table = data.groupby("sintoma_cs").agg(
        chamados=("case_id", "size"),
        concordancia=("vozes_concordam", lambda s: s.astype(bool).mean()),
        sem_defeito=("causa_principal", lambda s: (s == "sem_defeito").mean()),
    )
    return table.sort_values("chamados", ascending=False)


def radar(df: pd.DataFrame, recent_months: int = 3,
          min_cases: int = 15) -> pd.DataFrame:
    """Detecta combinações (modelo, sintoma, causa) em alta recente.

    Método simples e explicável (escore z de Poisson): compara a média
    mensal dos últimos ``recent_months`` meses com a média dos meses
    anteriores. ``z = (recente - base) / sqrt(base / recent_months)``.

    Args:
        df: Base enriquecida.
        recent_months: Tamanho da janela recente.
        min_cases: Mínimo de chamados na janela recente para entrar.

    Returns:
        Combinações ordenadas pelo escore, com médias e variação %.
    """
    data = df[df["mes"].notna()]
    months = sorted(data["mes"].unique())
    if len(months) <= recent_months + 2:
        return pd.DataFrame()
    recent = set(months[-recent_months:])
    n_base = len(months) - recent_months

    keys = ["modelo", "sintoma_cs", "causa_label"]
    data = data.assign(recente=data["mes"].isin(recent))
    grouped = data.groupby(keys + ["recente"]).size().unstack(fill_value=0)
    grouped = grouped.reindex(columns=[False, True], fill_value=0)
    grouped.columns = ["casos_base", "casos_recentes"]

    grouped["media_base"] = grouped["casos_base"] / n_base
    grouped["media_recente"] = grouped["casos_recentes"] / recent_months
    expected = grouped["media_base"].clip(lower=0.5)
    grouped["z"] = ((grouped["media_recente"] - expected)
                    / (expected / recent_months) ** 0.5)
    grouped["variacao_pct"] = (grouped["media_recente"] / expected - 1) * 100
    grouped = grouped[grouped["casos_recentes"] >= min_cases]
    return grouped.sort_values("z", ascending=False).reset_index()


def chronic_cohorts(df: pd.DataFrame, min_cases: int = 100) -> pd.DataFrame:
    """Coortes de fabricação (modelo, ano, semana) com mix anômalo.

    Útil para achar um "lote ruim" de fábrica: semanas de produção cujo
    percentual de um sintoma está muito acima da média do modelo.
    """
    data = df[df["valida"]].copy()
    data["coorte"] = (data["ano_fab"].astype(int).astype(str) + "-S"
                      + data["semana_fab"].astype(int).map("{:02d}".format))
    rows = []
    for model, part in data.groupby("modelo_serie"):
        overall = part["sintoma_cs"].value_counts(normalize=True)
        for cohort, chunk in part.groupby("coorte"):
            if len(chunk) < min_cases:
                continue
            counts = chunk["sintoma_cs"].value_counts()
            share = counts / counts.sum()
            # Exige ao menos 10 casos do sintoma: evita "lift" de raridades.
            lift = (share / overall).dropna()[counts >= 10]
            if lift.empty:
                continue
            symptom = lift.idxmax()
            rows.append({"modelo": model, "coorte": cohort,
                         "chamados": len(chunk), "sintoma": symptom,
                         "participacao": share[symptom],
                         "media_modelo": overall[symptom],
                         "lift": lift[symptom]})
    return pd.DataFrame(rows).sort_values("lift", ascending=False)
