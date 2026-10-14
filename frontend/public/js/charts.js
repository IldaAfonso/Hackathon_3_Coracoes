// Gráficos (Chart.js, servido localmente). Todos nascem e morrem com a rota.

import { COLORS } from "./config.js";
import { pct } from "./format.js";

const alive = [];

if (window.Chart) {
  window.Chart.defaults.font.family = 'Jost, "Segoe UI", system-ui, sans-serif';
  window.Chart.defaults.color = "#2a1f1a";
  window.Chart.defaults.maintainAspectRatio = false;
  window.Chart.defaults.animation = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 400 };
}

/** Barras de erro (intervalo de confiança) desenhadas sobre um gráfico de barras. */
const errorBars = {
  id: "errorBars",
  afterDatasetsDraw(chart) {
    const dataset = chart.data.datasets.find((d) => d.errorBars);
    if (!dataset) return;
    const { ctx, scales } = chart;
    const meta = chart.getDatasetMeta(chart.data.datasets.indexOf(dataset));
    ctx.save();
    ctx.strokeStyle = COLORS.burgundy;
    ctx.lineWidth = 2;
    dataset.errorBars.forEach((bar, index) => {
      if (!bar || bar.low == null || bar.high == null) return;
      const x = meta.data[index].x;
      const top = scales.y.getPixelForValue(bar.high);
      const bottom = scales.y.getPixelForValue(bar.low);
      ctx.beginPath();
      ctx.moveTo(x, top); ctx.lineTo(x, bottom);
      ctx.moveTo(x - 7, top); ctx.lineTo(x + 7, top);
      ctx.moveTo(x - 7, bottom); ctx.lineTo(x + 7, bottom);
      ctx.stroke();
    });
    ctx.restore();
  },
};

/** Cria um gráfico num <canvas> e o registra para ser destruído ao trocar de rota. */
export function mountChart(canvas, config) {
  if (!window.Chart) throw new Error("Chart.js não foi carregado.");
  const chart = new window.Chart(canvas, { plugins: [errorBars], ...config });
  alive.push(chart);
  return chart;
}

export function destroyCharts() {
  while (alive.length) alive.pop().destroy();
}

export const percentAxis = { ticks: { callback: (value) => pct(value, 0) } };
