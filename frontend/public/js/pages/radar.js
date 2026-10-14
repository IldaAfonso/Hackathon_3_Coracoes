// Radar: o que está crescendo sem ninguém ter perguntado.

import { api } from "../api.js";
import { autoTable, card, chartBox, notice, pageHeader } from "../components.js";
import { COLORS } from "../config.js";
import { h, render } from "../dom.js";
import { mountChart } from "../charts.js";
import { decimal, month } from "../format.js";

export const radarPage = {
  title: "Radar",
  menu: "Radar",
  async render({ signal }) {
    const data = await api.get("/radar", signal);
    const header = pageHeader("Radar de problemas", "Varre todas as combinações de modelo, sintoma e causa e aponta o que cresceu nos últimos 3 meses acima do histórico.");
    if (!data.alertas.length) return h("div", {}, header, notice("Base curta demais para o radar.", "info"));

    const options = data.alertas.map((a) => `${a.modelo} · ${a.sintoma_cs}`);
    const select = h("select", { id: "radar-pick", "aria-label": "Ver evolução de" },
      [...new Set(options)].map((label) => h("option", { text: label })));
    const { box, canvas } = chartBox("Chamados por mês do problema escolhido");
    const holder = h("div", {}, box);
    let chart = null;

    async function draw() {
      const [modelo, sintoma] = select.value.split(" · ");
      const rows = await api.get(`/radar/serie?modelo=${encodeURIComponent(modelo)}&sintoma=${encodeURIComponent(sintoma)}`);
      chart?.destroy();
      chart = mountChart(canvas, { type: "bar",
        data: { labels: rows.map((r) => month(r.mes)), datasets: [{ data: rows.map((r) => r.n), backgroundColor: COLORS.orange }] },
        options: { plugins: { legend: { display: false }, title: { display: true, text: select.value } } } });
    }
    select.addEventListener("change", () => draw().catch((e) => render(holder, notice(e.message, "error"))));

    const page = h("div", {}, header,
      autoTable(data.alertas, { media_base: (v) => decimal(v, 1), media_recente: (v) => decimal(v, 1), z: (v) => decimal(v, 1),
        variacao_pct: (v) => `${v > 0 ? "+" : ""}${decimal(v, 0)}%` }, "Alertas do radar", {
        modelo: "Modelo", sintoma_cs: "Sintoma (consumidor)", causa_label: "Causa (técnico)", casos_base: "Casos na base",
        casos_recentes: "Casos nos últimos 3 meses", media_base: "Média mensal (base)", media_recente: "Média mensal (recente)",
        z: "Desvios acima do normal (z)", variacao_pct: "Variação" }),
      h("section", { class: "section" }, h("div", { class: "field" }, h("label", { for: "radar-pick", text: "Ver evolução de" }), select),
        card({ title: "Evolução mensal" }, holder)),
      h("details", {}, h("summary", { text: "Lotes de fabricação com mix anômalo" }), autoTable(data.lotes_anomalos, {}, "Lotes anômalos")));
    page.afterMount = () => draw().catch(() => {});
    return page;
  },
};
