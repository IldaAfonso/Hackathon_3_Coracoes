// Peças reutilizáveis da interface. Todas devolvem elementos DOM.

import { h } from "./dom.js";

export const pageHeader = (title, lead) => h("header", {}, h("h1", { class: "page-title", text: title }), lead ? h("p", { class: "page-lead", text: lead }) : null);

export const badge = (text, tone = "neutral") => h("span", { class: `badge badge--${tone}`, text });

export const chip = (text, orange = false) => h("span", { class: orange ? "chip chip--orange" : "chip", text });

export function metric(label, value, hint) {
  return h("div", { class: "metric" },
    h("div", { class: "metric__label", text: label }),
    h("div", { class: "metric__value", text: value }),
    hint ? h("div", { class: "metric__hint", text: hint }) : null);
}

/** Cartão com kicker, título, número grande e corpo opcionais. */
export function card({ kicker, title, big, body, flat = false, className = "" }, ...children) {
  return h("article", { class: `card${flat ? " card--flat" : ""} ${className}`.trim() },
    kicker ? h("div", { class: "card__kicker", text: kicker }) : null,
    title ? h("h3", { text: title }) : null,
    big !== undefined ? h("div", { class: "card__big", text: big }) : null,
    body ? h("p", { class: "card__muted", text: body }) : null,
    children);
}

/**
 * Bloco que abre e fecha (<details>), para listas não alongarem a página.
 * Fechado por padrão; o resumo mostra o título e, se houver, a contagem.
 * @param {string} title
 * @param {Node|Node[]} content
 * @param {{open?: boolean, count?: number|string|null, hint?: string}} [options]
 */
export function fold(title, content, { open = false, count = null, hint = "" } = {}) {
  return h("details", { class: "fold", open },
    h("summary", { class: "fold__summary" },
      h("span", { class: "fold__title", text: title }),
      count !== null && count !== undefined ? h("span", { class: "fold__count", text: String(count) }) : null,
      hint ? h("span", { class: "fold__hint", text: hint }) : null),
    h("div", { class: "fold__body" }, content));
}

/** Barra "abrir todas / fechar todas" quando a página tem 2+ listas. */
export function foldToolbar(content) {
  if (!(content instanceof Element) || content.querySelectorAll("details.fold").length < 2) return null;
  const toggle = (open) => () => content.querySelectorAll("details.fold").forEach((item) => { item.open = open; });
  return h("div", { class: "fold-toolbar", role: "group", "aria-label": "Listas da página" },
    h("button", { class: "btn btn--ghost", type: "button", text: "Abrir todas as listas", onClick: toggle(true) }),
    h("button", { class: "btn btn--ghost", type: "button", text: "Fechar todas", onClick: toggle(false) }));
}

/**
 * Tabela acessível. Com legenda, vira uma lista que abre e fecha (o resumo
 * é a legenda com o número de linhas); `{ fold: false }` desliga isso.
 * @param {{key:string,label:string,num?:boolean,render?:(row:Object)=>Node|string}[]} columns
 * @param {Object[]} rows
 * @param {string} [caption]
 * @param {{fold?: boolean, open?: boolean}} [options]
 */
export function table(columns, rows, caption, { fold: folded = true, open = false } = {}) {
  const head = h("tr", {}, columns.map((c) => h("th", { scope: "col", class: c.num ? "num" : "", text: c.label })));
  const body = rows.map((row) => h("tr", {}, columns.map((c) => {
    const content = c.render ? c.render(row) : row[c.key];
    return h("td", { class: c.num ? "num" : "" }, content ?? "—");
  })));
  const grid = h("div", { class: "table-wrap" },
    h("table", {}, caption ? h("caption", { class: "sr-only", text: caption }) : null,
      h("thead", {}, head), h("tbody", {}, body)));
  return caption && folded ? fold(caption, grid, { open, count: rows.length }) : grid;
}

/** Matriz com intensidade de cor proporcional ao valor (0 a 1). */
export function heatTable({ rowLabels, colLabels, values, format, corner = "" }) {
  const head = h("tr", {}, h("th", { text: corner }), colLabels.map((c) => h("th", { scope: "col", class: "num", text: c })));
  const rows = rowLabels.map((label, i) => h("tr", {}, h("th", { scope: "row", text: label }),
    values[i].map((value) => {
      const cell = h("td", { class: "heat", text: value === null ? "—" : format(value) });
      cell.style.setProperty("--v", String(Math.min(1, Math.max(0, value ?? 0))));
      return cell;
    })));
  return h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, head), h("tbody", {}, rows)));
}

export const loading = () => h("div", { role: "status", "aria-label": "Carregando" },
  h("div", { class: "skeleton" }), h("div", { class: "skeleton" }));

export function errorBox(error, onRetry) {
  return h("div", { class: "alert alert--error", role: "alert" },
    h("strong", { text: "Algo deu errado. " }), error.message,
    onRetry ? h("p", {}, h("button", { class: "btn btn--outline", type: "button", onClick: onRetry, text: "Tentar de novo" })) : null);
}

export const notice = (text, tone = "info") => h("div", { class: `alert alert--${tone}`, role: tone === "error" ? "alert" : "status", text });

/** Um canvas dentro de um contêiner com altura fixa (exigência do Chart.js). */
export function chartBox(label, tall = false) {
  const canvas = h("canvas", { role: "img", "aria-label": label });
  return { box: h("div", { class: tall ? "chart chart--tall" : "chart" }, canvas), canvas };
}

/**
 * Tabela a partir das chaves do primeiro registro (para análises do núcleo
 * que devolvem colunas variáveis). `formats` mapeia chave -> função de formato
 * e `labels` mapeia chave -> cabeçalho legível.
 */
export function autoTable(rows, formats = {}, caption = "", labels = {}) {
  if (!rows.length) return h("p", { class: "card__muted", text: "Sem registros para mostrar." });
  const columns = Object.keys(rows[0]).map((key) => ({
    key,
    label: labels[key] ?? key.replaceAll("_", " "),
    num: typeof rows[0][key] === "number",
    render: (row) => (formats[key] ? formats[key](row[key], row) : row[key]),
  }));
  return table(columns, rows, caption);
}
