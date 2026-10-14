"""Estado compartilhado: a base enriquecida e seus derivados em cache.

As análises do núcleo são funções puras sobre um DataFrame. Aqui só se
decide QUANDO calcular e se guarda o resultado até a base mudar
(importação de uma nova planilha).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pandas as pd

from app import bootstrap  # noqa: F401  (antes dos módulos de análise)
from app.privacy import mask_frame
from app.settings import TEXT_COLUMNS
from dna_maquina import analytics, history, patterns, reliability, risk
from dna_maquina.pipeline import load_processed, save


class State:
    """Uma base, caches derivados e invalidação ao importar."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._df: pd.DataFrame | None = None
        self._cache: dict[str, Any] = {}

    @property
    def df(self) -> pd.DataFrame:
        """A base enriquecida (carregada na primeira vez)."""
        with self._lock:
            if self._df is None:
                self._df = load_processed()
            return self._df

    def masked(self) -> pd.DataFrame:
        """A base com o texto livre mascarado.

        É a ÚNICA versão que pode ir para um modelo de linguagem: os
        resumos e o assistente montam o prompt a partir de textos
        digitados por pessoas, e a base real tem um telefone escrito à
        mão. Mascarar só a resposta da API não impede que o dado saia
        da máquina na ida.
        """
        return self.memo(
            "masked", lambda: mask_frame(self.df, list(TEXT_COLUMNS))
        )

    def replace(self, df: pd.DataFrame) -> None:
        """Troca a base, grava o Parquet e descarta os caches."""
        with self._lock:
            save(df)
            self._df = df
            self._cache.clear()

    def memo(self, key: str, compute: Callable[[], Any]) -> Any:
        """Calcula uma vez por base e guarda em cache."""
        with self._lock:
            if key not in self._cache:
                self._cache[key] = compute()
            return self._cache[key]

    def summary(self) -> pd.DataFrame:
        """Ficha resumida de cada máquina."""
        return self.memo("summary", lambda: history.machine_summary(self.df))

    def radar(self) -> pd.DataFrame:
        """Alertas do radar de problemas."""
        return self.memo("radar", lambda: analytics.radar(self.df))

    def machine_confidence(self) -> pd.Series:
        """Nota de confiabilidade do DNA por máquina."""
        return self.memo(
            "machine_confidence",
            lambda: reliability.machine_confidence(self.df),
        )

    def failure_modes(self):
        """Modos de falha descobertos no texto dos técnicos."""
        return self.memo(
            "failure_modes", lambda: patterns.discover_failure_modes(self.df)
        )

    def risk_model(self):
        """Modelo de risco e métricas; treina na hora se não existir."""

        def build():
            loaded = risk.load()
            if loaded is None:
                model, metrics = risk.train_and_evaluate(self.df)
                risk.save(model, metrics)
                loaded = risk.load()
            return loaded

        return self.memo("risk_model", build)

    def risk_scores(self) -> pd.Series:
        """Risco de retorno em 90 dias de cada chamado."""
        return self.memo(
            "risk_scores",
            lambda: risk.score_cases(self.risk_model()[0], self.df),
        )

    def cause_model(self):
        """Modelo de causa provável; treina na hora se não existir."""

        def build():
            loaded = reliability.load_cause_model()
            if loaded is None:
                model, metrics = reliability.train_cause_model(self.df)
                reliability.save_cause_model(model, metrics)
                loaded = reliability.load_cause_model()
            return loaded

        return self.memo("cause_model", build)

    def probable_causes(self) -> pd.DataFrame:
        """Causa provável (IA) de cada chamado sem laudo."""
        return self.memo(
            "probable_causes",
            lambda: reliability.probable_causes(
                self.cause_model()[0], self.df
            ),
        )


state = State()
