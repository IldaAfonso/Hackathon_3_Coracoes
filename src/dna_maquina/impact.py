"""
Melhoria × Impacto: a pergunta "funcionou?" respondida com dados.

Responde à Dor 04 (não existe correlação entre melhoria e impacto) e à
persona Marina (engenheira de produto), que precisa levar à engenharia a
prova de que uma mudança de engenharia reduziu as ocorrências em campo.

Dois tipos de melhoria exigem dois desenhos de análise diferentes
-----------------------------------------------------------------
1. **Corte de série** (``tipo = "corte_serie"``) — mudança de projeto na
   fábrica a partir de um número de série (ex.: bandeja de cápsulas).
   A base de chamados é de 2025–2026, ou seja, POSTERIOR à melhoria de 2022;
   comparar "antes e depois" pelo calendário não faz sentido. Por isso a
   comparação é por **coorte de fabricação**: máquinas fabricadas antes do
   corte × depois do corte, observadas no MESMO período de calendário.
   Isso controla sazonalidade e mudanças de processo de atendimento.

2. **Retrofit de campo** (``tipo = "retrofit_campo"``) — kit aplicado pelo
   técnico em qualquer série (ex.: adaptação hidráulica, O-ring).
   Aqui a pergunta é: **depois do reparo com o kit, o problema voltou?**
   Compara-se a taxa de retorno em 90 dias de atendimentos de vazamento
   COM o kit × SEM o kit. Atendimentos nos últimos 90 dias da base são
   excluídos (censura à direita: ainda não deu tempo de voltar).

Limitação central (e honesta): a extração contém só máquinas que tiveram
chamado. Sem a base instalada (quantas máquinas foram vendidas por coorte)
não dá para calcular a taxa de falha absoluta. Os indicadores usados são
de MIX (participação do sintoma nos chamados da coorte) e de
REINCIDÊNCIA — ambos independem do denominador da base instalada. Com a
base instalada na POC, o mesmo código calcula falhas por 1.000 máquinas.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from dna_maquina import config
from dna_maquina.serial import serial_order_key


@dataclass
class Improvement:
    """Uma melhoria de engenharia registrada no catálogo (melhorias.json).

    Attributes espelham o JSON; ``serie_inicial`` só existe em melhorias
    do tipo ``corte_serie``.
    """

    id: str
    titulo: str
    documento: str
    modelo: str
    data_documento: str
    tipo: str
    sintoma_alvo: str
    componentes_alvo: list[str]
    flag_evidencia: str
    objetivo: str
    serie_inicial: str | None = None
    pecas: list[str] = field(default_factory=list)
    codigo: str | None = None
    termos_evidencia: list[str] = field(default_factory=list)


def load_improvements(path: Path = config.IMPROVEMENTS_FILE
                      ) -> list[Improvement]:
    """Lê o catálogo de melhorias (diretório de melhorias do P&D)."""
    with open(path, encoding="utf-8") as handle:
        return [Improvement(**item) for item in json.load(handle)]


def save_improvements(items: list[Improvement],
                      path: Path = config.IMPROVEMENTS_FILE) -> None:
    """Grava o catálogo — usado pelo formulário "Registrar melhoria"."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump([i.__dict__ for i in items], handle, ensure_ascii=False,
                  indent=2)


