"""
Pipeline de ponta a ponta: planilha .xlsx -> base enriquecida (Parquet).

Uso pela linha de comando::

    python -m dna_maquina.pipeline                 # processa data/raw/*.xlsx
    python -m dna_maquina.pipeline caminho.xlsx    # processa um arquivo

O app Streamlit chama :func:`enrich` diretamente quando o usuário importa
uma nova base pela interface, então CLI e app produzem o mesmo resultado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from dna_maquina import config
from dna_maquina.analytics import add_voice_agreement
from dna_maquina.history import add_machine_sequence
from dna_maquina.ingest import load_complaints, merge_bases
from dna_maquina.reliability import add_recovered_cohorts, record_confidence
from dna_maquina.taxonomy import classify_repairs


def enrich(clean: pd.DataFrame) -> pd.DataFrame:
    """Aplica todas as etapas analíticas sobre a base limpa.

    Ordem: taxonomia do reparo -> concordância das vozes -> sequência por
    máquina (DNA) -> camada de confiabilidade (coorte recuperada por IA
    para séries ilegíveis e nota de confiabilidade 0–100 por chamado).
    A função é idempotente: pode ser chamada de novo sobre uma base já
    enriquecida (as colunas são recalculadas).
    """
    data = classify_repairs(clean)
    data = add_voice_agreement(data)
    data = add_machine_sequence(data)
    data = add_recovered_cohorts(data)
    data["confianca"] = record_confidence(data)
    return data


def build_from_files(paths: list[Path]) -> pd.DataFrame:
    """Lê várias planilhas, junta sem duplicar e enriquece o resultado."""
    if not paths:
        raise FileNotFoundError(
            f"Nenhuma planilha .xlsx encontrada em {config.RAW_DIR}")
    combined = load_complaints(paths[0])
    for path in paths[1:]:
        combined = merge_bases(combined, load_complaints(path))
    return enrich(combined)


def save(df: pd.DataFrame, path: Path = config.PROCESSED_FILE) -> Path:
    """Grava a base enriquecida em Parquet (rápido e preserva tipos)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def load_processed(path: Path = config.PROCESSED_FILE) -> pd.DataFrame:
    """Lê a base processada; se não existir, processa ``data/raw``."""
    if path.exists():
        return pd.read_parquet(path)
    df = build_from_files(sorted(config.RAW_DIR.glob("*.xlsx")))
    save(df, path)
    return df


def main(argv: list[str]) -> None:
    """Ponto de entrada da linha de comando."""
    paths = ([Path(a) for a in argv] if argv
             else sorted(config.RAW_DIR.glob("*.xlsx")))
    df = build_from_files(paths)
    out = save(df)
    print(f"{len(df):,} chamados | {df['serie'].nunique():,} séries | "
          f"salvo em {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
