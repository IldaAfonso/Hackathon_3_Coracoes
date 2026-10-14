"""
Resumo do DNA da máquina com LLM (Amazon Bedrock), para o técnico.

Pergunta de negócio
-------------------
Persona Carlos (técnico): "Se eu soubesse o que já fizeram nessa máquina,
chegaria sabendo onde olhar." A linha do tempo já existe no app; o LLM a
transforma em 3–4 frases acionáveis: o que aconteceu, qual o padrão e por
onde começar o diagnóstico.

Desenho (decisões de engenharia de LLM)
---------------------------------------
* **Fatos primeiro, texto depois.** O código monta um bloco de FATOS a
  partir dos dados (:func:`build_machine_facts`); o LLM só redige. O
  prompt proíbe inventar peças, números ou procedimentos (anti-alucinação).
* **Três fontes, em ordem:** (1) cache em disco — resposta já gerada para
  os mesmos fatos; (2) Bedrock, se habilitado; (3) resumo determinístico
  por regras. A demo NUNCA depende de rede: basta pré-gerar o cache.
* **Configuração por variáveis de ambiente** (nada de credencial no código):
  ``DNA_USE_BEDROCK=1`` liga a chamada; ``BEDROCK_MODEL_ID`` escolhe o
  modelo; ``AWS_REGION`` a região. As credenciais vêm do perfil AWS padrão.
* **API Converse do Bedrock:** interface única para os modelos do Bedrock,
  facilita trocar de modelo sem mudar código.

Pré-gerar o cache para a demo (precisa de credenciais AWS)::

    DNA_USE_BEDROCK=1 PYTHONPATH=src python -m dna_maquina.llm G5PS000220465809
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass

import pandas as pd

from dna_maquina import config
from dna_maquina.serial import normalize_serial, serial_order_key

CACHE_FILE = config.PROJECT_ROOT / "data" / "cache" / "resumos_llm.json"
DEFAULT_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
"""ID sugerido; confira o ID exato no console do Bedrock (Model catalog)
da conta do hackathon e sobrescreva com ``BEDROCK_MODEL_ID``."""

MAX_EVENTS = 15
"""Máximo de chamados enviados ao LLM (os mais recentes)."""

SYSTEM_PROMPT = (
    "Você é um assistente técnico do Pós-vendas de máquinas de café em "
    "cápsula. Recebe FATOS sobre o histórico de UMA máquina e escreve um "
    "resumo para o técnico que vai atendê-la. Regras: (1) use SOMENTE os "
    "fatos fornecidos; não invente peças, números, datas ou procedimentos; "
    "(2) português do Brasil, no máximo 4 frases curtas; (3) frase 1: o "
    "histórico em números; frase 2: o padrão (sintoma ou causa que se "
    "repete, retornos rápidos); frase 3: por onde começar o diagnóstico, "
    "citando apenas componentes e boletins que aparecem nos fatos; frase "
    "4 (opcional): o que falta registrar. Sem saudações, sem markdown."
)


@dataclass
class Summary:
    """Resumo gerado e de onde ele veio (para transparência na tela)."""

    texto: str
    fonte: str  # "bedrock", "cache" ou "regras"


def build_machine_facts(df: pd.DataFrame, serial: str,
                        improvements: list | None = None) -> str:
    """Monta o bloco de FATOS (texto) sobre uma máquina.

    Args:
        df: Base enriquecida.
        serial: Número de série (normalizado internamente).
        improvements: Catálogo de melhorias (lista de ``Improvement``);
            se informado, os boletins aplicáveis entram nos fatos.

    Returns:
        Texto com uma linha por fato. Vazio se a série não existir.
    """
    key = normalize_serial(serial)
    rows = df[df["serie"] == key].sort_values("data_abertura")
    if rows.empty:
        return ""
    first = rows.iloc[0]
    leaks = int((rows["sintoma_cs"] == config.LEAK_SYMPTOM).sum())
    lines = [
        f"Série: {key} | modelo: {first['modelo']} | fabricação: "
        f"{int(first['ano_fab'])}, semana {int(first['semana_fab'])}",
        f"Chamados no período: {len(rows)} "
        f"({rows['data_abertura'].min():%d/%m/%Y} a "
        f"{rows['data_abertura'].max():%d/%m/%Y}); vazamentos: {leaks}; "
        f"voltas em até 90 dias: {int(rows['reincidente'].sum())}; "
        f"chamados sem registro técnico: "
        f"{int((~rows['tem_reparo_registrado']).sum())}",
        "Recebeu adaptação hidráulica (kit de campo): "
        + ("sim" if rows["fez_adaptacao_hidraulica"].any() else "não"),
    ]
    lines += _improvement_facts(rows, key, improvements or [])
    lines.append("Chamados (mais recentes por último):")
    for _, row in rows.tail(MAX_EVENTS).iterrows():
        conclusion = row["conclusao"] if pd.notna(row["conclusao"]) else (
            "sem registro técnico")
        lines.append(f"- {row['data_abertura']:%d/%m/%Y} | consumidor: "
                     f"{row['sintoma_cs']} | causa lida: "
                     f"{row['causa_label']} | técnico: "
                     f"{str(conclusion)[:160]}")
    return "\n".join(lines)


def _improvement_facts(rows: pd.DataFrame, key: str,
                       improvements: list) -> list[str]:
    """Fatos sobre os boletins de fábrica aplicáveis à série."""
    order = serial_order_key(key)
    model = rows["modelo_serie"].iat[0]
    facts = []
    for item in improvements:
        if item.modelo != model or item.tipo != "corte_serie":
            continue
        has_it = order is not None and order >= serial_order_key(
            item.serie_inicial)
        facts.append(f"Boletim '{item.titulo}': "
                     + ("já sai de fábrica com a melhoria" if has_it
                        else "fabricada ANTES da melhoria"))
    return facts


def rule_based_summary(rows: pd.DataFrame) -> str:
    """Resumo determinístico (sem LLM), a partir dos chamados da máquina.

    Usado quando o Bedrock está desligado ou indisponível. Segue a mesma
    estrutura pedida ao LLM: números, padrão, por onde começar, lacunas.
    """
    if rows.empty:
        return "Série não encontrada na base."
    leaks = int((rows["sintoma_cs"] == config.LEAK_SYMPTOM).sum())
    returns = int(rows["reincidente"].sum())
    missing = int((~rows["tem_reparo_registrado"]).sum())
    text = (f"{len(rows)} chamados entre "
            f"{rows['data_abertura'].min():%m/%Y} e "
            f"{rows['data_abertura'].max():%m/%Y}, {leaks} por vazamento e "
            f"{returns} voltando em até 90 dias.")
    known = rows.loc[rows["tem_reparo_registrado"], "causa_label"]
    counts = known.value_counts()
    if len(counts) and counts.iloc[0] > 1:
        text += (f" Causa que se repete: {counts.index[0].lower()} "
                 f"({counts.iloc[0]} vezes).")
    elif len(counts):
        listed = ", ".join(c.lower() for c in counts.index[:4])
        text += f" Cada técnico registrou uma causa diferente: {listed}."
    if not rows["fez_adaptacao_hidraulica"].any() and leaks:
        text += " Não há registro da adaptação hidráulica."
    if missing:
        text += f" {missing} chamados ficaram sem registro técnico."
    return text


def _cache_key(serial: str, facts: str) -> str:
    """Chave = série + hash dos fatos (fatos mudaram => resumo novo)."""
    digest = hashlib.sha256(facts.encode("utf-8")).hexdigest()[:16]
    return f"{normalize_serial(serial)}:{digest}"


def _read_cache() -> dict[str, str]:
    """Lê o cache de resumos (dicionário chave -> texto)."""
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def _write_cache(cache: dict[str, str]) -> None:
    """Grava o cache em disco (UTF-8, legível)."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def bedrock_enabled() -> bool:
    """Bedrock só é chamado com ``DNA_USE_BEDROCK=1`` (decisão explícita)."""
    return os.getenv("DNA_USE_BEDROCK") == "1"


