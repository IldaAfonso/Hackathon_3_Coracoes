"""
Ingestão e limpeza da extração de chamados (planilha .xlsx do Salesforce).

Fluxo implementado por :func:`load_complaints`:

1. Lê a primeira aba da planilha (ou a aba indicada);
2. Valida se as colunas mínimas existem (:data:`config.REQUIRED_COLUMNS`);
3. Renomeia para nomes canônicos e descarta colunas vazias ("Unnamed");
4. Converte datas e recalcula ano/mês (as colunas originais são fórmulas);
5. Normaliza e decodifica o número de série (:mod:`dna_maquina.serial`);
6. Marca problemas de qualidade de dados SEM apagar registros — o desafio
   diz que dados imperfeitos são parte do problema real, então o protótipo
   mostra a imperfeição em vez de escondê-la.

A função :func:`merge_bases` implementa o diferencial pedido no desafio:
importar uma nova base .xlsx e atualizar as análises, sem duplicar chamados.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd

from dna_maquina import config
from dna_maquina.serial import decode_serial_column


class SchemaError(ValueError):
    """Erro levantado quando a planilha não tem as colunas obrigatórias."""


def _validate_columns(raw: pd.DataFrame) -> None:
    """Garante que a planilha tem as colunas mínimas para a análise.

    Raises:
        SchemaError: Com a lista de colunas faltantes, para o app exibir
            uma mensagem clara ao usuário que importou a base.
    """
    missing = [c for c in config.REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise SchemaError(
            "A planilha não tem as colunas obrigatórias: " + ", ".join(missing)
        )


def _parse_dates(column: pd.Series) -> pd.Series:
    """Converte datas aceitando os formatos que aparecem em extrações.

    * Células já datadas pelo Excel chegam como ``datetime`` (mantidas);
    * Textos ISO ``AAAA-MM-DD`` são lidos como ano-mês-dia;
    * Demais textos (ex.: ``15/02/2025``) são lidos no padrão brasileiro,
      dia primeiro. Valores ilegíveis viram ``NaT`` (não quebram a carga).
    """
    if pd.api.types.is_datetime64_any_dtype(column):
        return column
    text = column.astype("string").str.strip()
    is_iso = text.str.match(r"^\d{4}-\d{2}-\d{2}").fillna(False)
    iso = pd.to_datetime(text.where(is_iso).str[:10], errors="coerce",
                         format="%Y-%m-%d")
    brazilian = pd.to_datetime(text.where(~is_iso), errors="coerce",
                               dayfirst=True, format="mixed")
    return iso.fillna(brazilian)


def _add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Cria colunas booleanas ``dq_*`` descrevendo a qualidade do registro.

    * ``dq_serie_invalida``: série não decodificável (não entra no DNA nem
      na análise antes/depois, mas continua nas contagens gerais);
    * ``dq_instalacao_suspeita``: instalação antes de 2018 ou no futuro;
    * ``dq_abertura_antes_instalacao``: chamado aberto antes da instalação;
    * ``dq_modelo_divergente``: modelo informado difere do prefixo da série;
    * ``dq_sem_conclusao``: chamado sem conclusão técnica registrada.
    """
    out = df.copy()
    today = pd.Timestamp.today().normalize()
    install = out["data_instalacao"]
    out["dq_serie_invalida"] = ~out["valida"]
    out["dq_instalacao_suspeita"] = (
        (install.dt.year < config.MIN_PLAUSIBLE_INSTALL_YEAR)
        | (install > today)
    )
    out["dq_abertura_antes_instalacao"] = out["data_abertura"] < install
    out["dq_modelo_divergente"] = (
        out["modelo_serie"].notna() & (out["modelo_serie"] != out["modelo"])
    )
    out["dq_sem_conclusao"] = out["conclusao"].isna()
    return out


def clean_complaints(raw: pd.DataFrame) -> pd.DataFrame:
    """Transforma o DataFrame cru da planilha no DataFrame canônico.

    Args:
        raw: Conteúdo da planilha exatamente como lido pelo pandas.

    Returns:
        DataFrame com nomes canônicos, datas tipadas, série decodificada
        e flags de qualidade. Um registro por chamado (``case_id``).

    Raises:
        SchemaError: Se faltarem colunas obrigatórias.
    """
    _validate_columns(raw)
    df = raw.rename(columns=config.COLUMN_MAP)
    df = df[[c for c in config.COLUMN_MAP.values() if c in df.columns]].copy()
    for column in config.COLUMN_MAP.values():  # colunas opcionais ausentes
        if column not in df.columns:
            df[column] = pd.NA

    for column in config.DATE_COLUMNS:
        df[column] = _parse_dates(df[column])
    df["case_id"] = pd.to_numeric(df["case_id"], errors="coerce")
    df = df.dropna(subset=["case_id", "data_abertura"])
    df["case_id"] = df["case_id"].astype("int64")

    # Textos: remove espaços extras; mantém NaN como ausente.
    text_cols = ["sintoma_cs", "modelo", "laudo", "motivo", "conclusao",
                 "produto", "atendimento"]
    for column in text_cols:
        df[column] = df[column].astype("string").str.strip()
        df[column] = df[column].replace("", pd.NA)

    # Código da melhoria aplicada (campo de lista no chamado): caixa alta.
    df["codigo_melhoria"] = (df["codigo_melhoria"].astype("string")
                             .str.strip().str.upper()
                             .replace("", pd.NA))

    # Recalcula o período (as colunas Mês/Ano da planilha são fórmulas).
    df["ano"] = df["data_abertura"].dt.year
    df["mes"] = df["data_abertura"].dt.to_period("M").dt.to_timestamp()

    # Tensão e cor a partir do nome do produto (ex.: "... PT 127V").
    produto = df["produto"].fillna("")
    df["tensao"] = produto.str.extract(r"(127|220)V", expand=False)
    df["cor"] = produto.str.extract(r"\b(PT|VM|BR)\b", expand=False)

    decoded = decode_serial_column(df["serie_raw"])
    df = pd.concat([df, decoded], axis=1)
    df = df.drop_duplicates(subset="case_id", keep="last")
    return _add_quality_flags(df).reset_index(drop=True)


def read_excel(source: str | Path | BinaryIO,
               sheet_name: str | int = 0) -> pd.DataFrame:
    """Lê a planilha de chamados (arquivo em disco ou upload do app).

    Args:
        source: Caminho do .xlsx ou objeto de arquivo (``st.file_uploader``).
        sheet_name: Aba a ler; por padrão a primeira.

    Returns:
        DataFrame cru, ainda com os nomes originais das colunas.
    """
    return pd.read_excel(source, sheet_name=sheet_name)


def load_complaints(source: str | Path | BinaryIO) -> pd.DataFrame:
    """Atalho: lê e limpa a planilha em um único passo."""
    return clean_complaints(read_excel(source))


def merge_bases(current: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    """Junta uma base nova à existente, sem duplicar chamados.

    Regra: quando o mesmo ``case_id`` aparece nas duas bases, vale o
    registro mais NOVO (a extração mais recente pode trazer a conclusão
    técnica que antes estava vazia).

    Args:
        current: Base já tratada e enriquecida.
        incoming: Base recém-importada (já passada por ``clean_complaints``).

    Returns:
        Base combinada, ordenada por data de abertura.
    """
    combined = pd.concat([current, incoming], ignore_index=True)
    combined = combined.drop_duplicates(subset="case_id", keep="last")
    return combined.sort_values("data_abertura").reset_index(drop=True)
