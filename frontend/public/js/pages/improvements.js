// Melhoria × impacto: a pergunta que nunca voltava para a engenharia.

import { api } from "../api.js";
import { link } from "../areas.js";
import { badge, card, chartBox, fold, metric, notice, pageHeader, table } from "../components.js";
import { COLORS, VERDICT_TONE } from "../config.js";
import { h, render } from "../dom.js";
import { mountChart, percentAxis } from "../charts.js";
import { int, month, pValue, pct, signedPct } from "../format.js";

const DEFAULT_ID = "G5-BANDEJA-2022"; // o caso ponta a ponta do briefing

function comparisonChart(canvas, groups) {
  mountChart(canvas, {
    type: "bar",
    data: {
      labels: groups.map((g) => g.grupo),
      datasets: [{
        data: groups.map((g) => g.taxa),
        backgroundColor: [COLORS.grey, COLORS.burgundy],
        errorBars: groups.map((g) => ({ low: g.ic_inf, high: g.ic_sup })),
      }],
    },
    options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => pct(c.parsed.y) } } },
      scales: { y: { beginAtZero: true, ...percentAxis } } },
  });
}

function seriesChart(canvas, evaluation) {
  const rows = evaluation.serie_temporal;
  if (evaluation.melhoria.tipo === "corte_serie") {
    mountChart(canvas, {
      type: "bar",
      data: { labels: rows.map((r) => r.coorte), datasets: [{ data: rows.map((r) => r.taxa),
        backgroundColor: rows.map((r) => (r.depois ? COLORS.burgundy : COLORS.grey)) }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ...percentAxis } } },
    });
  } else {
    mountChart(canvas, {
      type: "line",
      data: { labels: rows.map((r) => month(r.mes)), datasets: [{ data: rows.map((r) => r.taxa), borderColor: COLORS.orange, backgroundColor: COLORS.orange, tension: 0.25 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ...percentAxis } } },
    });
  }
}

function evaluationView(evaluation) {
  const [before, after] = evaluation.tabela;
  const comparison = chartBox("Comparação antes e depois, com intervalo de confiança de 95%");
  const series = chartBox("Evolução por coorte ou por mês");
  const info = evaluation.melhoria;
  const origin = evaluation.evidencia;
  const originText = {
    serie: "Vínculo pela série de fabricação (não depende de texto do técnico).",
    registrada: `Vínculo REGISTRADO: ${int(origin.chamados_com_codigo)} chamados trazem o código da melhoria.`,
    inferida: "Vínculo INFERIDO por palavras no texto livre; nenhum chamado traz o código ainda.",
  }[origin.origem];
  const view = h("div", {},
    h("p", {}, h("strong", { text: `${info.documento}. ` }), info.objetivo),
    h("p", {},
      info.codigo ? badge(`Código do projeto ${info.codigo}`, "neutral") : null, " ",
      badge(origin.origem === "registrada" ? "registrado" : origin.origem === "serie" ? "por série" : "inferido", origin.origem === "inferida" ? "warn" : "good"),
      ` ${originText}`),
    h("div", { class: "grid" },
      metric(`${before.grupo}: ${evaluation.indicador}`, pct(before.taxa), `n = ${int(before.n)} chamados · ${int(before.maquinas)} máquinas`),
      metric(`${after.grupo}: ${evaluation.indicador}`, pct(after.taxa), `${signedPct(evaluation.reducao_relativa == null ? null : -evaluation.reducao_relativa)} relativo · n = ${int(after.n)} · ${int(after.maquinas)} máquinas`),
      metric("p-valor", pValue(evaluation.p_valor), "chance de ver essa diferença por acaso"),
      h("div", { class: "metric" }, h("div", { class: "metric__label", text: "Veredito para o P&D" }),
        h("div", { class: "metric__value" }, badge(evaluation.veredito, VERDICT_TONE[evaluation.veredito] ?? "neutral")))),
    h("div", { class: "grid grid--wide section" },
      card({ title: "Antes × depois, com IC de 95%" }, comparison.box),
      card({ title: info.tipo === "corte_serie" ? "Por semana de fabricação" : "Adoção do kit, mês a mês" }, series.box)),
    fold("Premissas desta análise", [
      h("ul", {}, evaluation.notas.map((note) => h("li", { text: note }))),
      table([
        { key: "grupo", label: "Grupo" }, { key: "n", label: "Chamados", num: true, render: (r) => int(r.n) },
        { key: "eventos", label: "Eventos", num: true, render: (r) => int(r.eventos) },
        { key: "taxa", label: "Taxa", num: true, render: (r) => pct(r.taxa) },
        { key: "ic_inf", label: "IC inferior", num: true, render: (r) => pct(r.ic_inf) },
        { key: "ic_sup", label: "IC superior", num: true, render: (r) => pct(r.ic_sup) },
      ], evaluation.tabela)], { count: evaluation.notas.length }),
    h("p", {}, h("a", { class: "btn btn--outline", href: link("estoque", info.id), text: "Levantar máquinas em estoque para esta melhoria" })));
  view.afterMount = () => { comparisonChart(comparison.canvas, evaluation.tabela); seriesChart(series.canvas, evaluation); };
  return view;
}

