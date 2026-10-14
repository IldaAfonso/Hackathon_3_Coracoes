// Risco de retorno: priorizar o acompanhamento antes de o consumidor ligar de novo.

import { api } from "../api.js";
import { link } from "../areas.js";
import { card, chartBox, fold, metric, pageHeader, table } from "../components.js";
import { COLORS } from "../config.js";
import { h } from "../dom.js";
import { mountChart, percentAxis } from "../charts.js";
import { date, decimal, int, pct } from "../format.js";

function charts(metrics, calibration, importances) {
  const deciles = metrics.calibracao.map((c) => c.decil + 1);
  mountChart(calibration, {
    type: "bar",
    data: { labels: deciles, datasets: [
      { type: "bar", label: "Observado", data: metrics.calibracao.map((c) => c.observado), backgroundColor: COLORS.burgundy },
      { type: "line", label: "Previsto", data: metrics.calibracao.map((c) => c.previsto), borderColor: COLORS.orange, backgroundColor: COLORS.orange },
    ] },
    options: { plugins: { legend: { position: "bottom" } }, scales: { y: { beginAtZero: true, ...percentAxis },
      x: { title: { display: true, text: "Decil de risco (1 = menor)" } } } },
  });
  const entries = Object.entries(metrics.importancias).slice(0, 8);
  mountChart(importances, {
    type: "bar",
    data: { labels: entries.map(([name]) => name), datasets: [{ data: entries.map(([, value]) => value), backgroundColor: COLORS.orange }] },
    options: { indexAxis: "y", plugins: { legend: { display: false } } },
  });
}

export const riskPage = {
  title: "Riscos",
  async render({ signal }) {
    const data = await api.get("/risk", signal);
    const m = data.metricas;
    const calibration = chartBox("Risco previsto e observado por decil");
    const importances = chartBox("Variáveis que o modelo mais usa");
    const page = h("div", {},
      pageHeader("Risco de retorno (ML)", "Ao encerrar um chamado, qual a chance de a mesma máquina voltar em até 90 dias? Serve para o CS ligar antes de o consumidor ligar de novo."),
      h("div", { class: "grid" },
        metric("Retorno médio (teste 2026)", pct(m.taxa_retorno_teste)),
        metric("Retorno nos 10% de maior risco", pct(m.precisao_top10_modelo), "dos chamados que o modelo pôs no topo"),
        metric("AUC do modelo", decimal(m.auc_modelo), `regra simples: ${decimal(m.auc_baseline)}`),
        metric("Com laudo: top 20% × média", `${pct(m.taxa_top20_com_registro, 0)} × ${pct(m.taxa_media_com_registro, 0)}`, "onde a regra simples não distingue nada")),
      h("div", { class: "grid grid--wide section" },
        card({ title: "Previsto × observado (teste 2026)" }, calibration.box),
        card({ title: "O que o modelo mais usa" }, importances.box)),
      h("section", { class: "section" },
        table([
          { key: "data_abertura", label: "Abertura", render: (r) => date(r.data_abertura) },
          { key: "serie", label: "Série", render: (r) => h("a", { href: link("dna", r.serie), text: r.serie }) },
          { key: "modelo", label: "Modelo" }, { key: "sintoma_cs", label: "Sintoma" }, { key: "causa_label", label: "Causa" },
          { key: "ordem_na_maquina", label: "Nº na máquina", num: true, render: (r) => int(r.ordem_na_maquina) },
          { key: "risco", label: "Risco", num: true, render: (r) => pct(r.risco, 0) },
        ], data.acompanhar, "Chamados recentes para acompanhar, do maior risco ao menor")),
      fold("Como o modelo foi construído",
        h("ul", {},
          h("li", { text: "Gradient boosting com variáveis conhecidas no encerramento do chamado: sintoma, laudo, causa, kit, histórico da máquina, idade e modelo." }),
          h("li", { text: `Validação temporal: treino com 2025 (${int(m.n_treino)} chamados) e teste com 2026 (${int(m.n_teste)}).` }),
          h("li", { text: "Comparado com a regra simples \"chamado sem registro técnico\"." }),
          h("li", { text: "Chamados dos últimos 90 dias não entram no treino (desfecho ainda desconhecido) e são os que recebem a previsão." }))));
    page.afterMount = () => charts(m, calibration.canvas, importances.canvas);
    return page;
  },
};