def call_bedrock(facts: str, client=None) -> str:
    """Chama o modelo no Bedrock via API Converse.

    Args:
        facts: Bloco de fatos da máquina.
        client: Cliente ``bedrock-runtime`` (injetável nos testes).

    Returns:
        Texto gerado pelo modelo.
    """
    if client is None:
        import boto3  # import tardio: o app roda sem boto3 instalado

        client = boto3.client("bedrock-runtime",
                              region_name=os.getenv("AWS_REGION",
                                                    "us-east-1"))
    response = client.converse(
        modelId=os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": "FATOS:\n" + facts}]}],
        inferenceConfig={"maxTokens": 300, "temperature": 0.2},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def summarize(df: pd.DataFrame, serial: str, improvements: list | None = None,
              client=None) -> Summary:
    """Resumo da máquina: cache → Bedrock → regras, nessa ordem.

    Qualquer erro do Bedrock (credencial, rede, cota) cai no resumo por
    regras — a tela nunca quebra durante a demo.
    """
    facts = build_machine_facts(df, serial, improvements)
    if not facts:
        return Summary("Série não encontrada na base.", "regras")
    cache = _read_cache()
    key = _cache_key(serial, facts)
    if key in cache:
        return Summary(cache[key], "cache")
    if bedrock_enabled() or client is not None:
        try:
            text = call_bedrock(facts, client)
        except Exception as error:  # noqa: BLE001 — fallback deliberado
            print(f"[llm] Bedrock indisponível: {error}", file=sys.stderr)
        else:
            cache[key] = text
            _write_cache(cache)
            return Summary(text, "bedrock")
    rows = df[df["serie"] == normalize_serial(serial)].sort_values(
        "data_abertura")
    return Summary(rule_based_summary(rows), "regras")


def main(serials: list[str]) -> None:
    """CLI: gera (e guarda em cache) o resumo das séries informadas."""
    from dna_maquina.impact import load_improvements
    from dna_maquina.pipeline import load_processed

    df = load_processed()
    for serial in serials:
        result = summarize(df, serial, load_improvements())
        print(f"\n[{serial}] fonte={result.fonte}\n{result.texto}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["G5PS000220465809"])
