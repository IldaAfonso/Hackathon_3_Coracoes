// Início: a história do produto, contada com os números da base real.
// 1) o histórico de hoje não atende; 2) o número de série liga os três
// times; 3) o que implantar.

import { api } from "../api.js";
import { chartBox, card, chip, metric, table } from "../components.js";
import { COLORS } from "../config.js";
import { h, render } from "../dom.js";
import { mountChart } from "../charts.js";
import { int, month, pct } from "../format.js";

function hero() {
  return h("section", { class: "hero" },
    h("h1", { text: "O histórico da máquina hoje não atende." }),
    h("p", { text: "Três times cuidam da mesma máquina, cada um num momento, e cada um registra num lugar. Ninguém enxerga a história inteira. O DNA da Máquina usa o número de série como chave para ligar a reclamação do consumidor, o laudo do técnico e a melhoria do P&D." }),
    h("div", { class: "hero__actions" },
      h("a", { class: "btn btn--light", href: "#/pd/dna", text: "Ver o DNA de uma máquina" }),
      h("a", { class: "btn btn--outline", href: "#/pd/melhorias", text: "A melhoria funcionou?" })));
}

function teamCard(team) {
  return card({ kicker: team.papel, flat: false },
    h("div", { class: "team__role", text: team.nome }),
    h("div", { class: "card__big", text: int(team.registros) }),
    h("p", { class: "card__muted", text: `registros · ${team.campo}` }),
    h("p", {}, h("strong", { text: "Registra: " }), team.registra),
    h("div", {}, team.exemplos.map((example) => chip(example))),
    h("div", { class: "team__today", text: `Hoje recebe: ${team.recebe_hoje}` }));
}

function teamsSection(times) {
  const link = h("div", { class: "teams__link", text: "nº de série" });
  const [cs, pos, pd] = times.times;
  const bond = times.ligacao;
  return h("section", { class: "section", "aria-labelledby": "times-titulo" },
    h("div", { class: "section__head" },
      h("div", {}, h("h2", { id: "times-titulo", text: "A chave que liga os três times" }),
        h("p", { class: "page-lead", text: "O número de série nasce na fábrica e acompanha a máquina em cada atendimento. É o único campo que os três times já têm em comum." }))),
    h("div", { class: "teams" }, teamCard(cs), link, teamCard(pos), link.cloneNode(true), teamCard(pd)),
    h("div", { class: "grid" },
      metric("Máquinas com chamado (série válida)", int(bond.maquinas_com_chamado)),
      metric("Chamados com número de série válido", pct(bond.pct_chamados_serie_valida), "só esses ligam à fábrica e à versão"),
      metric("Com registro técnico", pct(bond.pct_com_registro_tecnico), "o Pós-vendas respondeu pelo menos uma vez")));
}

function symptomValue(symptom) {
  if (symptom.valor === null) return "—";
  return symptom.unidade === "%" ? pct(symptom.valor) : int(symptom.valor);
}

function diagnosticSection(diagnostic) {
  return h("section", { class: "section", "aria-labelledby": "diag-titulo" },
    h("h2", { id: "diag-titulo", text: "Por que o histórico de hoje não atende" }),
    h("p", { class: "page-lead", text: `Calculado na base real: ${int(diagnostic.base.chamados)} chamados de ${int(diagnostic.base.maquinas)} máquinas.` }),
    h("div", { class: "grid" }, diagnostic.sintomas.map((symptom) =>
      card({ kicker: symptom.time, title: symptom.titulo, big: symptomValue(symptom), body: symptom.leitura }))));
}

function deploySection(diagnostic) {
  return h("section", { class: "band", "aria-labelledby": "implantar-titulo" },
    h("h2", { id: "implantar-titulo", text: "Pontos de melhoria que identificamos" }),
    h("p", { class: "page-lead", text: "Cada ponto traz a evidência medida na base real e o que o protótipo já demonstra. Os que dependem de sistemas da empresa (como o Salesforce) são recomendações, não parte do protótipo." }),
    h("div", { class: "grid grid--wide" }, diagnostic.melhorias_a_implantar.map((item) => {
      const found = diagnostic.sintomas.find((s) => s.id === item.evidencia);
      return card({ kicker: `Prioridade ${item.prioridade}`, title: item.titulo, body: item.porque },
        found ? h("p", {}, h("strong", { text: "Evidência: " }), `${symptomValue(found)} · ${found.titulo}`) : null,
        h("p", {}, h("strong", { text: "No protótipo: " }), item.no_prototipo),
        chip(item.dono, true), chip(item.tipo));
    })));
}

