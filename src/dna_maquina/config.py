"""
Configuração central do projeto DNA da Máquina.

Este módulo concentra TODAS as constantes que descrevem o formato dos dados
de entrada (extração do Salesforce), para que nenhuma outra parte do código
precise conhecer os nomes "crus" das colunas da planilha. Se a 3corações
mudar o layout do relatório, só este arquivo precisa ser alterado.

Decisões registradas aqui:
    * Os nomes de coluna da planilha original são mapeados para nomes
      canônicos em snake_case (PEP 8), sem acentos, para uso no código.
    * As colunas "Mês" e "Ano" da planilha original são fórmulas do Excel
      (ex.: ``=TEXT(F2,"mmmm")``) e chegam como texto da fórmula, não como
      valor. Por isso elas são descartadas e recalculadas a partir da data
      de abertura do chamado.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos padrão do projeto
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
"""Raiz do repositório (dois níveis acima de ``src/dna_maquina``)."""

RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
"""Pasta onde ficam as planilhas .xlsx originais, sem nenhuma alteração."""

PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"
"""Pasta onde o pipeline grava a base tratada (formato Parquet)."""

IMPROVEMENTS_FILE: Path = PROJECT_ROOT / "data" / "melhorias.json"
"""Catálogo de melhorias de engenharia (boletins e informativos técnicos)."""

PROCESSED_FILE: Path = PROCESSED_DIR / "chamados.parquet"
"""Base consolidada e enriquecida, lida pelo app Streamlit."""

# ---------------------------------------------------------------------------
# Mapeamento de colunas: nome na planilha -> nome canônico no código
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, str] = {
    "Número do caso": "case_id",
    "Classificação do Atendimento": "classificacao",
    "Assunto CS": "assunto_cs",
    "Detalhamento CS": "sintoma_cs",
    "Tipo de registro do caso": "tipo_registro",
    "Data de abertura": "data_abertura",
    "Nome do produto": "produto",
    "Número de série": "serie_raw",
    "Data da instalação": "data_instalacao",
    "Modelo da Máquina": "modelo",
    "Atendimento": "atendimento",
    "Laudo Técnico": "laudo",
    "Motivo Técnico": "motivo",
    "Conclusão Técnica": "conclusao",
    "Código da melhoria": "codigo_melhoria",
}

REQUIRED_COLUMNS: tuple[str, ...] = (
    "Número do caso",
    "Detalhamento CS",
    "Data de abertura",
    "Número de série",
    "Modelo da Máquina",
)
"""Colunas mínimas para o pipeline funcionar. As demais são opcionais e,
se ausentes numa nova base importada, são criadas vazias."""

DATE_COLUMNS: tuple[str, ...] = ("data_abertura", "data_instalacao")

# ---------------------------------------------------------------------------
# Limites de sanidade para datas (qualidade de dados)
# ---------------------------------------------------------------------------
MIN_PLAUSIBLE_INSTALL_YEAR: int = 2018
"""A linha G4/G5 não existia antes disso; datas anteriores são marcadas
como suspeitas (há registros com instalação em 1964 na base)."""

# ---------------------------------------------------------------------------
# Parâmetros analíticos
# ---------------------------------------------------------------------------
REINCIDENCE_WINDOW_DAYS: int = 90
"""Janela para considerar que um problema "voltou" depois de um reparo.
90 dias é um prazo usual de garantia de serviço no Brasil (CDC, art. 26)."""

LEAK_SYMPTOM: str = "Máquina vazando"
"""Sintoma-alvo das três melhorias documentadas do G5 Passione."""
