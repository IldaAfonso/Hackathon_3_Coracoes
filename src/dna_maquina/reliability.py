"""
Histórico CONFIÁVEL: IA para medir e melhorar a confiabilidade do DNA.

A pergunta do desafio pede um histórico "confiável". Este módulo ataca as
três fontes de não-confiabilidade encontradas na base real:

1. **Séries ilegíveis (3%)** — :func:`recover_cohort` tenta reconstruir a
   série com UMA correção de digitação (dígito a mais, a menos ou trocado)
   e só aceita o resultado se ele for plausível (mesmo modelo informado e
   fabricação até 2 anos antes da instalação) e ÚNICO em ano/semana. O
   resultado é uma COORTE recuperada (ano e semana), marcada como tal —
   nunca uma série "inventada".
2. **Chamados sem laudo (21%)** — :func:`train_cause_model` treina um
   classificador (gradient boosting) que, a partir do sintoma, do modelo,
   da idade e da causa anterior da máquina, sugere as 3 causas mais
   prováveis. Exibido sempre como "causa provável (IA)", com probabilidade
   e acurácia medida em teste temporal — dado inferido não se mistura com
   dado registrado.
3. **Ninguém mede a confiabilidade** — :func:`record_confidence` dá a cada
   chamado uma nota de 0 a 100 com pesos explícitos, e
   :func:`machine_confidence` agrega por máquina. A nota acompanha o DNA
   na tela: o usuário sabe quanto pode confiar naquele histórico.
"""

from __future__ import annotations

import json
import string
from dataclasses import asdict, dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from dna_maquina import config
from dna_maquina.serial import parse_serial
from dna_maquina.taxonomy import COMPONENT_LABELS

CAUSE_MODEL_FILE = config.PROJECT_ROOT / "models" / "causa_provavel.joblib"
CAUSE_METRICS_FILE = config.PROJECT_ROOT / "models" / "metricas_causa.json"
TEST_START = pd.Timestamp("2026-01-01")
MAX_PRODUCTION_LAG_YEARS = 2
"""Máquina instalada até 2 anos depois de fabricada (observado na base)."""

# Pesos da nota de confiabilidade (somam 100). Explícitos e auditáveis.
CONFIDENCE_WEIGHTS: dict[str, int] = {
    "serie_valida": 30,
    "tem_registro_tecnico": 30,
    "datas_coerentes": 15,
    "vozes_concordam": 15,
    "instalacao_plausivel": 10,
}

CAUSE_CATEGORICAL = ["sintoma_cs", "modelo", "tensao", "causa_anterior",
                     "atendimento", "formato"]
CAUSE_NUMERIC = ["ano_fab", "idade_dias", "ordem_na_maquina",
                 "dias_desde_anterior"]


# ---------------------------------------------------------------------------
# 1. Recuperação de coorte para séries ilegíveis
# ---------------------------------------------------------------------------
def _one_edit_candidates(serial: str) -> set[str]:
    """Todas as séries a UMA edição de distância (apagar, trocar, inserir
    um dígito) + correção do prefixo "GALN" → "G4LN"."""
    candidates = {serial.replace("GALN", "G4LN", 1)}
    for i in range(len(serial) + 1):
        if i < len(serial):
            candidates.add(serial[:i] + serial[i + 1:])
        for digit in string.digits:
            candidates.add(serial[:i] + digit + serial[i:])
            if i < len(serial):
                candidates.add(serial[:i] + digit + serial[i + 1:])
    return candidates


def recover_cohort(serial: str, install_date: pd.Timestamp,
                   model: str) -> tuple[int, int] | None:
    """Recupera (ano, semana) de fabricação de uma série ilegível.

    Args:
        serial: Série normalizada que não passou na validação.
        install_date: Data de instalação informada no chamado.
        model: Modelo informado (Passione/Luna).

    Returns:
        ``(ano, semana)`` quando existe exatamente UMA coorte plausível;
        ``None`` quando nenhuma ou várias são plausíveis (ambíguo = não
        recupera — preferimos não saber a errar).
    """
    if pd.isna(install_date) or not serial:
        return None
    cohorts = set()
    for candidate in _one_edit_candidates(serial):
        info = parse_serial(candidate)
        lag = install_date.year - (info.ano_fab or 0)
        if (info.valida and info.modelo_serie == model
                and 0 <= lag <= MAX_PRODUCTION_LAG_YEARS):
            cohorts.add((info.ano_fab, info.semana_fab))
    return cohorts.pop() if len(cohorts) == 1 else None


