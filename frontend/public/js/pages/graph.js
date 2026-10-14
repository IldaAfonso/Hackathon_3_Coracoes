// Grafo da máquina: o número de série liga os três times numa só história.

import { api } from "../api.js";
import { badge, notice, pageHeader } from "../components.js";
import { IMPROVEMENT_STATUS } from "../config.js";
import { h, svg } from "../dom.js";
import { date } from "../format.js";
import { GRAPH, buildGraph, truncate } from "../graph-layout.js";

const DEMO_SERIAL = "G5PS000220465809";
const NODE = { call: [150, 36], voice: [210, 34] };

const curve = (x1, y1, x2, y2) => {
  const mid = (x1 + x2) / 2;
  return `M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`;
};

function node(kind, cx, cy, label, full, size) {
  const [w, hgt] = size;
  return svg("g", { class: `gnode gnode--${kind}`, tabindex: "0" },
    svg("title", { text: full }),
    svg("rect", { x: cx - w / 2, y: cy - hgt / 2, width: w, height: hgt, rx: 10 }),
    svg("text", { x: cx, y: cy + 4, "text-anchor": "middle", text: label }));
}

function drawGraph(machine, after = false, verdicts = {}) {
  const graph = buildGraph(machine);
  const { center, left, right } = GRAPH;
  const edges = graph.edges.map((edge) => {
    const [side, y1] = edge.from;
    const [col, y2] = edge.to;
    const toLeft = col === "s";
    const x1 = center + (toLeft ? -NODE.call[0] / 2 : NODE.call[0] / 2);
    const x2 = toLeft ? left + NODE.voice[0] / 2 : right - NODE.voice[0] / 2;
    const missing = edge.missing ? (after ? " gedge--future" : " gedge--missing") : "";
    return svg("path", { class: `gedge gedge--${edge.kind}${missing}`, d: curve(x1, y1, x2, y2), "data-side": side });
  });
  const returns = graph.returns.map((link) => svg("path", {
    class: "gedge gedge--return", "marker-end": "url(#seta)",
    d: `M${center + 75},${link.from + 18} C${center + 130},${link.from + 30} ${center + 130},${link.to - 30} ${center + 75},${link.to - 18}`,
  }));
  const calls = graph.calls.map((call) => {
    const back = call.event.voltou_em_90_dias;
    const g = node(back ? "call-return" : "call", center, call.y,
      `${date(call.event.data)} · ${truncate(call.event.caso, 8)}`, `Caso ${call.event.caso ?? "—"} em ${date(call.event.data)}`, NODE.call);
    return g;
  });
  const symptoms = [...graph.symptoms].map(([name, y]) => node("cs", left, y, truncate(name, 28), `Customer Success: ${name}`, NODE.voice));
  const causes = [...graph.causes].map(([name, y]) => {
    if (name !== "Sem registro técnico") return node("pos", right, y, truncate(name, 30), `Pós-vendas: ${name}`, NODE.voice);
    return after
      ? node("pos-future", right, y, "Laudo ligado ao chamado", "Depois: o laudo do técnico fica ligado a cada chamado (o conteúdo ainda será registrado pelo técnico)", NODE.voice)
      : node("pos-missing", right, y, truncate(name, 30), `Pós-vendas: ${name}`, NODE.voice);
  });
  const serial = machine.ficha.serie;
  const improvements = machine.melhorias.slice(0, 3).map((item, index) => {
    const status = IMPROVEMENT_STATUS[item.status] ?? { label: item.status };
    const verdict = after ? verdicts[item.id] : null;
    const tone = { Funcionou: "pd-good", "Sem efeito mensurável": "pd-warn" }[verdict] ?? "pd";
    const short = { "Sem efeito mensurável": "sem efeito", "Amostra insuficiente": "amostra pequena" }[verdict] ?? verdict?.toLowerCase();
    const label = verdict ? `${truncate(item.titulo, 21)} · ${short}` : truncate(item.titulo, 30);
    return svg("g", {},
      svg("path", { class: "gedge gedge--pd", d: curve(center + 70, 52, right - (after ? 135 : 105), 20 + index * 30) }),
      node(tone, right, 20 + index * 30, label, `P&D: ${item.titulo} (${status.label})${verdict ? `. O P&D recebe a resposta: ${verdict}` : ""}`, verdict ? [270, 26] : NODE.voice));
  });
  const view = svg("svg", {
    class: "graph", viewBox: `0 0 ${GRAPH.width} ${graph.height}`, role: "img",
    "aria-label": `Grafo da máquina ${serial}: ${graph.shown} chamados ligados às vozes do consumidor, do técnico e às melhorias do P&D`,
  },
  svg("defs", {}, svg("marker", { id: "seta", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" },
    svg("path", { d: "M0,0 L10,5 L0,10 z", class: "garrow" }))),
  svg("text", { class: "gcol", x: left, y: 120, "text-anchor": "middle", text: "CUSTOMER SUCCESS · ouve" }),
  svg("text", { class: "gcol", x: center, y: 120, "text-anchor": "middle", text: "CHAMADOS DA MESMA SÉRIE" }),
  svg("text", { class: "gcol", x: right, y: 120, "text-anchor": "middle", text: "PÓS-VENDAS · resolve" }),
  svg("path", { class: "gspine", d: `M${center},62 L${center},${graph.calls.at(-1)?.y ?? 130}` }),
  edges, returns, calls, symptoms, causes, improvements,
  after ? svg("text", { class: "gok", x: center, y: 84, "text-anchor": "middle", text: "✔ série validada na abertura" }) : null,
  svg("g", { class: "gnode gnode--machine" },
    svg("title", { text: `Máquina ${serial}` }),
    svg("rect", { x: center - 130, y: 14, width: 260, height: 46, rx: 23 }),
    svg("text", { x: center, y: 42, "text-anchor": "middle", text: serial })));
  return { view, graph };
}

function legend(after) {
  const item = (cls, text) => h("li", {}, h("span", { class: `swatch swatch--${cls}` }), text);
  return h("ul", { class: "legend", "aria-label": "Legenda" },
    item("machine", "Máquina (chave: número de série)"), item("cs", "Voz do consumidor"),
    item("pos", "Voz do técnico"), item("pd", "Melhoria do P&D"),
    item("return", "Chamado que voltou em até 90 dias"),
    after ? item("future", "Laudo ligado ao chamado") : item("missing", "Sem registro técnico"));
}

export const graphPage = {
  title: "Grafo",
  menu: "Grafo",
  async render({ params, signal }) {
    const serial = params[0] ?? DEMO_SERIAL;
    const after = params[1] === "depois";
    const machine = await api.get(`/machines/${encodeURIComponent(serial)}`, signal);
    const verdicts = {};
    if (after) {
      await Promise.all(machine.melhorias.slice(0, 3).map(async (item) => {
        try { verdicts[item.id] = (await api.get(`/impact/${encodeURIComponent(item.id)}`, signal)).veredito; } catch { /* sem veredito */ }
      }));
    }
    const { view, graph } = drawGraph(machine, after, verdicts);
    const base = `#/grafo/${encodeURIComponent(serial)}`;
    const modes = h("nav", { class: "tabs", "aria-label": "Momento" },
      h("a", { class: "tab", href: base, "aria-current": after ? null : "page", text: "Hoje" }),
      h("a", { class: "tab", href: `${base}/depois`, "aria-current": after ? "page" : null, text: "Depois das melhorias" }));
    const ficha = machine.ficha;
    return h("div", {},
      pageHeader("O grafo da máquina", "Um número de série liga o que o consumidor disse, o que o técnico encontrou e a melhoria do P&D. É a história inteira que hoje ninguém enxerga."),
      h("p", {}, badge(ficha.serie, "neutral"), " ",
        `${ficha.chamados} chamados · ${ficha.voltas_em_90_dias} voltaram em até 90 dias`,
        graph.total > graph.shown ? ` · mostrando os ${graph.shown} mais recentes` : "", " ",
        h("a", { href: `#/pd/dna/${encodeURIComponent(ficha.serie)}`, text: "Ver o DNA completo" })),
      modes,
      after ? notice("Ilustração do estado futuro: o mesmo histórico, real, com os pontos de melhoria em funcionamento (série validada, laudo ligado ao chamado, P&D recebendo a resposta de cada melhoria). Nenhum chamado ou causa foi inventado; mudam as ligações. Depende de os sistemas da empresa implantarem os pontos recomendados.", "info") : null,
      graph.shown ? h("div", { class: "graph-wrap" }, view) : notice("Esta série não tem chamados.", "info"),
      legend(after));
  },
};
