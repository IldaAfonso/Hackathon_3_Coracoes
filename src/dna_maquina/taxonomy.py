"""
Taxonomia de falhas: transforma o texto livre do técnico em componentes.

Por que este módulo existe
--------------------------
Cada chamado tem "duas vozes":

* a do **consumidor**, registrada pelo Customer Success em ``sintoma_cs``
  (ex.: "Máquina vazando") — o SINTOMA percebido;
* a do **técnico**, em ``laudo``, ``motivo`` e ``conclusao`` (texto livre,
  ex.: "feito adaptação (bico e T), troca do oring") — a CAUSA e a AÇÃO.

O campo ``motivo`` é padronizado, mas genérico demais ("AJUSTE SEM TROCA DE
PEÇA" aparece 5 mil vezes). A informação rica está no texto livre. Aqui
aplicamos regras de palavras-chave (expressões regulares), escolhidas com
o olhar de engenharia de confiabilidade, para extrair:

1. ``componentes``: lista de componentes citados no reparo;
2. ``causa_principal``: o componente mais "forte" (prioridade definida
   abaixo: troca de peça vale mais que higienização);
3. ``familia_tecnica``: Hidráulico, Elétrico, Mecânico, Uso/Ambiente, Sem
   defeito — compatível com o ``laudo`` original;
4. flags das melhorias de campo do G5 (adaptação hidráulica, O-ring,
   bandeja), usadas para medir a efetividade dos boletins técnicos.

Abordagem baseada em regras (e não em LLM) foi escolhida para o protótipo
por ser auditável pelo P&D: cada classificação pode ser explicada pela
palavra que a disparou. Um classificador via Amazon Bedrock é um passo
natural da POC e pode usar estas regras como rótulos iniciais.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import pandas as pd


def strip_accents(text: object) -> str:
    """Remove acentos e coloca em minúsculas, para casar regex de forma
    robusta contra textos digitados à mão ("higienizaçao", "HIGIENIZAÇÃO").
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


@dataclass(frozen=True)
class Component:
    """Um componente (ou ação) reconhecível no texto do técnico.

    Attributes:
        key: Identificador interno em snake_case.
        label: Nome amigável exibido no app.
        family: Família técnica (Hidráulico, Elétrico, Mecânico, ...).
        priority: Quanto MENOR, mais forte como causa principal.
        pattern: Expressão regular aplicada ao texto sem acentos.
    """

    key: str
    label: str
    family: str
    priority: int
    pattern: re.Pattern[str]


def _rx(expression: str) -> re.Pattern[str]:
    """Compila uma regex já com ignore-case (atalho de legibilidade)."""
    return re.compile(expression, flags=re.IGNORECASE)


# Ordem de prioridade: troca de peça estrutural > peça hidráulica > ajuste
# > limpeza > orientação > sem defeito. Isso reflete a lógica de análise de
# falhas: a causa-raiz é o componente que precisou ser substituído.
COMPONENTS: tuple[Component, ...] = (
    Component("unidade_extracao", "Unidade/grupo de extração", "Mecânico",
              10, _rx(r"unidade|grupo|camara|guarnic")),
    Component("placa_eletronica", "Placa eletrônica / painel", "Elétrico",
              11, _rx(r"placa|fusivel|display|painel|teclado|interface")),
    Component("termobloco", "Termobloco / aquecimento", "Elétrico",
              12, _rx(r"termobloc|caldeira|resistencia|sensor de temp")),
    Component("bomba", "Bomba d'água", "Hidráulico",
              13, _rx(r"bomba")),
    Component("contador_volumetrico", "Contador volumétrico", "Hidráulico",
              14, _rx(r"contador|fluxometro")),
    Component("vedacao_oring", "Vedação / O-ring / anel", "Hidráulico",
              15, _rx(r"o-?ring|anel|vedac")),
    Component("bandeja", "Bandeja de cápsulas", "Mecânico",
              16, _rx(r"bandeja")),
    Component("conexoes_hidraulicas", "Conexões / mangueiras / junção",
              "Hidráulico", 17,
              _rx(r"conex|junc|uniao|mangueira|tubo|\bt\)|\btee\b|adapta")),
    Component("pino_ceramico", "Pino cerâmico / agulha", "Mecânico",
              18, _rx(r"pino|agulha|lanca")),
    Component("alavanca", "Alavanca / manopla", "Mecânico",
              19, _rx(r"alavanca|manopla")),
    Component("bico_saida", "Bico de saída (entupimento)", "Hidráulico",
              30, _rx(r"bico|desobstr|entup")),
    Component("fauna", "Fauna nociva / infestação", "Uso/Ambiente",
              31, _rx(r"barata|formiga|inseto|infest|fauna")),
    Component("higienizacao", "Higienização / descalcificação",
              "Uso/Ambiente", 40, _rx(r"higien|limpeza|descalc|retrolav")),
    Component("orientacao_uso", "Orientação de uso / mau uso",
              "Uso/Ambiente", 41,
              _rx(r"orienta|instruc|mau uso|uso de leite|leite")),
    Component("sem_defeito", "Sem defeito constatado", "Sem defeito",
              50, _rx(r"sem defeito|nenhum defeito|sem deeito|sem anomalia")),
)