function overviewSection() {
  const body = h("div", {});
  const tabs = h("div", { class: "tabs", role: "group", "aria-label": "Modelo" });
  const options = [["Ambos", "Passione,Luna"], ["Passione", "Passione"], ["Luna", "Luna"]];
  let current = options[0][1];

  async function load() {
    render(body, h("p", { class: "card__muted", text: "Atualizando…" }));
    const data = await api.get(`/overview?modelos=${encodeURIComponent(current)}`);
    const monthly = chartBox("Chamados por mês, por modelo");
    const symptoms = chartBox("Sintomas mais relatados");
    const causes = chartBox("O que o técnico encontrou");
    render(body,
      h("div", { class: "grid" },
        metric("Chamados", int(data.totais.chamados)),
        metric("Máquinas com chamado", int(data.totais.maquinas)),
        metric("Voltaram em até 90 dias", pct(data.totais.reincidencia)),
        metric("Sem registro técnico", pct(data.totais.sem_registro_tecnico))),
      h("div", { class: "grid grid--wide" },
        card({ title: "Chamados por mês" }, monthly.box),
        card({ title: "Sintomas mais relatados (voz do consumidor)" }, symptoms.box),
        card({ title: "O que o técnico encontrou (voz do Pós-vendas)" }, causes.box)));
    drawOverview(data, { monthly, symptoms, causes });
  }

  options.forEach(([label, value], index) => {
    tabs.append(h("button", {
      type: "button", "aria-pressed": index === 0 ? "true" : "false", text: label,
      onClick: (event) => {
        current = value;
        tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", "false"));
        event.currentTarget.setAttribute("aria-pressed", "true");
        load();
      },
    }));
  });
  const section = h("section", { class: "section", "aria-labelledby": "visao-titulo" },
    h("h2", { id: "visao-titulo", text: "A base em segundos, não em dias" }), tabs, body);
  section.afterLoad = load;
  return section;
}

function drawOverview(data, boxes) {
  const labels = [...new Set(data.mensal.map((row) => row.mes))].sort();
  const models = [...new Set(data.mensal.map((row) => row.modelo))];
  const palette = [COLORS.burgundy, COLORS.orange, COLORS.sand];
  mountChart(boxes.monthly.canvas, {
    type: "line",
    data: {
      labels: labels.map(month),
      datasets: models.map((model, i) => ({
        label: model, borderColor: palette[i % palette.length], backgroundColor: palette[i % palette.length], tension: 0.25,
        data: labels.map((l) => data.mensal.find((r) => r.mes === l && r.modelo === model)?.n ?? 0),
      })),
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });
  const bars = (canvas, items, color) => mountChart(canvas, {
    type: "bar",
    data: { labels: items.map((i) => i.nome), datasets: [{ data: items.map((i) => i.n), backgroundColor: color }] },
    options: { indexAxis: "y", plugins: { legend: { display: false } } },
  });
  bars(boxes.symptoms.canvas, data.top_sintomas, COLORS.burgundy);
  bars(boxes.causes.canvas, data.top_causas, COLORS.orange);
}

function chronicSection(chronic) {
  return h("section", { class: "section", "aria-labelledby": "demo-titulo" },
    h("h2", { id: "demo-titulo", text: "Comece por uma máquina crônica" }),
    h("p", { class: "page-lead", text: `${int(chronic.total)} máquinas têm 3 ou mais chamados no período. Abra o DNA de uma delas e veja a história inteira.` }),
    table([
      { key: "serie", label: "Número de série", render: (r) => h("a", { href: `#/pd/dna/${encodeURIComponent(r.serie)}`, text: r.serie }) },
      { key: "modelo", label: "Modelo" },
      { key: "chamados", label: "Chamados", num: true },
      { key: "reincidencias", label: "Voltas em 90 dias", num: true },
    ], chronic.maquinas, "Máquinas crônicas"));
}

export const homePage = {
  title: "Início",
  menu: "Início",
  async render({ signal }) {
    const [times, diagnostic, chronic] = await Promise.all([
      api.get("/times", signal), api.get("/diagnostico", signal), api.get("/machines/chronic?limit=8", signal),
    ]);
    const overview = overviewSection();
    const page = h("div", {}, hero(), teamsSection(times), diagnosticSection(diagnostic),
      deploySection(diagnostic), overview, chronicSection(chronic));
    page.afterMount = () => overview.afterLoad().catch(() => {});
    return page;
  },
};
