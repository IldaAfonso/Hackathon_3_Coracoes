"""Pré-voo do Amazon Bedrock: diz, em português, o que consertar.

Uso (com os serviços no ar)::

    make bedrock-check

Roda DENTRO do container do backend e confere, nesta ordem: variáveis,
credenciais e uma chamada simples ao modelo. Cada falha vem com o
diagnóstico e a correção. Nunca imprime chave ou token.

No MVP o Bedrock só redige o resumo em texto da página DNA (opcional).
O assistente é a Cora, que usa o modelo e a credencial dela; para
conferir o caminho da Cora até as ferramentas, use ``make mcp-check``.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Mapping

DEFAULT_REGION = "us-east-1"
DEFAULT_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
MAX_TOKENS = 60

_CODE_HINTS: dict[str, str] = {
    "NoCredentialsError": (
        "o container não enxerga credenciais AWS. Exporte "
        "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (e AWS_SESSION_TOKEN) "
        "no terminal ANTES de subir, ou use AWS_PROFILE com "
        "compose.aws.yaml (docs/BEDROCK_E_AWS.md)."
    ),
    "PartialCredentialsError": (
        "credencial incompleta: falta a chave secreta ou o token."
    ),
    "ExpiredTokenException": (
        "as credenciais temporárias expiraram: gere novas e suba de novo."
    ),
    "ExpiredToken": (
        "as credenciais temporárias expiraram: gere novas e suba de novo."
    ),
    "RequestExpired": (
        "o relógio da máquina está fora de hora ou a credencial expirou."
    ),
    "UnrecognizedClientException": (
        "credencial inválida (chave errada, de outra conta ou de outra "
        "partição). Confira as chaves."
    ),
    "InvalidSignatureException": (
        "assinatura inválida: chave secreta errada ou relógio fora de hora."
    ),
    "ResourceNotFoundException": (
        "modelo não encontrado nesta região: confira AWS_REGION e "
        "BEDROCK_MODEL_ID."
    ),
    "ThrottlingException": (
        "limite de requisições: espere alguns segundos. Para a demo, use "
        "o cache (make bedrock-warm)."
    ),
    "TooManyRequestsException": (
        "limite de requisições: espere alguns segundos."
    ),
    "ServiceQuotaExceededException": (
        "cota da conta esgotada para este modelo."
    ),
    "ModelNotReadyException": "o modelo ainda não está pronto: tente de novo.",
    "EndpointConnectionError": (
        "sem rede até o Bedrock: confira internet, proxy ou VPN."
    ),
    "ConnectTimeoutError": (
        "sem rede até o Bedrock: confira internet, proxy ou VPN."
    ),
    "ReadTimeoutError": "o Bedrock demorou demais: tente de novo.",
}


def error_code(error: BaseException) -> str:
    """Código do erro da AWS, ou o nome da classe se não houver."""
    response = getattr(error, "response", None) or {}
    return response.get("Error", {}).get("Code") or type(error).__name__


def diagnose(error: BaseException) -> str:
    """Traduz um erro do boto3 em diagnóstico acionável.

    Função pura (testada): recebe a exceção, devolve texto.
    """
    code = error_code(error)
    message = str(error).lower()
    if code == "AccessDeniedException":
        return (
            f"{code}: sem permissão ou modelo não habilitado. A identidade "
            "precisa de bedrock:InvokeModel (no modelo e no perfil de "
            "inferência) e o acesso ao modelo precisa estar habilitado no "
            "console do Bedrock, nesta região."
        )
    if code == "ValidationException":
        if "inference profile" in message or "on-demand" in message:
            return (
                f"{code}: este modelo exige um PERFIL DE INFERÊNCIA. Use o "
                "ID com prefixo de região (ex.: us.anthropic...) copiado "
                "do console, em Inference profiles."
            )
        return (
            f"{code}: ID do modelo inválido ou parâmetro rejeitado. Copie "
            "o ID exato do console (Model catalog)."
        )
    hint = _CODE_HINTS.get(code)
    if hint:
        return f"{code}: {hint}"
    return f"{code}: erro inesperado. Leia a mensagem completa abaixo."


def check_env(env: Mapping[str, str]) -> list[tuple[str, str]]:
    """Confere as variáveis; devolve pares (nível, texto). Pura."""
    notes = []
    if env.get("DNA_USE_BEDROCK") != "1":
        notes.append(
            (
                "AVISO",
                "DNA_USE_BEDROCK não é 1: o resumo da máquina sai "
                "por regras (o assistente ainda tenta o Bedrock).",
            )
        )
    region = env.get("AWS_REGION") or DEFAULT_REGION
    notes.append(
        (
            "INFO",
            f"região: {region}"
            + ("" if env.get("AWS_REGION") else " (padrão)"),
        )
    )
    model = env.get("BEDROCK_MODEL_ID") or DEFAULT_MODEL_ID
    notes.append(
        (
            "INFO",
            f"modelo: {model}"
            + ("" if env.get("BEDROCK_MODEL_ID") else " (padrão)"),
        )
    )
    has_keys = bool(env.get("AWS_ACCESS_KEY_ID"))
    has_profile = bool(env.get("AWS_PROFILE"))
    has_role = bool(
        env.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        or env.get("AWS_WEB_IDENTITY_TOKEN_FILE")
    )
    if not (has_keys or has_profile or has_role):
        notes.append(
            (
                "AVISO",
                "nenhuma credencial nas variáveis do container "
                "(AWS_ACCESS_KEY_ID, AWS_PROFILE ou role).",
            )
        )
    return notes


def say(level: str, text: str) -> None:
    """Imprime uma linha de resultado."""
    print(f"{level:5s} {text}")


def list_candidates(region: str) -> None:
    """Sugere IDs de modelos Anthropic (se a permissão deixar)."""
    try:
        import boto3

        client = boto3.client("bedrock", region_name=region)
        profiles = client.list_inference_profiles(typeEquals="SYSTEM_DEFINED")
        ids = [
            p["inferenceProfileId"]
            for p in profiles.get("inferenceProfileSummaries", [])
            if "anthropic" in p["inferenceProfileId"]
        ]
    except Exception:  # noqa: BLE001 - dica opcional, nunca bloqueia
        return
    if ids:
        say("DICA", "perfis Anthropic nesta região: " + ", ".join(ids[:6]))


def call_simple(client, model_id: str) -> float:
    """Uma chamada mínima; devolve a latência em segundos."""
    start = time.perf_counter()
    reply = client.converse(
        modelId=model_id,
        messages=[
            {"role": "user", "content": [{"text": "Responda apenas: OK"}]}
        ],
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0},
    )
    text = reply["output"]["message"]["content"][0]["text"].strip()
    say(
        "OK",
        f"chamada simples ({time.perf_counter() - start:.1f}s): {text[:30]!r}",
    )
    return time.perf_counter() - start


def main() -> int:
    """Roda as verificações; código de saída 1 se alguma falhar."""
    for level, text in check_env(os.environ):
        say(level, text)
    region = os.getenv("AWS_REGION") or DEFAULT_REGION
    model_id = os.getenv("BEDROCK_MODEL_ID") or DEFAULT_MODEL_ID
    try:
        import boto3

        session = boto3.Session(region_name=region)
        who = session.client("sts").get_caller_identity()
        say(
            "OK", f"credenciais válidas (conta final ...{who['Account'][-4:]})"
        )
        client = session.client("bedrock-runtime")
        call_simple(client, model_id)
    except Exception as error:  # noqa: BLE001 - o diagnóstico é o produto
        say("FALHA", diagnose(error))
        say("", f"detalhe: {str(error)[:300]}")
        list_candidates(region)
        return 1
    print("\nBEDROCK PRONTO (resumos da página DNA)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
