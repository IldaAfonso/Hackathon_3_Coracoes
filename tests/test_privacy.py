"""Privacidade: nada de dado pessoal sai pela API.

A conferência da base do desafio achou um telefone real escrito à mão
num texto de técnico; estes testes travam o comportamento da máscara.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.privacy import count_matches, mask_frame, mask_text


@pytest.mark.parametrize(
    "text",
    [
        "ligar para (11) 91234-5678 amanhã",
        "ligar 11 91234-5678",
        "fone 11912345678",
        "tel +55 11 91234 5678",
        "fixo 11 3456-7890",
    ],
)
def test_phone_numbers_are_masked(text):
    masked = mask_text(text)
    assert "[telefone]" in masked
    assert not any(ch.isdigit() for ch in masked.replace("[telefone]", ""))


def test_email_cpf_and_cep_are_masked():
    masked = mask_text(
        "maria@exemplo.com.br, CPF 123.456.789-09, CEP 01310-100"
    )
    assert "[e-mail]" in masked and "[CPF]" in masked and "[CEP]" in masked
    assert "@" not in masked and "123.456" not in masked


@pytest.mark.parametrize(
    "serial",
    [
        "G5PS000210224033",
        "G4LN127232802098",
        "G5PS127241004388",
    ],
)
def test_machine_serials_are_never_masked(serial):
    """A série é a chave do produto: mascará-la quebra o histórico."""
    assert (
        mask_text(f"série {serial} sem vazamento")
        == f"série {serial} sem vazamento"
    )


def test_part_numbers_dates_and_counts_survive():
    text = "Trocado 3000017 em 13/10/2026, 2 peças, 15 dias, 40 minutos"
    assert mask_text(text) == text


def test_non_text_values_pass_through():
    assert mask_text(None) is None
    assert mask_text(42) == 42
    assert pd.isna(mask_text(float("nan")))


def test_mask_frame_masks_only_requested_existing_columns():
    df = pd.DataFrame({"a": ["tel 11 91234-5678"], "b": ["tel 11 91234-5678"]})
    out = mask_frame(df, ["a", "inexistente"])
    assert "[telefone]" in out["a"].iat[0]
    assert out["b"].iat[0] == df["b"].iat[0]
    assert "[telefone]" not in df["a"].iat[0]  # o original não é alterado


def test_count_matches_counts_cells_not_matches():
    series = pd.Series(["ok", "ligar 11 91234-5678", None, "a@b.co"])
    assert count_matches(series) == 2
