"""
Modelo de risco de reincidência: "este problema vai voltar?".

Pergunta de negócio
-------------------
Quando um atendimento é encerrado, qual a chance de a MESMA máquina abrir
um novo chamado em até 90 dias? Responder isso na hora permite ao
Pós-vendas/CS priorizar uma ligação de acompanhamento ou uma revisita
ANTES de a consumidora (persona Juliana) ligar de novo.

Desenho do modelo (decisões de ML Engineering)
----------------------------------------------
* **Momento da previsão = encerramento do chamado.** Só entram variáveis
  conhecidas nesse momento (sintoma, laudo, causa, kit, histórico da
  máquina). Nada do futuro entra — evita vazamento de informação.
* **Alvo:** ``problema_voltou`` (novo chamado da mesma série em ≤ 90 dias).
* **Censura à direita:** chamados dos últimos 90 dias da base ficam FORA
  do treino e do teste (ainda não deu tempo de saber se voltaram); são
  justamente os que recebem a previsão no app.
* **Validação temporal (não aleatória):** treina com chamados de 2025 e
  testa com os de 2026 — simula o uso real, em que o modelo prevê o
  futuro a partir do passado.
* **Algoritmo:** ``HistGradientBoostingClassifier`` — lida com categorias
  e valores ausentes nativamente, treina em segundos, sem GPU.
* **Comparação com baseline:** uma regra simples ("chamado sem registro
  técnico") — o modelo só se justifica se for melhor que ela.

Uso pela linha de comando::

    PYTHONPATH=src python -m dna_maquina.risk     # treina, avalia e salva
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score

from dna_maquina import config

MODEL_FILE = config.PROJECT_ROOT / "models" / "risco_retorno.joblib"
METRICS_FILE = config.PROJECT_ROOT / "models" / "metricas_risco.json"

TEST_START = pd.Timestamp("2026-01-01")
"""Início do período de teste: treino = 2025, teste = 2026."""

TOP_SHARE = 0.20
"""Fração de chamados de maior risco usada no indicador de captura."""

RANDOM_STATE = 42

CATEGORICAL = ["modelo", "tensao", "formato", "sintoma_cs", "laudo",
               "causa_principal", "familia_tecnica", "atendimento",
               "vozes_concordam_txt"]
NUMERIC = ["ano_fab", "idade_dias", "ordem_na_maquina",
           "dias_desde_anterior", "tem_reparo_registrado",
           "fez_adaptacao_hidraulica", "trocou_oring_anel"]
FEATURES = CATEGORICAL + NUMERIC

FEATURE_LABELS = {
    "modelo": "Modelo", "tensao": "Tensão", "formato": "Formato da série",
    "sintoma_cs": "Sintoma relatado", "laudo": "Laudo técnico",
    "causa_principal": "Causa encontrada",
    "familia_tecnica": "Família técnica", "atendimento": "Tipo de atendimento",
    "vozes_concordam_txt": "Vozes concordam?", "ano_fab": "Ano de fabricação",
    "idade_dias": "Idade da máquina (dias)",
    "ordem_na_maquina": "Nº do chamado na máquina",
    "dias_desde_anterior": "Dias desde o chamado anterior",
    "tem_reparo_registrado": "Tem registro técnico",
    "fez_adaptacao_hidraulica": "Recebeu adaptação hidráulica",
    "trocou_oring_anel": "Trocou O-ring/anel",
}


@dataclass
class RiskMetrics:
    """Métricas de avaliação no período de teste (2026)."""

    n_treino: int
    n_teste: int
    taxa_retorno_teste: float
    auc_modelo: float
    auc_baseline: float
    ap_modelo: float
    ap_baseline: float
    captura_top20_modelo: float
    captura_top20_baseline: float
    precisao_top10_modelo: float
    auc_so_com_registro: float
    taxa_top20_com_registro: float
    taxa_media_com_registro: float
    importancias: dict[str, float]
    calibracao: list[dict[str, float]]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Monta a matriz de variáveis conhecidas no ENCERRAMENTO do chamado.

    Args:
        df: Base enriquecida pelo pipeline.

    Returns:
        DataFrame só com as colunas de :data:`FEATURES`, com categorias
        tipadas como ``category`` (exigência do gradient boosting nativo).
    """
    out = pd.DataFrame(index=df.index)
    for column in ["modelo", "tensao", "formato", "sintoma_cs",
                   "causa_principal", "familia_tecnica", "atendimento"]:
        out[column] = df[column].astype("string").fillna("ausente")
    out["laudo"] = df["laudo"].astype("string").fillna("Sem laudo")
    out["vozes_concordam_txt"] = df["vozes_concordam"].map(
        {True: "sim", False: "não"}).fillna("não avaliado")

    # Sintomas raros viram "Outros" para o modelo não decorar exceções.
    top = out["sintoma_cs"].value_counts().head(25).index
    out["sintoma_cs"] = out["sintoma_cs"].where(
        out["sintoma_cs"].isin(top), "Outros")

    idade = (df["data_abertura"] - df["data_instalacao"]).dt.days
    out["idade_dias"] = idade.where(~df["dq_instalacao_suspeita"]
                                    & (idade >= 0))
    out["ano_fab"] = df["ano_fab"]
    out["ordem_na_maquina"] = df["ordem_na_maquina"]
    out["dias_desde_anterior"] = df["dias_desde_anterior"]
    for flag in ["tem_reparo_registrado", "fez_adaptacao_hidraulica",
                 "trocou_oring_anel"]:
        out[flag] = df[flag].fillna(False).astype(int)

    for column in CATEGORICAL:
        out[column] = out[column].astype("category")
    return out[FEATURES]


