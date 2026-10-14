"""
DNA da Máquina — protótipo Streamlit (Cafeína Week 2026, Desafio TRES).

Como rodar::

    pip install -r requirements.txt
    streamlit run app/streamlit_app.py

O app lê ``data/processed/chamados.parquet``; se não existir, processa
automaticamente as planilhas de ``data/raw``. Cada página responde a uma
dor do P&D e a uma persona do desafio:

=====================  ==========================  ======================
Página                 Dor do P&D                  Persona principal
=====================  ==========================  ======================
Visão geral            06 (dados lentos)           Marina (P&D)
DNA da máquina         07 (sem histórico)          Carlos, Rafael
Melhoria × impacto     04 (melhoria × impacto)     Marina (P&D)
Duas vozes             05 (histórias diferentes)   Rafael, Marina
Radar                  03 (problemas despercebidos) Marina
Importar base          06 (diferencial .xlsx)      Marina
=====================  ==========================  ======================
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Permite rodar sem instalar o pacote (``streamlit run`` a partir da raiz).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dna_maquina import (  # noqa: E402
    analytics,
    assistant,
    config,
    history,
    impact,
    llm,
    patterns,
    reliability,
    risk,
)
from dna_maquina.ingest import (  # noqa: E402
    SchemaError,
    clean_complaints,
    merge_bases,
)
from dna_maquina.pipeline import enrich, load_processed, save  # noqa: E402

# ---------------------------------------------------------------------------
# Identidade visual (tokens alinhados ao guia de design da equipe)
# ---------------------------------------------------------------------------
COFFEE = "#6B3E26"
CREMA = "#C8893B"
ALERT = "#C2410C"
OK = "#2F7D4F"
NEUTRAL = "#8A8178"
PLOT_TEMPLATE = "simple_white"

st.set_page_config(page_title="DNA da Máquina", page_icon="☕",
                   layout="wide")


# Funções cacheadas recebem "_df" (sublinhado): o Streamlit não tenta
# fazer hash da base inteira; o cache é limpo ao importar nova base.
@st.cache_data(show_spinner="Carregando e enriquecendo a base…")
def get_data() -> pd.DataFrame:
    """Carrega a base enriquecida uma única vez por sessão (cache)."""
    return load_processed()


@st.cache_data(show_spinner="Montando o DNA de cada máquina…")
def get_summary(_df: pd.DataFrame) -> pd.DataFrame:
    """Ficha resumida por máquina (cacheada: ~20 mil séries)."""
    return history.machine_summary(_df)


@st.cache_data(show_spinner="Varrendo combinações…")
def get_radar(_df: pd.DataFrame) -> pd.DataFrame:
    """Alertas do radar (cacheados enquanto a base não mudar)."""
    return analytics.radar(_df)


@st.cache_resource(show_spinner="Carregando o modelo de risco…")
def get_risk_model():
    """Modelo de risco treinado (treina na hora se ainda não existir)."""
    loaded = risk.load()
    if loaded is None:
        model, metrics = risk.train_and_evaluate(get_data())
        risk.save(model, metrics)
        loaded = risk.load()
    return loaded


@st.cache_data(show_spinner="Calculando o risco de cada chamado…")
def get_risk_scores(_df: pd.DataFrame) -> pd.Series:
    """Probabilidade de retorno em 90 dias por chamado (cacheada)."""
    model, _ = get_risk_model()
    return risk.score_cases(model, _df)


@st.cache_resource(show_spinner="Treinando o modelo de causa provável…")
def get_cause_model():
    """Modelo de causa provável (treina na hora se ainda não existir)."""
    loaded = reliability.load_cause_model()
    if loaded is None:
        model, metrics = reliability.train_cause_model(get_data())
        reliability.save_cause_model(model, metrics)
        loaded = reliability.load_cause_model()
    return loaded


@st.cache_data(show_spinner="A IA está lendo os textos dos técnicos…")
def get_failure_modes(_df: pd.DataFrame):
    """Modos de falha descobertos no texto (TF-IDF + NMF), cacheados."""
    return patterns.discover_failure_modes(_df)


@st.cache_data(show_spinner=False)
def get_machine_confidence(_df: pd.DataFrame) -> pd.Series:
    """Nota de confiabilidade do DNA por máquina (0–100)."""
    return reliability.machine_confidence(_df)


def pct(value: float, digits: int = 1) -> str:
    """Formata proporção como porcentagem no padrão brasileiro."""
    if pd.isna(value):
        return "—"
    return f"{value * 100:.{digits}f}%".replace(".", ",")


def fmt_int(value: float) -> str:
    """Formata inteiro com separador de milhar brasileiro."""
    return f"{int(value):,}".replace(",", ".")


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
def page_overview(df: pd.DataFrame) -> None:
    """Visão geral: o retrato da base em segundos, não em dias."""
    st.title("Visão geral")
    st.caption("Antes: extrair do Salesforce, limpar e montar gráficos à mão "
               "a cada pergunta. Agora: as respostas já estão aqui.")

    models = st.multiselect("Modelo", sorted(df["modelo"].dropna().unique()),
                            default=["Passione", "Luna"])
    data = df[df["modelo"].isin(models)]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Chamados", fmt_int(len(data)))
    c2.metric("Máquinas com chamado", fmt_int(data["serie"].nunique()))
    c3.metric("Voltaram em até 90 dias", pct(data["reincidente"].mean()),
              help="Chamado aberto até 90 dias depois de outro da mesma "
                   "máquina.")
    c4.metric("Sem registro técnico", pct((~data["tem_reparo_registrado"])
                                          .mean()),
              help="Chamados sem laudo/conclusão do técnico.")

    left, right = st.columns([3, 2])
    monthly = data.groupby(["mes", "modelo"]).size().reset_index(name="n")
    fig = px.line(monthly, x="mes", y="n", color="modelo", markers=True,
                  template=PLOT_TEMPLATE,
                  color_discrete_sequence=[COFFEE, CREMA],
                  labels={"mes": "Mês de abertura", "n": "Chamados"},
                  title="Chamados por mês")
    left.plotly_chart(fig, width="stretch")

    top = data["sintoma_cs"].value_counts().head(10).sort_values()
    fig = px.bar(top, orientation="h", template=PLOT_TEMPLATE,
                 color_discrete_sequence=[COFFEE],
                 labels={"value": "Chamados", "sintoma_cs": ""},
                 title="Top 10 sintomas relatados")
    fig.update_layout(showlegend=False)
    right.plotly_chart(fig, width="stretch")

    causes = (data[data["tem_reparo_registrado"]]["causa_label"]
              .value_counts().head(12).sort_values())
    fig = px.bar(causes, orientation="h", template=PLOT_TEMPLATE,
                 color_discrete_sequence=[CREMA],
                 labels={"value": "Chamados", "causa_label": ""},
                 title="O que o técnico encontrou (causa principal)")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")


def page_machine(df: pd.DataFrame) -> None:
    """DNA da máquina: ficha + linha do tempo de uma série."""
    st.title("DNA da máquina")
    st.caption("Para o técnico consultar antes de sair e para o CS saber, "
               "durante a ligação, se a máquina já teve o mesmo problema.")

    summary = get_summary(df)
    chronic = summary[summary["cronica"]]
    st.write(f"**{fmt_int(len(chronic))} máquinas crônicas** "
             f"(3 ou mais chamados no período).")

    # Abre na máquina com mais vazamentos: a "Juliana" do desafio.
    ranked = summary.sort_values(["vazamentos", "chamados"])
    default = ranked.index[-1] if len(ranked) else ""
    serial = st.text_input("Número de série", value=default,
                           help="Aceita minúsculas e espaços.")
    timeline = history.machine_timeline(df, serial)
    if timeline.empty:
        st.warning("Série não encontrada na base.")
    else:
        from dna_maquina.serial import parse_serial

        info = parse_serial(serial)
        row = summary.loc[info.serie]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Modelo", row["modelo"])
        c2.metric("Fabricação", f"{int(row['ano_fab'])} · S"
                  f"{int(row['semana_fab']):02d}")
        c3.metric("Chamados", int(row["chamados"]))
        c4.metric("Voltas em 90 dias", int(row["reincidencias"]))
        c5.metric("Recebeu adaptação hidráulica",
                  "Sim" if row["recebeu_adaptacao"] else "Não")

        _render_improvement_status(info.serie, df)
        _render_ai_summary(info.serie, df)
        _render_confidence(info.serie, df)

        fig = px.scatter(timeline, x="data_abertura", y="sintoma_cs",
                         color="causa_label", template=PLOT_TEMPLATE,
                         hover_data=["conclusao"], height=320,
                         labels={"data_abertura": "", "sintoma_cs": "",
                                 "causa_label": "Causa (técnico)"},
                         title="Linha do tempo")
        fig.update_traces(marker={"size": 16})
        st.plotly_chart(fig, width="stretch")
        shown = timeline.assign(
            data_abertura=timeline["data_abertura"].dt.strftime("%d/%m/%Y"))
        st.dataframe(shown.rename(columns={
            "data_abertura": "Abertura", "case_id": "Caso",
            "sintoma_cs": "Consumidor disse", "laudo": "Laudo",
            "motivo": "Motivo técnico", "causa_label": "Causa (leitura)",
            "conclusao": "Técnico escreveu",
            "dias_desde_anterior": "Dias desde anterior",
            "reincidente": "Voltou?", "vozes_concordam": "Vozes batem?",
            "fez_adaptacao_hidraulica": "Adaptação?"}),
            width="stretch", hide_index=True)

    with st.expander("Ranking de máquinas crônicas"):
        st.dataframe(chronic.head(200), width="stretch")


def _render_confidence(serial: str, df: pd.DataFrame) -> None:
    """Nota de confiabilidade do DNA e causa provável (IA) sem laudo."""
    score = get_machine_confidence(df).get(serial)
    if score is None:
        return
    rows = df[df["serie"] == serial]
    missing = rows[~rows["tem_reparo_registrado"]]
    left, right = st.columns([1, 3])
    left.metric("Confiabilidade do DNA",
                f"{score:.0f}/100 · {reliability.confidence_label(score)}",
                help="Série válida (30), laudo registrado (30), datas "
                     "coerentes (15), vozes concordam (15), instalação "
                     "plausível (10).")
    if len(missing):
        model, metrics = get_cause_model()
        guesses = reliability.probable_causes(model, df).loc[missing.index]
        right.markdown(
            f"**Causa provável (IA) nos {len(missing)} chamados sem laudo** "
            f"— acerta entre as 3 sugestões em "
            f"{pct(metrics['acerto_top3'], 0)} dos casos (teste 2026).")
        right.dataframe(pd.DataFrame({
            "Abertura": missing["data_abertura"].dt.strftime("%d/%m/%Y"),
            "Consumidor disse": missing["sintoma_cs"],
            "Causa provável (IA)": guesses["causa_provavel_ia"]}),
            width="stretch", hide_index=True)


def _render_ai_summary(serial: str, df: pd.DataFrame) -> None:
    """Resumo para o técnico (LLM) + risco de retorno do último chamado."""
    summary = llm.summarize(df, serial, impact.load_improvements())
    source = {"bedrock": "gerado por IA (Amazon Bedrock)",
              "cache": "gerado por IA (Amazon Bedrock, em cache)",
              "regras": "resumo automático por regras (Bedrock desligado)"}
    scores = get_risk_scores(df)
    last = df[df["serie"] == serial].sort_values("data_abertura").index[-1]
    left, right = st.columns([3, 1])
    left.markdown("**Resumo para o técnico**  \n" + summary.texto)
    left.caption(source[summary.fonte])
    if last in scores.index:
        right.metric("Risco de voltar em 90 dias", pct(scores[last], 0),
                     help="Probabilidade estimada pelo modelo de ML para "
                          "o último chamado desta máquina.")


def _render_improvement_status(serial: str, df: pd.DataFrame) -> None:
    """Mostra quais melhorias de fábrica a máquina já 'nasceu' com."""
    from dna_maquina.serial import serial_order_key

    key = serial_order_key(serial)
    model = df.loc[df["serie"] == serial, "modelo_serie"].iat[0]
    badges = []
    for item in impact.load_improvements():
        if item.modelo != model:
            continue
        if item.tipo == "corte_serie":
            has_it = key is not None and key >= serial_order_key(
                item.serie_inicial)
            badges.append(("✅ " if has_it else "⚠️ ") + item.titulo
                          + (" (de fábrica)" if has_it else
                             " — fabricada ANTES da melhoria"))
        else:
            applied = df.loc[df["serie"] == serial, item.flag_evidencia].any()
            badges.append(("🔧 " if applied else "➖ ") + item.titulo
                          + (" aplicada em campo" if applied
                             else " sem registro de aplicação"))
    if badges:
        st.info("  \n".join(badges))


def page_impact(df: pd.DataFrame) -> None:
    """Melhoria × impacto: a prova de que a melhoria funcionou."""
    st.title("Melhoria × impacto")
    st.caption("A pergunta que nunca voltava para a engenharia: funcionou?")

    items = impact.load_improvements()
    names = {f"{i.titulo} ({i.data_documento[:4]})": i for i in items}
    choice = st.selectbox("Melhoria", list(names))
    item = names[choice]
    result = impact.evaluate(df, item)
    table = result.tabela

    st.markdown(f"**{item.documento}** · {item.objetivo}")
    labels = list(table.index)
    before, after = table.iloc[0], table.iloc[1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"{labels[0]}: {result.indicador}", pct(before["taxa"]),
              help=f"n = {fmt_int(before['n'])} chamados, "
                   f"{fmt_int(before['maquinas'])} máquinas")
    c2.metric(f"{labels[1]}: {result.indicador}", pct(after["taxa"]),
              delta=f"{-result.reducao_relativa * 100:+.0f}% relativo"
              .replace(".", ","), delta_color="inverse",
              help=f"n = {fmt_int(after['n'])} chamados, "
                   f"{fmt_int(after['maquinas'])} máquinas")
    c3.metric("p-valor", f"{result.p_valor:.1g}".replace(".", ","))
    verdict = _verdict(result)
    c4.metric("Veredito", verdict)

    fig = go.Figure()
    fig.add_bar(x=labels, y=table["taxa"], marker_color=[NEUTRAL, COFFEE],
                error_y={"type": "data", "symmetric": False,
                         "array": table["ic_sup"] - table["taxa"],
                         "arrayminus": table["taxa"] - table["ic_inf"]},
                text=[pct(v) for v in table["taxa"]], textposition="inside",
                insidetextanchor="middle", textfont={"color": "white",
                                                     "size": 18})
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_tickformat=".0%",
                      title="Comparação com intervalo de confiança de 95%",
                      height=380)
    left, right = st.columns(2)
    left.plotly_chart(fig, width="stretch")

    series = result.serie_temporal
    if item.tipo == "corte_serie":
        fig = px.bar(series, x="coorte", y="taxa", template=PLOT_TEMPLATE,
                     color=series["depois"].map({True: "Depois do corte",
                                                 False: "Antes do corte"}),
                     color_discrete_map={"Depois do corte": COFFEE,
                                         "Antes do corte": NEUTRAL},
                     labels={"coorte": "Semana de fabricação",
                             "taxa": result.indicador, "color": ""},
                     title="Por semana de fabricação (lotes ≥ 50 chamados)")
    else:
        fig = px.line(series, x="mes", y="taxa", markers=True,
                      template=PLOT_TEMPLATE,
                      color_discrete_sequence=[CREMA],
                      labels={"mes": "", "taxa": "% dos reparos de vazamento"},
                      title="Adoção do kit em campo, mês a mês")
    fig.update_layout(yaxis_tickformat=".0%", height=380)
    right.plotly_chart(fig, width="stretch")

    with st.expander("Premissas desta análise"):
        for note in result.notas:
            st.markdown(f"- {note}")
        st.dataframe(table, width="stretch")

    with st.expander("Registrar nova melhoria (diretório do P&D)"):
        _improvement_form(items)


def _verdict(result: impact.CohortResult) -> str:
    """Traduz a estatística em um veredito direto para o P&D."""
    if pd.isna(result.p_valor) or result.tabela["n"].min() < 100:
        return "Amostra insuficiente"
    if result.p_valor < 0.05 and result.reducao_relativa > 0:
        return "Funcionou"
    if result.p_valor < 0.05:
        return "Piorou"
    return "Sem efeito mensurável"


def _improvement_form(items: list[impact.Improvement]) -> None:
    """Formulário para o P&D cadastrar uma melhoria e fechar o ciclo."""
    with st.form("nova_melhoria"):
        title = st.text_input("Título")
        model = st.selectbox("Modelo", ["Passione", "Luna"])
        kind = st.radio("Tipo", ["corte_serie", "retrofit_campo"],
                        format_func={"corte_serie": "Mudança de fábrica "
                                     "(a partir de uma série)",
                                     "retrofit_campo": "Kit aplicado em "
                                     "campo"}.get)
        serial = st.text_input("Série inicial (se mudança de fábrica)")
        symptom = st.text_input("Sintoma-alvo", value=config.LEAK_SYMPTOM)
        doc_date = st.date_input("Data do boletim", value=date.today())
        if st.form_submit_button("Salvar melhoria") and title:
            items.append(impact.Improvement(
                id=f"{model[:2].upper()}-{len(items) + 1:03d}", titulo=title,
                documento="Cadastro via app", modelo=model,
                data_documento=doc_date.isoformat(), tipo=kind,
                sintoma_alvo=symptom, componentes_alvo=[],
                flag_evidencia="fez_adaptacao_hidraulica",
                objetivo="—", serie_inicial=serial or None))
            impact.save_improvements(items)
            st.success("Melhoria registrada. Selecione-a na lista acima.")


def page_voices(df: pd.DataFrame) -> None:
    """Duas vozes: consumidor × técnico."""
    st.title("Duas vozes")
    st.caption("O que o consumidor relatou × o que o técnico encontrou.")
    matrix = analytics.voices_matrix(df)
    fig = px.imshow(matrix, text_auto=".0%", aspect="auto",
                    color_continuous_scale=["#FFFFFF", CREMA, COFFEE],
                    labels={"x": "Causa encontrada pelo técnico",
                            "y": "Sintoma relatado", "color": "%"})
    fig.update_layout(height=520, coloraxis_showscale=False)
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(fig, width="stretch")

    table = analytics.agreement_by_symptom(df).head(12)
    st.subheader("Quando as vozes batem")
    st.dataframe(table.style.format({"concordancia": "{:.0%}",
                                     "sem_defeito": "{:.0%}"}),
                 width="stretch")


def page_radar(df: pd.DataFrame) -> None:
    """Radar: o que está crescendo sem ninguém ter perguntado."""
    st.title("Radar de problemas")
    st.caption("Varre todas as combinações modelo × sintoma × causa e "
               "aponta o que cresceu nos últimos 3 meses acima do histórico.")
    alerts = get_radar(df)
    if alerts.empty:
        st.info("Base curta demais para o radar.")
        return
    st.dataframe(alerts.head(15).style.format({
        "media_base": "{:.1f}", "media_recente": "{:.1f}", "z": "{:.1f}",
        "variacao_pct": "{:+.0f}%"}), width="stretch",
        hide_index=True)

    pick = st.selectbox("Ver evolução de", alerts.head(15).apply(
        lambda r: f"{r.modelo} · {r.sintoma_cs}", axis=1).unique())
    model, symptom = pick.split(" · ", 1)
    series = (df[(df["modelo"] == model) & (df["sintoma_cs"] == symptom)]
              .groupby("mes").size().reset_index(name="n"))
    fig = px.bar(series, x="mes", y="n", template=PLOT_TEMPLATE,
                 color_discrete_sequence=[ALERT],
                 labels={"mes": "", "n": "Chamados"}, title=pick)
    st.plotly_chart(fig, width="stretch")

    with st.expander("Lotes de fabricação com mix anômalo"):
        st.dataframe(analytics.chronic_cohorts(df).head(20),
                     width="stretch", hide_index=True)


def page_import(df: pd.DataFrame) -> None:
    """Importa nova extração .xlsx e atualiza todas as análises."""
    st.title("Importar nova base")
    st.caption("Envie uma nova extração do Salesforce (.xlsx, mesmo layout). "
               "Chamados repetidos são atualizados, não duplicados.")
    upload = st.file_uploader("Planilha .xlsx", type=["xlsx"])
    if upload is not None and st.button("Processar e atualizar"):
        try:
            incoming = clean_complaints(pd.read_excel(upload))
        except SchemaError as error:
            st.error(str(error))
            return
        before = len(df)
        merged = enrich(merge_bases(df, incoming))
        save(merged)
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success(f"{fmt_int(len(incoming))} chamados lidos; base passou "
                   f"de {fmt_int(before)} para {fmt_int(len(merged))}.")

    st.subheader("Qualidade dos dados da base atual")
    flags = {
        "Série inválida/ilegível": "dq_serie_invalida",
        "Instalação com data impossível": "dq_instalacao_suspeita",
        "Chamado aberto antes da instalação": "dq_abertura_antes_instalacao",
        "Sem conclusão técnica": "dq_sem_conclusao",
        "Série ilegível com coorte recuperada (IA)": "coorte_recuperada",
    }
    quality = pd.DataFrame({
        "Registros": {k: int(df[v].sum()) for k, v in flags.items()},
        "% da base": {k: pct(df[v].mean()) for k, v in flags.items()},
    })
    st.dataframe(quality, width="stretch")


def page_risk(df: pd.DataFrame) -> None:
    """Risco de retorno: modelo de ML para priorizar acompanhamento."""
    st.title("Risco de retorno")
    st.caption("Ao encerrar um chamado, qual a chance de a mesma máquina "
               "voltar em até 90 dias? Serve para o CS ligar antes da "
               "consumidora ligar de novo.")
    _, metrics = get_risk_model()
    scores = get_risk_scores(df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Retorno médio (teste 2026)",
              pct(metrics["taxa_retorno_teste"]))
    c2.metric("Retorno nos 10% de maior risco",
              pct(metrics["precisao_top10_modelo"]),
              help="Dos chamados que o modelo pôs no topo, quantos de fato "
                   "voltaram em 90 dias.")
    c3.metric("AUC do modelo", f"{metrics['auc_modelo']:.2f}"
              .replace(".", ","),
              delta=f"regra simples: {metrics['auc_baseline']:.2f}"
              .replace(".", ","), delta_color="off")
    c4.metric("Com laudo: top 20% × média",
              f"{pct(metrics['taxa_top20_com_registro'], 0)} × "
              f"{pct(metrics['taxa_media_com_registro'], 0)}",
              help="Entre chamados COM registro técnico, onde a regra "
                   "simples não distingue nada.")

    left, right = st.columns(2)
    calib = pd.DataFrame(metrics["calibracao"])
    fig = go.Figure()
    fig.add_bar(x=calib["decil"] + 1, y=calib["observado"],
                name="Observado", marker_color=COFFEE)
    fig.add_scatter(x=calib["decil"] + 1, y=calib["previsto"],
                    name="Previsto", mode="lines+markers",
                    line={"color": CREMA})
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_tickformat=".0%",
                      xaxis_title="Decil de risco (1 = menor)",
                      title="Previsto × observado (teste 2026)", height=380)
    left.plotly_chart(fig, width="stretch")
    imp = pd.Series(metrics["importancias"]).head(8).sort_values()
    fig = px.bar(imp, orientation="h", template=PLOT_TEMPLATE,
                 color_discrete_sequence=[CREMA],
                 labels={"value": "Queda de AUC sem a variável",
                         "index": ""},
                 title="O que o modelo mais usa")
    fig.update_layout(showlegend=False, height=380)
    right.plotly_chart(fig, width="stretch")

    st.subheader("Chamados recentes para acompanhar")
    recent_start = df["data_abertura"].max() - pd.Timedelta(
        days=config.REINCIDENCE_WINDOW_DAYS)
    recent = df.loc[scores.index].assign(risco=scores)
    recent = recent[recent["data_abertura"] > recent_start]
    table = recent.sort_values("risco", ascending=False).head(50)[
        ["data_abertura", "serie", "modelo", "sintoma_cs", "causa_label",
         "ordem_na_maquina", "risco"]]
    st.dataframe(table.rename(columns={
        "data_abertura": "Abertura", "serie": "Série", "modelo": "Modelo",
        "sintoma_cs": "Sintoma", "causa_label": "Causa",
        "ordem_na_maquina": "Nº na máquina", "risco": "Risco"}).style.format(
        {"Risco": "{:.0%}", "Abertura": "{:%d/%m/%Y}",
         "Nº na máquina": "{:.0f}"}),
        width="stretch", hide_index=True)
    if st.button("Retreinar o modelo com a base atual"):
        model, new_metrics = risk.train_and_evaluate(df)
        risk.save(model, new_metrics)
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success(f"Modelo retreinado. AUC no teste: "
                   f"{new_metrics.auc_modelo:.2f}.")
    with st.expander("Como o modelo foi construído"):
        st.markdown(
            f"- Gradient boosting (scikit-learn) com variáveis conhecidas "
            f"no encerramento do chamado: sintoma, laudo, causa, kit, "
            f"histórico da máquina, idade e modelo.\n"
            f"- Validação temporal: treino com 2025 "
            f"({fmt_int(metrics['n_treino'])} chamados), teste com 2026 "
            f"({fmt_int(metrics['n_teste'])}).\n"
            f"- Comparado com a regra \"chamado sem registro técnico\" "
            f"(AUC {metrics['auc_baseline']:.2f}).\n"
            f"- Chamados dos últimos 90 dias não entram no treino "
            f"(desfecho desconhecido) e são os que recebem a previsão.")


def page_patterns(df: pd.DataFrame) -> None:
    """Padrões descobertos pela IA no texto livre dos técnicos."""
    st.title("Padrões no texto (IA)")
    st.caption("Um modelo não supervisionado (TF-IDF + NMF) leu as "
               "conclusões técnicas e agrupou sozinho os modos de falha "
               "que se repetem — inclusive os que nenhuma regra procura.")
    modes = get_failure_modes(df)
    st.dataframe(modes.temas.rename(columns={
        "nome": "Modo de falha (nome automático)", "termos": "Termos que "
        "definem o tema", "chamados": "Chamados"}).drop(columns="tema"),
        width="stretch", hide_index=True)

    left, right = st.columns(2)
    share = modes.por_modelo[["Passione", "Luna"]]
    fig = px.imshow(share, text_auto=".0%", aspect="auto",
                    color_continuous_scale=["#FFFFFF", CREMA, COFFEE],
                    labels={"x": "Modelo", "y": "", "color": "%"},
                    title="Peso de cada modo de falha por modelo")
    fig.update_layout(coloraxis_showscale=False, height=460)
    left.plotly_chart(fig, width="stretch")
    rising = patterns.emerging_topics(modes).head(5).reset_index()
    fig = px.bar(rising, x="variacao_pp", y="tema", orientation="h",
                 template=PLOT_TEMPLATE, color_discrete_sequence=[ALERT],
                 labels={"variacao_pp": "Variação da fatia (p.p., últimos "
                         "3 meses)", "tema": ""},
                 title="Modos de falha em alta")
    fig.update_layout(height=460, yaxis={"autorange": "reversed"})
    right.plotly_chart(fig, width="stretch")

    st.subheader("Boletins técnicos citados pelos técnicos")
    st.caption("Achado da leitura do texto: boletins aplicados em campo "
               "que não estão no diretório de melhorias fornecido. "
               "Cadastrando-os em Melhoria × impacto, o efeito passa a ser "
               "medido.")
    st.dataframe(patterns.bulletin_mentions(df).head(12).style.format(
        {"primeiro_mes": "{:%m/%Y}", "ultimo_mes": "{:%m/%Y}"}),
        width="stretch", hide_index=True)


def page_assistant(df: pd.DataFrame) -> None:
    """Assistente: a conversa com IA é da Cora; aqui fica o plano B."""
    st.title("Assistente de engenharia")
    cora_url = os.getenv("DNA_CORA_URL", "").strip().rstrip("/")
    st.info("A conversa com IA acontece na **Cora**, que chama as análises "
            "deste projeto pelo conector MCP “DNA da Máquina” (rota /mcp do "
            "backend). Esta interface antiga mostra só as respostas por "
            "regras. Veja docs/CORA.md.")
    if cora_url:
        st.link_button("Abrir a Cora", cora_url)

    st.subheader("Perguntas prontas (sem IA, funcionam sem internet)")
    for preset in assistant.PRESETS:
        with st.expander(preset):
            text, raw = assistant.answer_preset(df, preset)
            st.markdown(f"**{text}**")
            st.json(raw, expanded=False)

    st.subheader("Parecer técnico para o P&D (por regras)")
    items = {i.titulo: i.id for i in impact.load_improvements()}
    choice = st.selectbox("Melhoria", list(items), key="parecer")
    if st.button("Gerar parecer"):
        memo = assistant.decision_memo(df, items[choice])
        st.text(memo)
        st.download_button("Baixar parecer (.txt)", memo,
                           file_name=f"parecer_{items[choice]}.txt")


PAGES = {
    "Visão geral": page_overview,
    "DNA da máquina": page_machine,
    "Melhoria × impacto": page_impact,
    "Duas vozes": page_voices,
    "Radar": page_radar,
    "Risco de retorno": page_risk,
    "Padrões no texto (IA)": page_patterns,
    "Assistente (IA)": page_assistant,
    "Importar base": page_import,
}


def main() -> None:
    """Monta a navegação lateral e renderiza a página escolhida."""
    st.sidebar.markdown("## ☕ DNA da Máquina")
    st.sidebar.caption("Histórico confiável de cada máquina TRES, "
                       "do chamado à engenharia.")
    page = st.sidebar.radio("Navegação", list(PAGES))
    data = get_data()
    st.sidebar.caption(f"Base: {fmt_int(len(data))} chamados · "
                       f"{data['data_abertura'].min():%m/%Y} a "
                       f"{data['data_abertura'].max():%m/%Y}")
    PAGES[page](data)


main()