# ---------------------------------------------------------------------------
# Estatística (implementada com a biblioteca padrão, sem SciPy)
# ---------------------------------------------------------------------------
def wilson_interval(successes: int, total: int,
                    z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de Wilson (95 %) para uma proporção.

    Preferido ao intervalo normal simples porque se comporta bem com
    amostras pequenas e proporções próximas de 0 — o caso de várias coortes.
    """
    if total == 0:
        return (math.nan, math.nan)
    p = successes / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (center - half, center + half)


def two_proportion_test(x1: int, n1: int, x2: int, n2: int) -> float:
    """Teste z bicaudal de diferença entre duas proporções; retorna o p-valor.

    Interpretação para o P&D: p < 0,05 => a diferença entre "antes"
    e "depois" dificilmente é obra do acaso.
    """
    if min(n1, n2) == 0:
        return math.nan
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return math.nan
    z = (x1 / n1 - x2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


@dataclass
class CohortResult:
    """Resultado comparativo entre o grupo "antes" e o grupo "depois"."""

    melhoria: Improvement
    tabela: pd.DataFrame          # uma linha por grupo (antes/depois)
    serie_temporal: pd.DataFrame  # indicador por coorte (semana) ou mês
    p_valor: float
    reducao_relativa: float       # (antes - depois) / antes
    indicador: str                # nome legível do indicador principal
    notas: list[str]


def _summarize_group(group: pd.DataFrame, flag: str) -> dict[str, float]:
    """Calcula os indicadores de um grupo (coorte ou conjunto de reparos)."""
    n = len(group)
    hits = int(group[flag].sum())
    low, high = wilson_interval(hits, n)
    return {"n": n, "eventos": hits, "taxa": hits / n if n else math.nan,
            "ic_inf": low, "ic_sup": high}


def _compare_groups(control: pd.Series,
                    treated: pd.Series) -> tuple[float, float]:
    """Compara dois grupos: devolve (p-valor, redução relativa).

    Se um dos grupos está vazio (por exemplo, uma base importada sem
    chamados de uma das coortes), não existe comparação possível. Em vez
    de quebrar a tela, devolve NaN: o veredito vira "Amostra
    insuficiente", que é a resposta honesta.

    Args:
        control: Linha do grupo de referência (antes / sem kit).
        treated: Linha do grupo tratado (depois / com kit).

    Returns:
        ``(p_valor, reducao_relativa)``; ambos NaN se faltar grupo.
    """
    if not control["n"] or not treated["n"]:  # 0 ou NaN
        return math.nan, math.nan
    p_value = two_proportion_test(
        int(control["eventos"]), int(control["n"]),
        int(treated["eventos"]), int(treated["n"]))
    reduction = ((control["taxa"] - treated["taxa"]) / control["taxa"]
                 if control["taxa"] else math.nan)
    return p_value, reduction


def serial_cutoff_impact(df: pd.DataFrame, item: Improvement,
                         window_weeks: int = 52) -> CohortResult:
    """Antes × depois por coorte de fabricação (melhoria de corte de série).

    Indicador principal: participação do sintoma-alvo (ex.: vazamento) no
    total de chamados da coorte. Comparação restrita a ``window_weeks``
    semanas de fabricação antes e depois do corte, para que as coortes
    tenham idades parecidas.

    Args:
        df: Base enriquecida.
        item: Melhoria do tipo ``corte_serie``.
        window_weeks: Largura da janela de fabricação em cada lado.

    Returns:
        :class:`CohortResult` com tabela, série temporal e p-valor.
    """
    cutoff = serial_order_key(item.serie_inicial or "")
    if cutoff is None:
        raise ValueError(f"Série de corte inválida: {item.serie_inicial}")

    base = df[(df["modelo_serie"] == item.modelo) & df["valida"]].copy()
    base["alvo"] = base["sintoma_cs"].eq(item.sintoma_alvo)
    base["fab"] = pd.to_datetime(
        base["ano_fab"].astype(int).astype(str)
        + base["semana_fab"].astype(int).map("{:02d}".format) + "1",
        format="%G%V%u", errors="coerce",
    )
    cut_year, cut_week = divmod(cutoff // 100_000, 100)
    cut_date = pd.to_datetime(f"{cut_year}{cut_week:02d}1", format="%G%V%u")
    window = pd.Timedelta(weeks=window_weeks)
    base = base[(base["fab"] >= cut_date - window)
                & (base["fab"] < cut_date + window)]
    base["grupo"] = (base["chave_ordem"] >= cutoff).map(
        {False: "Antes", True: "Depois"})

    rows = {g: _summarize_group(part, "alvo")
            for g, part in base.groupby("grupo")}
    table = pd.DataFrame(rows).T.reindex(["Antes", "Depois"])
    table["maquinas"] = base.groupby("grupo")["serie"].nunique()
    table = table.fillna({"n": 0, "eventos": 0, "maquinas": 0})
    p_value, reduction = _compare_groups(table.loc["Antes"],
                                         table.loc["Depois"])

    # Série por SEMANA de fabricação (a produção vem em lotes semanais).
    # Semanas com menos de 50 chamados são omitidas do gráfico (ruído).
    weekly = (base.assign(coorte=base["ano_fab"].astype(int).astype(str)
                          + "-S" + base["semana_fab"].astype(int)
                          .map("{:02d}".format))
              .groupby(["fab", "coorte"])
              .agg(n=("alvo", "size"), eventos=("alvo", "sum"),
                   depois=("grupo", lambda g: (g == "Depois").mean() > 0.5)))
    weekly = weekly[weekly["n"] >= 50]
    weekly["taxa"] = weekly["eventos"] / weekly["n"]
    monthly = weekly

    notes = [
        f"Coortes fabricadas até {window_weeks} semanas antes e depois "
        f"do corte {item.serie_inicial} ({cut_year}, semana {cut_week}).",
        "Todas observadas no mesmo período (chamados de 2025–2026).",
        "Indicador de mix: não depende da base instalada; a coorte 'Antes' "
        "é mais velha, o que tende a SUBESTIMAR o ganho se o desgaste "
        "aumenta com a idade.",
    ]
    return CohortResult(item, table, monthly.reset_index(), p_value,
                        reduction, f"% de chamados '{item.sintoma_alvo}'",
                        notes)


def with_evidence(df: pd.DataFrame, item: Improvement) -> pd.DataFrame:
    """Garante a coluna de evidência da melhoria (sem alterar ``df``).

    Ordem: coluna já existente; ``codigo_melhoria`` registrado no chamado
    (evidência exata, só se algum chamado já traz o código da melhoria);
    senão, termos no texto livre (evidência inferida).
    """
    registered = (df["codigo_melhoria"].eq(item.codigo).fillna(False)
                  if item.codigo and "codigo_melhoria" in df.columns
                  else None)
    if registered is not None and registered.any():
        out = df.copy()
        out[item.flag_evidencia] = registered.astype(bool)
        return out
    if item.flag_evidencia in df.columns:
        return df
    out = df.copy()
    out[item.flag_evidencia] = text_mentions(out, item.termos_evidencia)
    return out


def text_mentions(df: pd.DataFrame, terms: list[str]) -> pd.Series:
    """Chamados cuja conclusão cita algum termo (sem acento, sem caixa)."""
    from dna_maquina.taxonomy import strip_accents

    terms = [strip_accents(t).lower() for t in terms if t.strip()]
    if not terms or "conclusao" not in df.columns:
        return pd.Series(False, index=df.index)
    folded = df["conclusao"].fillna("").map(
        lambda text: strip_accents(text).lower())
    mask = pd.Series(False, index=df.index)
    for term in terms:
        mask |= folded.str.contains(term, regex=False)
    return mask


def retrofit_impact(df: pd.DataFrame, item: Improvement,
                    window_days: int = config.REINCIDENCE_WINDOW_DAYS
                    ) -> CohortResult:
    """Efetividade de um kit de campo: o problema voltou depois do reparo?

    Universo: atendimentos do modelo com sintoma-alvo e reparo registrado,
    abertos até ``window_days`` antes da última data da base (censura).
    Grupo "Com kit" = conclusão cita a flag de evidência da melhoria.

    Indicador principal: % de atendimentos seguidos de NOVO chamado da
    mesma máquina em até ``window_days`` dias (quanto menor, melhor).
    """
    last_date = df["data_abertura"].max()
    df = with_evidence(df, item)
    base = df[(df["modelo"] == item.modelo)
              & df["sintoma_cs"].eq(item.sintoma_alvo)
              & df["tem_reparo_registrado"]
              & df["valida"]
              & (df["data_abertura"] <= last_date
                 - pd.Timedelta(days=window_days))].copy()
    base["voltou"] = base["problema_voltou"].fillna(False).astype(bool)
    base["grupo"] = base[item.flag_evidencia].map(
        {False: "Sem kit", True: "Com kit"})

    rows = {g: _summarize_group(part, "voltou")
            for g, part in base.groupby("grupo")}
    table = pd.DataFrame(rows).T.reindex(["Sem kit", "Com kit"])
    table["maquinas"] = base.groupby("grupo")["serie"].nunique()
    table = table.fillna({"n": 0, "eventos": 0, "maquinas": 0})
    p_value, reduction = _compare_groups(table.loc["Sem kit"],
                                         table.loc["Com kit"])

    adoption = (df[(df["modelo"] == item.modelo)
                   & df["sintoma_cs"].eq(item.sintoma_alvo)
                   & df["tem_reparo_registrado"]]
                .groupby("mes")
                .agg(n=(item.flag_evidencia, "size"),
                     eventos=(item.flag_evidencia, "sum")))
    adoption["taxa"] = adoption["eventos"] / adoption["n"]

    censor_date = (last_date - pd.Timedelta(days=window_days)).date()
    notes = [
        f"Atendimentos de '{item.sintoma_alvo}' com reparo registrado; "
        f"retorno = novo chamado da mesma série em até {window_days} dias.",
        f"Excluídos chamados após {censor_date} "
        "(ainda sem tempo de observar retorno).",
        "Gráfico mostra a ADOÇÃO do kit: % dos reparos de vazamento que "
        "citam o kit, mês a mês. Kit citado só no texto livre pode ser "
        "subnotificado.",
    ]
    return CohortResult(item, table, adoption.reset_index(), p_value,
                        reduction,
                        f"% de reparos com retorno em {window_days} dias",
                        notes)


def evaluate(df: pd.DataFrame, item: Improvement) -> CohortResult:
    """Escolhe o desenho de análise adequado ao tipo da melhoria."""
    if item.tipo == "corte_serie":
        return serial_cutoff_impact(df, item)
    return retrofit_impact(df, item)
