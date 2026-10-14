"""Configuração do backend lida do ambiente (12-factor)."""

from __future__ import annotations

import os

BYTES_PER_MB = 1024 * 1024
MAX_UPLOAD_BYTES = int(os.getenv("DNA_MAX_UPLOAD_MB", "25")) * BYTES_PER_MB
LOG_LEVEL = os.getenv("DNA_LOG_LEVEL", "INFO").upper()

# Colunas de texto digitado por pessoas: sempre passam pela máscara de
# privacidade antes de sair pela API.
TEXT_COLUMNS = (
    "sintoma_cs",
    "laudo",
    "motivo",
    "causa_label",
    "conclusao",
)

# Veredito de uma melhoria (mesma regra da interface anterior).
MIN_GROUP_SIZE = 100
SIGNIFICANCE_LEVEL = 0.05

# Cora: plataforma corporativa de IA que conduz a conversa.
# URL base de onde o navegador abre a Cora (ex.: http://localhost:8000).
# Vazia = a página Assistente mostra como configurar e usa só as
# respostas por regras. A Cora chama as ferramentas daqui pelo /mcp.
CORA_URL = os.getenv("DNA_CORA_URL", "").strip().rstrip("/")
CORA_CONNECTOR_NAME = "DNA da Máquina"
