"""Assistente com Amazon Bedrock: o modelo conversa, as ferramentas calculam.

Alternativa à Cora quando ela não está disponível. O modelo (API Converse
do Bedrock, com *tool use*) recebe o MESMO catálogo de ferramentas do
:class:`dna_maquina.assistant.Toolbox` que a Cora recebe pelo MCP: ele
escolhe a ferramenta, lê o JSON e redige. Os números vêm do código.

Configuração por variáveis de ambiente (as mesmas do resumo da página DNA):
``DNA_USE_BEDROCK=1``, ``AWS_REGION`` e ``BEDROCK_MODEL_ID``. As
credenciais vêm da cadeia padrão do boto3 (variáveis, perfil ou papel IAM).
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd

from dna_maquina.assistant import TOOL_GUIDE, Toolbox
from dna_maquina.llm import DEFAULT_MODEL_ID

MAX_STEPS = 6
"""Rodadas modelo → ferramenta no máximo (evita laço infinito)."""

MAX_TOOL_CHARS = 12_000
"""Tamanho máximo do JSON de uma ferramenta enviado ao modelo."""

SYSTEM_PROMPT = (
    "Você é o assistente de engenharia do DNA da Máquina (P&D e pós-venda "
    "das máquinas de café TRES). Responda em português do Brasil, de forma "
    "objetiva, citando os números e a ferramenta de onde vieram. Escreva "
    "em texto simples, sem Markdown (sem #, ** ou tabelas); use '-' para "
    "listas. "
    + TOOL_GUIDE
)


def _tool_config(toolbox: Toolbox) -> dict:
    """Catálogo do Toolbox no formato ``toolConfig`` da API Converse."""
    specs = []
    for tool in toolbox.tools():
        schema = dict(tool.schema)
        if not schema.get("required"):
            schema.pop("required", None)
        specs.append({"toolSpec": {"name": tool.name,
                                   "description": tool.description,
                                   "inputSchema": {"json": schema}}})
    return {"tools": specs}


def _client():
    import boto3  # import tardio: o app roda sem boto3 instalado

    return boto3.client("bedrock-runtime",
                        region_name=os.getenv("AWS_REGION", "us-east-1"))


def ask(df: pd.DataFrame, question: str, serial: str | None = None,
        client=None) -> dict[str, Any]:
    """Responde uma pergunta usando o Bedrock com as ferramentas do projeto.

    Returns:
        ``{"texto": ..., "ferramentas": [nomes chamados], "fonte": "bedrock"}``.
        Erros do Bedrock sobem para quem chamou (a rota decide o que fazer).
    """
    client = client or _client()
    toolbox = Toolbox(df)
    config = _tool_config(toolbox)
    prompt = question if not serial else (
        f"{question}\n\n(Contexto da tela: máquina de série {serial}.)")
    messages: list[dict] = [{"role": "user", "content": [{"text": prompt}]}]
    used: list[str] = []

    for _ in range(MAX_STEPS):
        response = client.converse(
            modelId=os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=config,
            inferenceConfig={"maxTokens": 1200, "temperature": 0.2},
        )
        message = response["output"]["message"]
        messages.append(message)
        calls = [c["toolUse"] for c in message["content"] if "toolUse" in c]
        if response.get("stopReason") != "tool_use" or not calls:
            text = "\n".join(c["text"] for c in message["content"]
                             if "text" in c).strip()
            return {"texto": text, "ferramentas": used, "fonte": "bedrock"}
        results = []
        for call in calls:
            used.append(call["name"])
            output = json.dumps(toolbox.run(call["name"], call.get("input")),
                                ensure_ascii=False, default=str)
            results.append({"toolResult": {
                "toolUseId": call["toolUseId"],
                "content": [{"text": output[:MAX_TOOL_CHARS]}]}})
        messages.append({"role": "user", "content": results})

    return {"texto": "Não consegui concluir a resposta em poucas etapas; "
                     "reformule a pergunta de forma mais específica.",
            "ferramentas": used, "fonte": "bedrock"}
