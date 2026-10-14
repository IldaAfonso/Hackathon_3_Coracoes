// Padrões no texto (IA): modos de falha descobertos no que os técnicos escrevem.

import { api } from "../api.js";
import { autoTable, card, chartBox, heatTable, pageHeader } from "../components.js";
import { COLORS } from "../config.js";
import { h } from "../dom.js";
import { mountChart } from "../charts.js";
import { decimal, int, month, pct } from "../format.js";

export const patternsPage = {
  title: "Padrões no texto (IA)",
  menu: "Padrões (IA)",
  async render({ signal }) {
    const data = await api.get("/patterns", signal);
    const rising = chartBox("Modos de falha em alta");
    const share = data.por_modelo;
    const page = h("div", {},
      pageHeader("Padrões no texto (IA)", "Um modelo não supervisionado (TF-IDF + NMF) leu as conclusões dos técnicos e agrupou sozinho os modos de falha que se repetem, inclusive os que nenhuma regra procura."),
      autoTable(data.temas.map((row) => ({ "modo de falha (nome automático)": row.nome, "termos que definem o tema": row.termos, chamados: row.chamados })), { chamados: int }, "Modos de falha descobertos"),
      h("div", { class: "grid grid--wide section" },
        card({ title: "Peso de cada modo de falha, por modelo" },
          heatTable({ rowLabels: share.temas, colLabels: share.modelos, values: share.valores, format: (v) => pct(v, 0), corner: "Modo de falha" })),
        card({ title: "Em alta nos últimos 3 meses (variação da fatia, em pontos percentuais)" }, rising.box)),
      h("section", { class: "section" }, h("h2", { text: "Boletins técnicos citados pelos técnicos" }),
        h("p", { class: "page-lead", text: "Boletins aplicados em campo que não estão no diretório de melhorias fornecido. Cadastrando-os em Melhorias, o efeito deles passa a ser medido." }),
        autoTable(data.boletins, { primeiro_mes: month, ultimo_mes: month, citacoes: int, chamados: int }, "Boletins citados", {
          modelo: "Modelo", assunto: "Assunto do boletim", citacoes: "Citações", primeiro_mes: "Primeira citação", ultimo_mes: "Última citação" })));
    page.afterMount = () => mountChart(rising.canvas, {
      type: "bar",
      data: { labels: data.em_alta.map((r) => r.tema), datasets: [{ data: data.em_alta.map((r) => r.variacao_pp), backgroundColor: COLORS.orange }] },
      options: { indexAxis: "y", plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${decimal(c.parsed.x, 1)} p.p.` } } } },
    });
    return page;
  },
};
