"""Diagnóstico do Bedrock: cada erro vira uma instrução em português.

Sem credenciais aqui, o que se testa é a lógica de diagnóstico (funções
puras). A chamada real só pode ser verificada na máquina que tem as
credenciais: `make bedrock-check`.
"""

from __future__ import annotations

import pytest
from scripts.bedrock_check import (
    DEFAULT_MODEL_ID,
    check_env,
    diagnose,
    error_code,
)
from scripts.bedrock_warm import warmed


class FakeAwsError(Exception):
    """Imita o ClientError do botocore (tem `.response`)."""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.response = {"Error": {"Code": code, "Message": message}}


@pytest.mark.parametrize(
    "code, trecho",
    [
        ("AccessDeniedException", "bedrock:InvokeModel"),
        ("ExpiredTokenException", "expiraram"),
        ("UnrecognizedClientException", "credencial inválida"),
        ("ResourceNotFoundException", "AWS_REGION"),
        ("ThrottlingException", "bedrock-warm"),
    ],
)
def test_known_aws_errors_get_an_actionable_hint(code, trecho):
    assert trecho in diagnose(FakeAwsError(code))


def test_inference_profile_error_names_the_fix():
    erro = FakeAwsError(
        "ValidationException",
        "Invocation with on-demand throughput isn't supported",
    )
    assert "PERFIL DE INFERÊNCIA" in diagnose(erro)


def test_plain_validation_error_asks_for_the_exact_model_id():
    assert "ID exato" in diagnose(FakeAwsError("ValidationException", "x"))


def test_missing_credentials_error_points_to_the_exports():
    class NoCredentialsError(Exception):
        pass

    texto = diagnose(NoCredentialsError("Unable to locate credentials"))
    assert "AWS_ACCESS_KEY_ID" in texto and "AWS_PROFILE" in texto


def test_unknown_error_is_still_reported_with_its_code():
    assert error_code(FakeAwsError("AlgoNovo")) == "AlgoNovo"
    assert "AlgoNovo" in diagnose(FakeAwsError("AlgoNovo"))


def test_environment_check_flags_missing_credentials_and_flag():
    notes = dict()
    for level, text in check_env({}):
        notes.setdefault(level, []).append(text)
    assert any("DNA_USE_BEDROCK" in t for t in notes["AVISO"])
    assert any("credencial" in t for t in notes["AVISO"])
    assert any(DEFAULT_MODEL_ID in t for t in notes["INFO"])


def test_environment_check_is_quiet_when_everything_is_set():
    env = {
        "DNA_USE_BEDROCK": "1",
        "AWS_ACCESS_KEY_ID": "x",
        "AWS_REGION": "us-east-1",
        "BEDROCK_MODEL_ID": "m",
    }
    assert not [n for n in check_env(env) if n[0] == "AVISO"]


def test_credentials_are_never_printed_by_the_check():
    secret = "AKIAFAKEKEYFORTEST123"
    texts = [t for _, t in check_env({"AWS_ACCESS_KEY_ID": secret})]
    assert not any(secret in t for t in texts)


def test_warm_only_counts_bedrock_or_cache_as_warmed():
    assert warmed("bedrock") and warmed("cache")
    assert not warmed("regras") and not warmed("offline")
    assert not warmed(None)