function registerForm(onSaved) {
  const result = h("div", { "aria-live": "polite" });
  const form = h("form", {},
    h("div", { class: "field--inline" },
      h("div", { class: "field" }, h("label", { for: "m-titulo", text: "Título" }), h("input", { id: "m-titulo", name: "titulo", required: true, minlength: 3, maxlength: 120 })),
      h("div", { class: "field" }, h("label", { for: "m-modelo", text: "Modelo" }),
        h("select", { id: "m-modelo", name: "modelo" }, h("option", { text: "Passione" }), h("option", { text: "Luna" }))),
      h("div", { class: "field" }, h("label", { for: "m-tipo", text: "Tipo" }),
        h("select", { id: "m-tipo", name: "tipo" },
          h("option", { value: "corte_serie", text: "Mudança de fábrica (a partir de uma série)" }),
          h("option", { value: "retrofit_campo", text: "Kit aplicado em campo" })))),
    h("div", { class: "field--inline" },
      h("div", { class: "field" }, h("label", { for: "m-serie", text: "Série inicial (se mudança de fábrica)" }), h("input", { id: "m-serie", name: "serie_inicial", placeholder: "G5PS000210224033" })),
      h("div", { class: "field" }, h("label", { for: "m-data", text: "Data do boletim" }), h("input", { id: "m-data", name: "data_documento", type: "date", required: true, value: new Date().toISOString().slice(0, 10) }))),
    h("button", { class: "btn", type: "submit", text: "Registrar melhoria" }), result);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    if (!data.serie_inicial) delete data.serie_inicial;
    try {
      const created = await api.post("/improvements", data);
      render(result, notice(`Melhoria ${created.id} registrada com o código ${created.codigo}. Ela já aparece na lista acima.`, "ok"));
      onSaved(created.id);
    } catch (error) {
      render(result, notice(error.message, "error"));
    }
  });
  return form;
}

export const improvementsPage = {
  title: "Melhorias",
  async render({ params, signal }) {
    const catalog = await api.get("/impact", signal);
    if (!catalog.length) {
      return h("div", {}, pageHeader("Melhoria × impacto", "Ainda não há melhorias cadastradas."),
        h("p", {}, "Comece pelo boletim em PDF: ", h("a", { href: link("boletins"), text: "Inserir boletim" }), "."));
    }
    const wanted = params[0] ?? (catalog.find((c) => c.id === DEFAULT_ID) ?? catalog[0]).id;
    const select = h("select", { id: "melhoria", "aria-label": "Melhoria" },
      catalog.map((item) => h("option", { value: item.id, selected: item.id === wanted, text: `${item.titulo} (${item.ano})${item.codigo ? ` · ${item.codigo}` : ""}` })));
    select.addEventListener("change", () => { window.location.hash = link("melhorias", select.value); });
    const evaluation = await api.get(`/impact/${encodeURIComponent(wanted)}`, signal);
    const view = evaluationView(evaluation);
    const page = h("div", {},
      pageHeader("Melhoria × impacto", "A pergunta que nunca voltava para a engenharia: funcionou? Compara os chamados antes e depois de cada melhoria, com intervalo de confiança."),
      h("div", { class: "field" }, h("label", { for: "melhoria", text: "Melhoria" }), select),
      h("p", {}, "Tem o boletim em PDF? ", h("a", { href: link("boletins"), text: "Inserir boletim" }), " lê os campos, mostra os dados relacionados e gera o código do projeto da melhoria."),
      view,
      h("section", { class: "band" }, fold("Registrar a próxima melhoria (sem PDF)", [
        h("p", { class: "page-lead", text: "Cadastrar a melhoria com a série a partir da qual vale é o que fecha o ciclo: a próxima análise já mede o efeito dela." }),
        registerForm((id) => { setTimeout(() => { window.location.hash = link("melhorias", id); }, 800); })])));
    page.afterMount = view.afterMount;
    return page;
  },
};