def labeled_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Chamados com desfecho conhecido (fora da janela de censura)."""
    cutoff = df["data_abertura"].max() - pd.Timedelta(
        days=config.REINCIDENCE_WINDOW_DAYS)
    mask = df["valida"].astype(bool) & (df["data_abertura"] <= cutoff)
    out = df[mask].copy()
    out["y"] = out["problema_voltou"].fillna(False).astype(int)
    return out


def _capture(y: np.ndarray, score: np.ndarray, share: float) -> float:
    """% dos retornos reais que estão entre os ``share`` de maior risco.

    É o indicador operacional: "se o CS ligar só para os 20% de maior
    risco, quantos dos problemas que iam voltar ele alcança?".
    """
    order = np.argsort(-score, kind="stable")
    top = order[: int(len(score) * share)]
    return float(y[top].sum() / max(y.sum(), 1))


def _make_model() -> HistGradientBoostingClassifier:
    """Hiperparâmetros conservadores: modelo raso + regularização."""
    return HistGradientBoostingClassifier(
        categorical_features="from_dtype", max_iter=300,
        learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=40,
        l2_regularization=1.0, early_stopping=True,
        validation_fraction=0.15, random_state=RANDOM_STATE)


def train_and_evaluate(df: pd.DataFrame
                       ) -> tuple[HistGradientBoostingClassifier,
                                  RiskMetrics]:
    """Treina em 2025, avalia em 2026 e re-treina com tudo para produção.

    Returns:
        (modelo final treinado com todos os dados rotulados, métricas
        medidas no teste temporal).
    """
    data = labeled_cases(df)
    features = build_features(data)
    train = data["data_abertura"] < TEST_START
    x_train, x_test = features[train], features[~train]
    y_train, y_test = data.loc[train, "y"], data.loc[~train, "y"]

    model = _make_model().fit(x_train, y_train)
    score = model.predict_proba(x_test)[:, 1]
    baseline = 1 - x_test["tem_reparo_registrado"].to_numpy()

    importance = permutation_importance(
        model, x_test, y_test, scoring="roc_auc", n_repeats=3,
        random_state=RANDOM_STATE)
    importances = dict(sorted(
        ((FEATURE_LABELS[f], round(float(v), 4))
         for f, v in zip(FEATURES, importance.importances_mean)),
        key=lambda item: -item[1]))

    # Onde a regra simples não ajuda: chamados COM registro técnico.
    y_np = y_test.to_numpy()
    registered = x_test["tem_reparo_registrado"].to_numpy() == 1
    reg_score, reg_y = score[registered], y_np[registered]
    reg_top = np.argsort(-reg_score)[: int(len(reg_score) * TOP_SHARE)]
    top10 = np.argsort(-score)[: int(len(score) * 0.10)]

    deciles = pd.qcut(score, 10, labels=False, duplicates="drop")
    calibration = (pd.DataFrame({"decil": deciles, "previsto": score,
                                 "observado": y_test.to_numpy()})
                   .groupby("decil").mean().reset_index()
                   .round(4).to_dict("records"))

    metrics = RiskMetrics(
        n_treino=int(train.sum()), n_teste=int((~train).sum()),
        taxa_retorno_teste=round(float(y_test.mean()), 4),
        auc_modelo=round(roc_auc_score(y_test, score), 4),
        auc_baseline=round(roc_auc_score(y_test, baseline), 4),
        ap_modelo=round(average_precision_score(y_test, score), 4),
        ap_baseline=round(average_precision_score(y_test, baseline), 4),
        captura_top20_modelo=round(_capture(y_test.to_numpy(), score,
                                            TOP_SHARE), 4),
        captura_top20_baseline=round(_capture(y_test.to_numpy(),
                                              baseline.astype(float),
                                              TOP_SHARE), 4),
        precisao_top10_modelo=round(float(y_np[top10].mean()), 4),
        auc_so_com_registro=round(roc_auc_score(reg_y, reg_score), 4),
        taxa_top20_com_registro=round(float(reg_y[reg_top].mean()), 4),
        taxa_media_com_registro=round(float(reg_y.mean()), 4),
        importancias=importances, calibracao=calibration)

    # Modelo de produção: mesmos hiperparâmetros, todos os dados rotulados.
    final = _make_model().fit(features, data["y"])
    return final, metrics


def save(model: HistGradientBoostingClassifier, metrics: RiskMetrics) -> None:
    """Salva o modelo (joblib) e as métricas (JSON legível)."""
    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    METRICS_FILE.write_text(json.dumps(asdict(metrics), ensure_ascii=False,
                                       indent=2), encoding="utf-8")


def load() -> tuple[HistGradientBoostingClassifier, dict] | None:
    """Carrega modelo e métricas; ``None`` se ainda não foi treinado."""
    if not (MODEL_FILE.exists() and METRICS_FILE.exists()):
        return None
    return (joblib.load(MODEL_FILE),
            json.loads(METRICS_FILE.read_text(encoding="utf-8")))


def score_cases(model: HistGradientBoostingClassifier,
                df: pd.DataFrame) -> pd.Series:
    """Probabilidade de retorno em 90 dias para cada chamado válido."""
    valid = df[df["valida"].astype(bool)]
    proba = model.predict_proba(build_features(valid))[:, 1]
    return pd.Series(proba, index=valid.index, name="risco_retorno")


def main() -> None:
    """Treina, avalia, salva e imprime o resumo das métricas."""
    from dna_maquina.pipeline import load_processed

    model, metrics = train_and_evaluate(load_processed())
    save(model, metrics)
    summary = {k: v for k, v in asdict(metrics).items()
               if k not in ("calibracao", "importancias")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Top variáveis:", list(metrics.importancias.items())[:6])


if __name__ == "__main__":
    main()
    sys.exit(0)
