"""
Identificar padrões: IA que lê o texto livre dos técnicos.

Por que este módulo existe
--------------------------
A taxonomia por regras (:mod:`dna_maquina.taxonomy`) só encontra o que
alguém já sabia procurar. O desafio aponta exatamente essa dor: "só se vê
o que se procura". Aqui um modelo NÃO supervisionado lê ~24 mil conclusões
técnicas e agrupa sozinho os modos de falha que se repetem — inclusive os
que não estão em nenhuma regra (ex.: "bomba colada" aparece como grupo
próprio, com centenas de casos no G5 e no G4).

Método (explicável para a engenharia)
-------------------------------------
1. Texto normalizado (sem acento, minúsculo) e sem palavras de rotina
   ("teste", "cápsula", "realizado"…) que aparecem em quase todo laudo;
2. TF-IDF de palavras e pares de palavras: destaca o que é característico
   de cada laudo;
3. NMF (fatoração de matriz não negativa): cada "tema" é uma combinação
   de termos; cada laudo recebe o tema dominante. Os termos de maior peso
   NOMEIAM o tema — a engenharia lê e valida.
4. Cruzamento tema × modelo × mês: mostra onde e quando cada modo de falha
   cresce.

Privacidade: termos que aparecem em poucos laudos (``min_df``) são
descartados, o que também remove nomes próprios digitados pelos técnicos.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from dna_maquina.taxonomy import strip_accents

N_TOPICS = 12
MIN_DOCS_PER_TERM = 20
TOP_TERMS = 8
RANDOM_STATE = 0

ROUTINE_WORDS = (
    "de da do das dos e a o as os com para em no na nos nas foi feito "
    "feita realizado realizada realizados efetuado efetuados efetuada "
    "maquina maq equipamento teste testes capsula capsulas cliente um uma "
    "ao se por que reset ok liberada funcionando apos isso"
).split()


@dataclass
class FailureModes:
    """Resultado da descoberta de modos de falha no texto."""

    temas: pd.DataFrame        # id, nome, termos, chamados
    atribuicao: pd.Series      # tema dominante por chamado (índice da base)
    por_modelo: pd.DataFrame   # % de cada tema por modelo
    por_mes: pd.DataFrame      # chamados por tema e mês


def discover_failure_modes(df: pd.DataFrame,
                           n_topics: int = N_TOPICS) -> FailureModes:
    """Descobre modos de falha no texto das conclusões técnicas.

    Args:
        df: Base enriquecida (usa ``conclusao``, ``modelo`` e ``mes``).
        n_topics: Número de temas a extrair.

    Returns:
        :class:`FailureModes` com os temas e os cruzamentos.
    """
    data = df[df["conclusao"].notna()]
    text = data["conclusao"].map(strip_accents)
    vectorizer = TfidfVectorizer(
        stop_words=ROUTINE_WORDS, ngram_range=(1, 2),
        min_df=MIN_DOCS_PER_TERM, max_df=0.5,
        token_pattern=r"(?u)\b[a-z]{3,}\b")
    matrix = vectorizer.fit_transform(text)
    nmf = NMF(n_components=n_topics, init="nndsvda", max_iter=400,
              random_state=RANDOM_STATE)
    weights = nmf.fit_transform(matrix)
    terms = np.array(vectorizer.get_feature_names_out())

    assignment = pd.Series(weights.argmax(axis=1), index=data.index,
                           name="tema")
    rows = []
    for topic, components in enumerate(nmf.components_):
        top = terms[np.argsort(-components)[:TOP_TERMS]]
        rows.append({"tema": topic, "nome": _topic_name(top),
                     "termos": ", ".join(top),
                     "chamados": int((assignment == topic).sum())})
    topics = pd.DataFrame(rows).sort_values("chamados", ascending=False)

    names = topics.set_index("tema")["nome"]
    labeled = data.assign(tema=assignment.map(names))
    by_model = pd.crosstab(labeled["tema"], labeled["modelo"],
                           normalize="columns")
    by_month = labeled.groupby(["mes", "tema"]).size().unstack(fill_value=0)
    return FailureModes(topics.reset_index(drop=True), assignment,
                        by_model, by_month)


def _topic_name(top_terms: np.ndarray) -> str:
    """Nome legível do tema: os dois termos mais fortes e distintos.

    Pares de palavras que repetem um termo já usado são pulados, para não
    gerar nomes como "bomba / bomba colada".
    """
    chosen: list[str] = []
    for term in top_terms:
        words = set(term.split())
        if any(words & set(c.split()) for c in chosen):
            continue
        chosen.append(term)
        if len(chosen) == 2:
            break
    return " / ".join(chosen)


def emerging_topics(modes: FailureModes, model_share: pd.DataFrame | None
                    = None, recent_months: int = 3) -> pd.DataFrame:
    """Temas cuja participação cresceu nos últimos meses.

    Compara a fatia do tema nos ``recent_months`` mais recentes com a fatia
    no período anterior (pontos percentuais).
    """
    by_month = modes.por_mes
    share = by_month.div(by_month.sum(axis=1), axis=0)
    recent = share.tail(recent_months).mean()
    before = share.iloc[:-recent_months].mean()
    table = pd.DataFrame({"antes": before, "recente": recent})
    table["variacao_pp"] = (table["recente"] - table["antes"]) * 100
    return table.sort_values("variacao_pp", ascending=False)


_BULLETIN_SUBJECT = (r"boletim\s+tecnico\s+(?:(?:d[aoe]s?|n[aoe]s?|para|"
                     r"referente\s+(?:a|ao))\s+)?(?:(?:a|o)\s+)?([a-z]{4,})")
_GENERIC_WORDS = {"maquina", "equipamento", "para", "referente", "parte",
                  "sistema"}


def bulletin_mentions(df: pd.DataFrame) -> pd.DataFrame:
    """Boletins técnicos citados pelos técnicos no texto livre.

    Descoberta da análise de texto: técnicos escrevem "feito boletim
    técnico do bico", "boletim técnico na câmara"… Muitos desses boletins
    NÃO estão no diretório de melhorias fornecido. Listá-los mostra ao P&D
    quais melhorias de campo estão em uso e ainda não são medidas.

    Returns:
        Tabela modelo × assunto do boletim com nº de citações, primeiro e
        último mês em que aparecem.
    """
    text = df["conclusao"].map(strip_accents)
    mentions = df[text.str.contains("boletim", regex=False)].copy()
    subject = text[mentions.index].str.extract(_BULLETIN_SUBJECT)[0]
    mentions["assunto"] = subject.where(~subject.isin(_GENERIC_WORDS))
    mentions["assunto"] = mentions["assunto"].fillna("(não especificado)")
    table = mentions.groupby(["modelo", "assunto"]).agg(
        citacoes=("case_id", "size"), primeiro_mes=("mes", "min"),
        ultimo_mes=("mes", "max"))
    return table.sort_values("citacoes", ascending=False).reset_index()