def add_recovered_cohorts(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona ``ano_fab_rec``/``semana_fab_rec`` às séries inválidas."""
    out = df.copy()
    out["ano_fab_rec"] = np.nan
    out["semana_fab_rec"] = np.nan
    invalid = out[~out["valida"].astype(bool)]
    keys = invalid[["serie", "data_instalacao", "modelo"]].drop_duplicates()
    found = {}
    for serial, install, model in keys.itertuples(index=False):
        cohort = recover_cohort(serial, install, model)
        if cohort:
            found[(serial, install, model)] = cohort
    for idx, row in invalid.iterrows():
        cohort = found.get((row["serie"], row["data_instalacao"],
                            row["modelo"]))
        if cohort:
            out.loc[idx, ["ano_fab_rec", "semana_fab_rec"]] = cohort
    out["coorte_recuperada"] = out["ano_fab_rec"].notna()
    return out


# ---------------------------------------------------------------------------
# 2. Causa provável para chamados sem laudo
# ---------------------------------------------------------------------------
@dataclass
class CauseMetrics:
    """Acurácia do modelo de causa provável no teste temporal (2026)."""

    n_treino: int
    n_teste: int
    acerto_top1: float
    acerto_top3: float
    acerto_baseline: float


def _cause_features(df: pd.DataFrame) -> pd.DataFrame:
    """Variáveis disponíveis ANTES de o técnico registrar a causa."""
    ordered = df.sort_values(["serie", "data_abertura"])
    previous = ordered.groupby("serie")["causa_principal"].shift(1)
    previous = previous.where(previous.ne("sem_registro"))
    out = pd.DataFrame(index=df.index)
    out["causa_anterior"] = previous.reindex(df.index).fillna("nenhuma")
    for column in ["sintoma_cs", "modelo", "tensao", "atendimento",
                   "formato"]:
        out[column] = df[column].astype("string").fillna("ausente")
    for column in CAUSE_CATEGORICAL:
        out[column] = out[column].astype("category")
    idade = (df["data_abertura"] - df["data_instalacao"]).dt.days
    out["idade_dias"] = idade.where(idade >= 0)
    for column in ["ano_fab", "ordem_na_maquina", "dias_desde_anterior"]:
        out[column] = df[column]
    return out[CAUSE_CATEGORICAL + CAUSE_NUMERIC]


def _cause_model() -> HistGradientBoostingClassifier:
    """Mesma família do modelo de risco: rápido e lida com categorias."""
    return HistGradientBoostingClassifier(
        categorical_features="from_dtype", max_iter=200,
        learning_rate=0.08, min_samples_leaf=30, random_state=0)


def train_cause_model(df: pd.DataFrame
                      ) -> tuple[HistGradientBoostingClassifier,
                                 CauseMetrics]:
    """Treina com chamados COM causa registrada; testa em 2026.

    Baseline: a causa mais comum para o mesmo sintoma (o que um analista
    chutaria). O modelo final é re-treinado com todos os rotulados.
    """
    labeled = df[df["tem_reparo_registrado"]
                 & ~df["causa_principal"].isin(["outros", "sem_registro"])]
    features = _cause_features(df).loc[labeled.index]
    target = labeled["causa_principal"]
    train = labeled["data_abertura"] < TEST_START

    model = _cause_model().fit(features[train], target[train])
    proba = model.predict_proba(features[~train])
    top3 = model.classes_[np.argsort(-proba, axis=1)[:, :3]]
    truth = target[~train].to_numpy()
    by_symptom = (labeled[train].groupby("sintoma_cs")["causa_principal"]
                  .agg(lambda s: s.value_counts().index[0]))
    guess = labeled.loc[~train, "sintoma_cs"].map(by_symptom)

    metrics = CauseMetrics(
        n_treino=int(train.sum()), n_teste=int((~train).sum()),
        acerto_top1=round(float(np.mean(top3[:, 0] == truth)), 4),
        acerto_top3=round(float(np.mean(
            [t in row for t, row in zip(truth, top3)])), 4),
        acerto_baseline=round(float(np.mean(guess.to_numpy() == truth)), 4))
    final = _cause_model().fit(features, target)
    return final, metrics


def save_cause_model(model, metrics: CauseMetrics) -> None:
    """Persiste o modelo de causa provável e suas métricas."""
    CAUSE_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, CAUSE_MODEL_FILE)
    CAUSE_METRICS_FILE.write_text(json.dumps(asdict(metrics), indent=2),
                                  encoding="utf-8")


def load_cause_model():
    """Carrega (modelo, métricas) ou ``None`` se ainda não treinado."""
    if not (CAUSE_MODEL_FILE.exists() and CAUSE_METRICS_FILE.exists()):
        return None
    return (joblib.load(CAUSE_MODEL_FILE),
            json.loads(CAUSE_METRICS_FILE.read_text(encoding="utf-8")))


def probable_causes(model, df: pd.DataFrame) -> pd.DataFrame:
    """Top-3 causas prováveis para chamados SEM registro técnico.

    Returns:
        DataFrame indexado como ``df`` (só chamados sem registro) com a
        coluna ``causa_provavel_ia``: texto "Causa (62%), Causa (20%), …".
    """
    target = df[~df["tem_reparo_registrado"]]
    if target.empty:
        return pd.DataFrame(columns=["causa_provavel_ia"])
    proba = model.predict_proba(_cause_features(df).loc[target.index])
    order = np.argsort(-proba, axis=1)[:, :3]
    texts = []
    for row_proba, row_order in zip(proba, order):
        names = [COMPONENT_LABELS.get(model.classes_[i], model.classes_[i])
                 for i in row_order]
        parts = [f"{name} ({row_proba[i]:.0%})"
                 for name, i in zip(names, row_order)]
        texts.append(", ".join(parts))
    return pd.DataFrame({"causa_provavel_ia": texts}, index=target.index)


# ---------------------------------------------------------------------------
# 3. Nota de confiabilidade (0–100)
# ---------------------------------------------------------------------------
def record_confidence(df: pd.DataFrame) -> pd.Series:
    """Nota de confiabilidade de cada chamado, com pesos explícitos.

    Critérios (ver :data:`CONFIDENCE_WEIGHTS`): série válida, existe
    registro técnico, datas coerentes (abertura após instalação), as duas
    vozes concordam (ou o sintoma não tem regra) e instalação plausível.
    """
    checks = {
        "serie_valida": df["valida"].astype(bool),
        "tem_registro_tecnico": df["tem_reparo_registrado"].astype(bool),
        "datas_coerentes": ~df["dq_abertura_antes_instalacao"].astype(bool),
        "vozes_concordam": df["vozes_concordam"].map(
            {True: True, False: False}).fillna(True).astype(bool),
        "instalacao_plausivel": ~df["dq_instalacao_suspeita"].astype(bool),
    }
    score = sum(CONFIDENCE_WEIGHTS[k] * v.astype(int)
                for k, v in checks.items())
    return score.rename("confianca")


def machine_confidence(df: pd.DataFrame) -> pd.Series:
    """Nota média de confiabilidade do DNA de cada máquina (séries válidas).
    """
    valid = df[df["valida"].astype(bool)]
    return record_confidence(valid).groupby(valid["serie"]).mean().round(0)


def confidence_label(score: float) -> str:
    """Traduz a nota em linguagem simples para a tela."""
    if score >= 85:
        return "Alta"
    if score >= 65:
        return "Média"
    return "Baixa"
