"""
Apoiar decisões de engenharia: as análises viram FERRAMENTAS para a Cora.

Pergunta de negócio
-------------------
Dor 06 do P&D: "cada pergunta exige extrair, limpar e montar gráfico à
mão — minutos ou dias". Aqui a engenheira pergunta em português ("a
bandeja funcionou?", "o que está crescendo no Luna?") e recebe a
resposta COM as evidências, em segundos.

Arquitetura (a conversa é da Cora, os números são daqui)
--------------------------------------------------------
* A **Cora** (plataforma corporativa de IA do Grupo 3corações) conduz a
  conversa: ela tem o modelo de linguagem, o histórico, o login e o
  controle de acesso (RBAC). Este projeto NÃO chama mais nenhum modelo
  de linguagem para o assistente.
* Cada análise já testada do projeto (impacto de melhoria, DNA, radar,
  duas vozes, modos de falha…) é uma FERRAMENTA desta classe
  :class:`Toolbox`. O servidor MCP do backend
  (``backend/app/mcp_server.py``) publica essas ferramentas e a Cora as
  chama quando a pergunta precisa de dados de campo.
* O modelo da Cora NÃO calcula nada: escolhe a ferramenta, recebe os
  números em JSON e redige. Os números são do código, não do modelo
  (anti-alucinação por construção), e a Cora mostra quais ferramentas
  usou (rastreabilidade para a banca e para a engenharia).
* **Sem a Cora** (rede, demo offline): as perguntas prontas
  (:data:`PRESETS`) e o parecer técnico (:func:`decision_memo`) saem por
  texto-modelo, chamando as mesmas ferramentas.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from dna_maquina import analytics, history, impact

SIGNIFICANCE = 0.05
"""Nível de significância dos vereditos por regras."""

TOOL_GUIDE = (
    "Ferramentas de dados de campo das máquinas de café TRES (G5 Passione "
    "e G4 Luna), calculadas sobre os chamados reais de assistência "
    "técnica. Regras para quem usa: (1) responda só com os números que a "
    "ferramenta devolver; (2) nunca invente números, peças, datas ou "
    "causas — se a ferramenta não trouxer a informação, diga que os dados "
    "não permitem responder; (3) cite a ressalva quando houver (indicador "
    "de mix, não taxa de falha; leitura do número de série a confirmar "
    "com o P&D)."
)
"""Orientação enviada à Cora junto com o catálogo de ferramentas (MCP)."""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _key(key: Any) -> str:
    """Chave de dicionário legível: datas viram AAAA-MM-DD."""
    if isinstance(key, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(key).date())
    return str(key)


def _jsonable(value: Any) -> Any:
    """Converte tipos numpy/pandas em tipos JSON simples (recursivo)."""
    if isinstance(value, dict):
        return {_key(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, pd.DataFrame):
        return _jsonable(value.reset_index().to_dict("records"))
    if isinstance(value, pd.Series):
        return _jsonable(value.to_dict())
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value).date())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if math.isnan(value):
            return None
        # Números muito pequenos (p-valores) mantêm 3 algarismos
        # significativos; o resto é arredondado em 4 casas.
        return (float(f"{value:.3g}") if 0 < abs(value) < 1e-3
                else round(float(value), 4))
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value




# ---------------------------------------------------------------------------
# Ferramentas: funções do projeto expostas à Cora (via MCP)
# ---------------------------------------------------------------------------
@dataclass
class Tool:
    """Ferramenta do catálogo: nome, descrição, esquema e função."""

    name: str
    description: str
    schema: dict
    run: Callable[..., Any]


@dataclass
class Toolbox:
    """Conjunto de ferramentas sobre UMA base de dados já enriquecida."""

    df: pd.DataFrame
    _cache: dict = field(default_factory=dict)

    # -- ferramentas ---------------------------------------------------
    def listar_melhorias(self) -> list[dict]:
        return [{"id": i.id, "titulo": i.titulo, "modelo": i.modelo,
                 "data": i.data_documento, "tipo": i.tipo,
                 "objetivo": i.objetivo}
                for i in impact.load_improvements()]

    def listar_sintomas(self) -> dict:
        """Sintomas exatamente como o atendimento os registra.

        As ferramentas que filtram por sintoma exigem o texto exato;
        esta lista evita que o modelo adivinhe a grafia.
        """
        counts = self.df["sintoma_cs"].value_counts()
        return {"sintomas": counts}

    def avaliar_melhoria(self, id_melhoria: str) -> dict:
        items = {i.id: i for i in impact.load_improvements()}
        if id_melhoria not in items:
            return {"erro": f"melhoria inexistente; ids: {list(items)}"}
        result = impact.evaluate(self.df, items[id_melhoria])
        return {"melhoria": items[id_melhoria].titulo,
                "indicador": result.indicador,
                "grupos": result.tabela[["n", "eventos", "taxa", "ic_inf",
                                         "ic_sup", "maquinas"]],
                "reducao_relativa": result.reducao_relativa,
                "p_valor": float(f"{result.p_valor:.3g}"),
                "premissas": result.notas}

    def historico_maquina(self, serie: str) -> dict:
        from dna_maquina.llm import build_machine_facts

        facts = build_machine_facts(self.df, serie,
                                    impact.load_improvements())
        return {"fatos": facts or "série não encontrada"}

    def contar_chamados(self, modelo: str | None = None,
                        sintoma: str | None = None,
                        ano_fabricacao: int | None = None,
                        mes_inicio: str | None = None,
                        mes_fim: str | None = None) -> dict:
        data = self.df
        if modelo:
            data = data[data["modelo"] == modelo]
        if sintoma:
            data = data[data["sintoma_cs"] == sintoma]
        if ano_fabricacao:
            data = data[data["ano_fab"] == ano_fabricacao]
        if mes_inicio:
            data = data[data["mes"] >= pd.Timestamp(mes_inicio)]
        if mes_fim:
            data = data[data["mes"] <= pd.Timestamp(mes_fim)]
        return {"chamados": len(data), "maquinas": data["serie"].nunique(),
                "fracao_da_base": len(data) / len(self.df),
                "por_mes": data.groupby("mes").size().tail(12),
                "top_causas": data["causa_label"].value_counts(
                    normalize=True).head(5)}

    def duas_vozes(self, sintoma: str) -> dict:
        data = self.df[(self.df["sintoma_cs"] == sintoma)
                       & self.df["tem_reparo_registrado"]]
        if data.empty:
            return {"erro": "sintoma sem chamados com registro técnico"}
        agree = data["vozes_concordam"].dropna()
        return {"chamados": len(data),
                "causas_encontradas": data["causa_label"].value_counts(
                    normalize=True).head(6),
                "concordancia": agree.astype(bool).mean()
                if len(agree) else None}

    def radar(self, n: int = 5) -> dict:
        alerts = analytics.radar(self.df).head(n)
        return {"alertas": alerts[["modelo", "sintoma_cs", "causa_label",
                                   "media_base", "media_recente",
                                   "variacao_pct"]]}

    def modos_de_falha(self) -> dict:
        from dna_maquina import patterns

        if "modes" not in self._cache:
            self._cache["modes"] = patterns.discover_failure_modes(self.df)
        modes = self._cache["modes"]
        return {"temas": modes.temas[["nome", "termos", "chamados"]],
                "fatia_por_modelo": modes.por_modelo.round(3),
                "temas_em_alta": patterns.emerging_topics(modes).head(3),
                "boletins_citados_no_texto": patterns.bulletin_mentions(
                    self.df).head(6)}

    def maquinas_cronicas(self, n: int = 10) -> dict:
        summary = history.machine_summary(self.df)
        return {"total_cronicas": int(summary["cronica"].sum()),
                "top": summary.head(n)[["modelo", "chamados", "vazamentos",
                                        "reincidencias",
                                        "sintoma_mais_comum"]]}

    def qualidade_dos_dados(self) -> dict:
        from dna_maquina import reliability

        scores = reliability.machine_confidence(self.df)
        return {"series_invalidas": int((~self.df["valida"]).sum()),
                "sem_registro_tecnico": (~self.df["tem_reparo_registrado"]
                                         ).mean(),
                "confiabilidade_media_dna": scores.mean(),
                "maquinas_confiabilidade_alta": (scores >= 85).mean()}

    # -- catálogo ------------------------------------------------------
    def tools(self) -> list[Tool]:
        """Lista de ferramentas com descrições em português para o LLM."""
        symptoms = sorted(self.df["sintoma_cs"].dropna().unique().tolist())
        obj = {"type": "object", "properties": {}, "required": []}
        return [
            Tool("listar_melhorias", "Lista as melhorias de engenharia "
                 "cadastradas (boletins), com id, modelo e data.", obj,
                 self.listar_melhorias),
            Tool("listar_sintomas", "Sintomas relatados pelo consumidor, "
                 "com a grafia exata e o número de chamados de cada um.",
                 obj, self.listar_sintomas),
            Tool("avaliar_melhoria", "Mede se uma melhoria funcionou: antes "
                 "x depois, intervalo de confiança, p-valor e premissas.",
                 {"type": "object", "properties": {"id_melhoria": {
                     "type": "string", "description": "id da melhoria"}},
                  "required": ["id_melhoria"]}, self.avaliar_melhoria),
            Tool("historico_maquina", "Histórico (DNA) de uma máquina pelo "
                 "número de série.", {"type": "object", "properties": {
                     "serie": {"type": "string"}}, "required": ["serie"]},
                 self.historico_maquina),
            Tool("contar_chamados", "Conta chamados com filtros opcionais "
                 "(modelo Passione/Luna, sintoma, ano de fabricação, meses "
                 "AAAA-MM-01) e mostra a evolução mensal e as causas.",
                 {"type": "object", "properties": {
                     "modelo": {"type": "string", "enum": ["Passione",
                                                           "Luna"]},
                     "sintoma": {"type": "string", "enum": symptoms},
                     "ano_fabricacao": {"type": "integer"},
                     "mes_inicio": {"type": "string"},
                     "mes_fim": {"type": "string"}}, "required": []},
                 self.contar_chamados),
            Tool("duas_vozes", "Para um sintoma relatado pelo consumidor, "
                 "mostra o que o técnico de fato encontrou.",
                 {"type": "object", "properties": {"sintoma": {
                     "type": "string", "enum": symptoms}},
                  "required": ["sintoma"]}, self.duas_vozes),
            Tool("radar", "Combinações modelo x sintoma x causa que mais "
                 "cresceram nos últimos 3 meses.", obj, self.radar),
            Tool("modos_de_falha", "Modos de falha descobertos por IA no "
                 "texto dos técnicos, temas em alta e boletins citados.",
                 obj, self.modos_de_falha),
            Tool("maquinas_cronicas", "Máquinas com 3 ou mais chamados.",
                 obj, self.maquinas_cronicas),
            Tool("qualidade_dos_dados", "Confiabilidade da base: séries "
                 "inválidas, chamados sem laudo, nota do DNA.", obj,
                 self.qualidade_dos_dados),
        ]

    def run(self, name: str, arguments: dict) -> Any:
        """Executa uma ferramenta pelo nome; erros viram mensagem (o agente
        lê o erro e pode tentar de novo, em vez de a tela quebrar)."""
        tool = {t.name: t for t in self.tools()}.get(name)
        if tool is None:
            return {"erro": f"ferramenta desconhecida: {name}"}
        try:
            return _jsonable(tool.run(**(arguments or {})))
        except Exception as error:  # noqa: BLE001 — devolvido ao agente
            return {"erro": str(error)}


# ---------------------------------------------------------------------------
# Perguntas prontas (funcionam sem IA — plano B da demo)
# ---------------------------------------------------------------------------
PRESETS: dict[str, tuple[str, dict]] = {
    "A melhoria da bandeja de cápsulas funcionou?":
        ("avaliar_melhoria", {"id_melhoria": "G5-BANDEJA-2022"}),
    "O kit de adaptação hidráulica funcionou?":
        ("avaliar_melhoria", {"id_melhoria": "G5-ADAPT-HIDR-2022"}),
    "O que o técnico encontra quando o consumidor diz 'Máquina vazando'?":
        ("duas_vozes", {"sintoma": "Máquina vazando"}),
    "O que está crescendo nos últimos 3 meses?": ("radar", {}),
    "Que modos de falha a IA encontrou no texto dos técnicos?":
        ("modos_de_falha", {}),
    "Quão confiável é a base de dados?": ("qualidade_dos_dados", {}),
}


def answer_preset(df: pd.DataFrame, question: str) -> tuple[str, Any]:
    """Responde uma pergunta pronta sem LLM: ferramenta + texto-modelo.

    Returns:
        (texto curto, resultado bruto da ferramenta para exibir em tabela).
    """
    name, args = PRESETS[question]
    result = Toolbox(df).run(name, args)
    return _template(name, result), result


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%".replace(".", ",")


def _p_text(p_value: float | None) -> str:
    """p-valor legível: 'p < 0,001' ou 'p = 0,91'."""
    if p_value is None:
        return "p indisponível"
    if p_value < 0.001:
        return "p < 0,001"
    return f"p = {p_value:.2f}".replace(".", ",")


def _verdict(result: dict) -> str:
    """Veredito honesto: sem p-valor (amostra pequena) não há conclusão."""
    p_value, reduction = result.get("p_valor"), result.get("reducao_relativa")
    if p_value is None or reduction is None:
        return "amostra insuficiente"
    if p_value < SIGNIFICANCE and reduction > 0:
        return "funcionou"
    return "não teve efeito mensurável"


def _template(name: str, result: dict) -> str:
    """Texto-modelo por ferramenta (quando o LLM não está disponível)."""
    if "erro" in result:
        return result["erro"]
    if name == "avaliar_melhoria":
        groups = result["grupos"]
        before, after = groups[0], groups[1]
        verdict = _verdict(result)
        return (f"{result['melhoria']}: {verdict}. {result['indicador']}: "
                f"{_pct(before['taxa'])} → {_pct(after['taxa'])} "
                f"({_p_text(result['p_valor'])}).")
    if name == "duas_vozes":
        causes = result["causas_encontradas"]
        top = ", ".join(f"{k} {_pct(v)}" for k, v in list(causes.items())[:3])
        return (f"Em {result['chamados']} chamados, o técnico encontrou: "
                f"{top}. Concordância com o sintoma: "
                f"{_pct(result['concordancia'])}.")
    if name == "radar":
        first = result["alertas"][0]
        return (f"Maior alta: {first['modelo']} · {first['sintoma_cs']} · "
                f"{first['causa_label']} ({first['media_base']:.1f} → "
                f"{first['media_recente']:.1f} chamados/mês).")
    if name == "modos_de_falha":
        names = ", ".join(t["nome"] for t in result["temas"][:5])
        return (f"Principais modos de falha no texto: {names}. Veja também "
                f"os boletins citados pelos técnicos.")
    if name == "qualidade_dos_dados":
        return (f"{result['series_invalidas']} séries inválidas; "
                f"{_pct(result['sem_registro_tecnico'])} dos chamados sem "
                f"laudo; nota média do DNA "
                f"{result['confiabilidade_media_dna']:.0f}/100.")
    return "Resultado abaixo."



# ---------------------------------------------------------------------------
# Parecer técnico para o P&D (por regras; a Cora redige a versão livre)
# ---------------------------------------------------------------------------
def decision_memo(df: pd.DataFrame, improvement_id: str) -> str:
    """Parecer de uma página sobre uma melhoria, por texto-modelo.

    O texto é determinístico: os mesmos fatos geram o mesmo parecer.
    Para um parecer redigido livremente, a engenharia pede à Cora, que
    chama a ferramenta ``dna_parecer_tecnico`` e parte destes fatos.
    """
    return memo_template(Toolbox(df).avaliar_melhoria(improvement_id))


def memo_template(facts: dict) -> str:
    """Parecer: decisão, evidência, ressalvas e próximo passo."""
    if "erro" in facts:
        return facts["erro"]
    data = _jsonable(facts)
    before, after = data["grupos"][0], data["grupos"][1]
    decision = {
        "funcionou": "Manter a melhoria e usá-la como referência para o "
                     "próximo projeto.",
        "não teve efeito mensurável": "Rever a melhoria: não há efeito "
                                      "mensurável em campo; investigar o "
                                      "modo de falha antes de novo "
                                      "investimento.",
        "amostra insuficiente": "Ainda não decidir: a amostra não permite "
                                "testar o efeito; acompanhar até haver "
                                "chamados suficientes nos dois grupos.",
    }[_verdict(data)]
    return (f"Decisão de engenharia recomendada: {decision}\n\n"
            f"Evidência: {data['indicador']} passou de "
            f"{_pct(before['taxa'])} (n={before['n']:.0f}) para "
            f"{_pct(after['taxa'])} (n={after['n']:.0f}); redução relativa "
            f"de {_pct(data['reducao_relativa'])}; "
            f"{_p_text(data['p_valor'])}.\n\n"
            "Ressalvas: " + " ".join(data["premissas"]) + "\n\n"
            "Próximo passo: confirmar com a base instalada por série para "
            "medir a taxa de falha por 1.000 máquinas.")


def main(questions: list[str]) -> None:
    """CLI: responde as perguntas prontas por regras (sem IA)."""
    from dna_maquina.pipeline import load_processed

    df = load_processed()
    for question in questions or list(PRESETS):
        text, _ = answer_preset(df, question)
        print(f"\n{question}\n{text}")


if __name__ == "__main__":
    main(sys.argv[1:])