COMPONENT_LABELS: dict[str, str] = {c.key: c.label for c in COMPONENTS}
COMPONENT_FAMILY: dict[str, str] = {c.key: c.family for c in COMPONENTS}

# Flags específicas das três melhorias documentadas do G5 Passione.
RETROFIT_PATTERNS: dict[str, re.Pattern[str]] = {
    "fez_adaptacao_hidraulica": _rx(r"adapta"),
    "trocou_oring_anel": _rx(r"o-?ring|anel"),
    "mexeu_bandeja": _rx(r"bandeja"),
}

# Causas que "explicam" cada sintoma relatado pelo consumidor. Usado para
# medir a concordância entre as duas vozes do chamado. Construído a partir
# do conhecimento de engenharia sobre a máquina de cápsulas; revisar com P&D.
_HYDRAULIC = {"bomba", "contador_volumetrico", "vedacao_oring",
              "conexoes_hidraulicas", "bico_saida", "pino_ceramico"}
EXPECTED_CAUSES: dict[str, set[str]] = {
    "Máquina vazando": {"vedacao_oring", "conexoes_hidraulicas", "bandeja",
                        "unidade_extracao", "bomba", "termobloco"},
    "Bico entupido": {"bico_saida", "pino_ceramico", "higienizacao",
                      "unidade_extracao"},
    "Máquina não puxa água": _HYDRAULIC | {"higienizacao"},
    "Não extrai": _HYDRAULIC | {"unidade_extracao", "higienizacao"},
    "Máquina não liga": {"placa_eletronica", "termobloco"},
    "Botões piscando/Luz acesa": {"placa_eletronica", "termobloco"},
    "Painel não responde aos comandos": {"placa_eletronica"},
    "Voltagem errada": {"placa_eletronica", "termobloco"},
    "Máquina em curto/Saindo fumaça": {"placa_eletronica", "termobloco"},
    "Infestação": {"fauna", "higienizacao"},
    "Alavanca travada": {"alavanca", "unidade_extracao"},
    "Alavanca danificada": {"alavanca", "unidade_extracao"},
    "Bebida não esta suficientemente quente": {"termobloco",
                                               "placa_eletronica"},
}


def find_components(text: str) -> list[str]:
    """Lista os componentes citados no texto, em ordem de prioridade.

    Args:
        text: Texto já sem acentos e em minúsculas.

    Returns:
        Lista de ``Component.key`` (pode ser vazia).
    """
    found = [c for c in COMPONENTS if c.pattern.search(text)]
    return [c.key for c in sorted(found, key=lambda c: c.priority)]


def classify_repairs(df: pd.DataFrame) -> pd.DataFrame:
    """Enriquece a base com a leitura estruturada da voz do técnico.

    Concatena ``motivo`` + ``conclusao`` (o motivo padronizado ajuda quando
    a conclusão está vazia) e extrai componentes, causa principal, família
    e flags de melhorias de campo.

    Args:
        df: DataFrame canônico (após :mod:`dna_maquina.ingest`).

    Returns:
        Cópia do DataFrame com as novas colunas:
        ``componentes``, ``causa_principal``, ``causa_label``,
        ``familia_tecnica``, ``tem_reparo_registrado`` e as flags de
        :data:`RETROFIT_PATTERNS`.
    """
    out = df.copy()
    text = (out["motivo"].map(strip_accents) + " | "
            + out["conclusao"].map(strip_accents))
    out["tem_reparo_registrado"] = (
        out["conclusao"].notna() | out["motivo"].notna()
    )

    out["componentes"] = text.map(find_components)
    out["causa_principal"] = out["componentes"].map(
        lambda keys: keys[0] if keys else None
    )
    # Laudo "NENHUM DEFEITO" sem nenhum componente citado => sem defeito.
    no_defect = (out["causa_principal"].isna()
                 & out["laudo"].fillna("").str.upper().eq("NENHUM DEFEITO"))
    out.loc[no_defect, "causa_principal"] = "sem_defeito"
    out.loc[~out["tem_reparo_registrado"], "causa_principal"] = None
    out["causa_principal"] = out["causa_principal"].fillna(
        out["tem_reparo_registrado"].map(
            {True: "outros", False: "sem_registro"})
    )

    labels = {**COMPONENT_LABELS, "outros": "Outros / não identificado",
              "sem_registro": "Sem registro técnico"}
    families = {**COMPONENT_FAMILY, "outros": "Outros",
                "sem_registro": "Sem registro"}
    out["causa_label"] = out["causa_principal"].map(labels)
    out["familia_tecnica"] = out["causa_principal"].map(families)

    raw_conclusion = out["conclusao"].map(strip_accents)
    for flag, pattern in RETROFIT_PATTERNS.items():
        out[flag] = raw_conclusion.str.contains(pattern)
    return out


def voices_agree(symptom: str, components: list[str]) -> bool | None:
    """Indica se a voz do técnico "explica" a voz do consumidor.

    Args:
        symptom: Sintoma relatado (``sintoma_cs``).
        components: Componentes encontrados no reparo.

    Returns:
        ``True``/``False`` quando há regra para o sintoma; ``None`` quando
        o sintoma não tem causas esperadas mapeadas (não avaliado).
    """
    expected = EXPECTED_CAUSES.get(symptom)
    if expected is None or not components:
        return None
    return bool(expected.intersection(components))
