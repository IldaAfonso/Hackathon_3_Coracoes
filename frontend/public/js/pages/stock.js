// Estoque × melhoria: ao implantar uma melhoria, levantar as máquinas
// ainda em estoque que precisam recebê-la ANTES de serem vendidas.
//
// Fonte de dados nova (posição de estoque por série, do ERP/WMS). P&D vê o
// levantamento e importa o arquivo; Pós-venda executa e marca "aplicada".

import { api } from "../api.js";
import { link } from "../areas.js";
import { badge, fold, metric, notice, pageHeader, table } from "../components.js";
import { h, render } from "../dom.js";
import { date, int } from "../format.js";

const TONE = { pendente: "bad", aplicada: "good", de_fabrica: "neutral", verificar: "warn" };
const TYPE_LABEL = { retrofit_campo: "Kit de campo", corte_serie: "Mudança de fábrica" };

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const anchor = h("a", { href: url, download: name });
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Lista de pendentes em CSV (;) para a ordem de serviço do estoque. */
function pendingCsv(data) {
  const header = ["Número de série", "Local", "Entrada no estoque", "Dias em estoque", "Fabricação", "Código do projeto da melhoria"];
  const lines = data.maquinas.filter((m) => m.status === "pendente").map((m) => [
    m.serie, m.local, m.data_entrada ?? "", m.dias_em_estoque ?? "", `${m.ano_fab}/S${String(m.semana_fab).padStart(2, "0")}`, data.melhoria.codigo,
  ].join(";"));
  return `\uFEFF${header.join(";")}\n${lines.join("\n")}\n`;
}

function markButton(machine, code, area, onDone) {
  if (area !== "posvenda" || !["pendente", "aplicada"].includes(machine.status)) return null;
  const applied = machine.status === "aplicada";
  const button = h("button", { class: "btn btn--ghost", type: "button", text: applied ? "Desfazer" : "Marcar aplicada" });
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await api.post("/estoque/aplicacoes", { serie: machine.serie, codigo: code, aplicada: !applied });
      onDone();
    } catch (error) {
      button.replaceWith(notice(error.message, "error"));
    }
  });
  return button;
}

function machinesTable(rows, data, area, onDone, caption, open) {
  return table([
    { key: "serie", label: "Número de série", render: (r) => h("a", { href: link("dna", r.serie), text: r.serie }) },
    { key: "local", label: "Local" },
    { key: "data_entrada", label: "Entrada no estoque", render: (r) => (r.data_entrada ? date(r.data_entrada) : "—") },
    { key: "dias_em_estoque", label: "Dias parada", num: true, render: (r) => (r.dias_em_estoque == null ? "—" : int(r.dias_em_estoque)) },
    { key: "ano_fab", label: "Fabricação", render: (r) => (r.ano_fab ? `${r.ano_fab} · S${String(r.semana_fab).padStart(2, "0")}` : "ilegível") },
    { key: "status", label: "Situação", render: (r) => badge(r.situacao_label, TONE[r.status] ?? "neutral") },
    ...(area === "posvenda" ? [{ key: "acao", label: "Ação", render: (r) => markButton(r, data.melhoria.codigo, area, onDone) }] : []),
  ], rows, caption, { open });
}

function surveyView(data, area, onDone) {
  const by = (status) => data.maquinas.filter((m) => m.status === status);
  const pending = by("pendente");
  const item = data.melhoria;
  return h("div", {},
    h("p", {}, badge(`Código do projeto ${item.codigo}`, "neutral"), " ",
      `${item.titulo} · ${item.modelo} · ${TYPE_LABEL[item.tipo] ?? item.tipo} · boletim de ${date(item.data_documento)}`),
    notice(data.regra, "info"),
    h("div", { class: "grid" },
      metric("Aplicar antes de vender", int(data.por_status.pendente), `de ${int(data.total_do_modelo)} ${item.modelo} em estoque`),
      metric("Já aplicada no estoque", int(data.por_status.aplicada), "código registrado ou marcado aqui"),
      metric("Já sai de fábrica com ela", int(data.por_status.de_fabrica), "fabricadas depois do corte"),
      metric("Verificar", int(data.por_status.verificar), "série ilegível: conferir a etiqueta")),
    h("div", { class: "section" },
      pending.length ? h("p", {},
        h("button", { class: "btn btn--outline", type: "button", text: "Baixar pendentes (.csv) para a ordem de serviço",
          onClick: () => download(`estoque_${item.codigo}.csv`, pendingCsv(data)) })) : notice("Nenhuma máquina em estoque precisa desta melhoria.", "ok"),
      pending.length ? machinesTable(pending, data, area, onDone, "Máquinas para atualizar antes da venda (as que entraram primeiro saem primeiro)", false) : null,
      data.por_local.length ? table([
        { key: "local", label: "Local" },
        { key: "pendentes", label: "Máquinas pendentes", num: true, render: (r) => int(r.pendentes) },
      ], data.por_local, "Pendentes por local") : null,
      data.pecas_necessarias.length ? table([
        { key: "peca", label: "Peça do boletim" },
        { key: "quantidade", label: "Separar (1 por máquina pendente)", num: true, render: (r) => int(r.quantidade) },
      ], data.pecas_necessarias, "Peças a separar") : null,
      by("aplicada").length ? machinesTable(by("aplicada"), data, area, onDone, "Já aplicadas no estoque", false) : null,
      by("verificar").length ? machinesTable(by("verificar"), data, area, onDone, "Verificar a etiqueta (série ilegível)", false) : null));
}

function importForm(onDone) {
  const file = h("input", { id: "estoque-arquivo", name: "file", type: "file", accept: ".xlsx,.csv", required: true });
  const button = h("button", { class: "btn", type: "submit", text: "Importar posição de estoque" });
  const out = h("div", { "aria-live": "polite" });
  const form = h("form", {},
    h("p", { class: "card__muted", text: "Exportação do ERP/WMS com uma linha por máquina. Só \"Número de série\" é obrigatório; Modelo, Local, Data de entrada no estoque, Situação (em estoque, reservada, vendida) e Melhorias aplicadas (códigos do projeto) enriquecem o levantamento. O arquivo substitui a posição anterior." }),
    h("p", {}, h("a", { href: "/api/estoque/modelo.csv", download: "modelo_estoque.csv", text: "Baixar o modelo do arquivo (.csv)" })),
    h("div", { class: "field" }, h("label", { for: "estoque-arquivo", text: "Arquivo (.xlsx ou .csv)" }), file), button, out);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!file.files.length) return;
    button.disabled = true;
    try {
      const body = new FormData();
      body.append("file", file.files[0]);
      const done = await api.upload("/estoque/importar", body);
      render(out, notice(`Posição importada: ${int(done.em_estoque)} máquinas em estoque.`, "ok"));
      setTimeout(onDone, 800);
    } catch (error) {
      render(out, notice(error.message, "error"));
    } finally {
      button.disabled = false;
    }
  });
  return form;
}

export const stockPage = {
  title: "Estoque",
  async render({ params, area, signal }) {
    const overview = await api.get("/estoque", signal);
    if (!overview.melhorias.length) return h("div", {}, pageHeader("Estoque", "Ainda não há melhorias cadastradas."));
    const wanted = params[0] ?? overview.melhorias[0].id;
    const select = h("select", { id: "estoque-melhoria" }, overview.melhorias.map((m) =>
      h("option", { value: m.id, selected: m.id === wanted, text: `${m.codigo} · ${m.titulo} (${m.modelo})` })));
    select.addEventListener("change", () => { window.location.hash = link("estoque", select.value); });

    const result = h("div", { "aria-live": "polite" });
    const reload = async () => render(result, surveyView(await api.get(`/estoque/melhoria/${encodeURIComponent(select.value)}`), area, reload));
    render(result, surveyView(await api.get(`/estoque/melhoria/${encodeURIComponent(wanted)}`, signal), area, reload));

    const source = h("div", { class: "grid" },
      metric("Máquinas em estoque", int(overview.em_estoque), `${int(overview.vendidas_ignoradas)} vendidas ficam fora`),
      ...Object.entries(overview.por_modelo).map(([model, count]) => metric(model, int(count), "em estoque")));
    const places = table([
      { key: "local", label: "Local" }, { key: "n", label: "Máquinas", num: true, render: (r) => int(r.n) },
    ], Object.entries(overview.por_local).map(([local, n]) => ({ local, n })), "Máquinas em estoque por local");

    return h("div", {},
      pageHeader("Estoque × melhoria",
        area === "posvenda"
          ? "Máquinas ainda em estoque que precisam da melhoria antes de serem vendidas. Aplique, marque como aplicada e a lista do P&D se atualiza."
          : "Ao implantar uma melhoria, levante as máquinas já fabricadas e ainda paradas no estoque: elas saíram da fábrica sem a melhoria e precisam recebê-la antes da venda."),
      overview.aviso ? notice(overview.aviso, "error") : null,
      h("div", { class: "field" }, h("label", { for: "estoque-melhoria", text: "Melhoria (código do projeto)" }), select),
      result,
      h("section", { class: "section" },
        fold("A fonte de estoque", [source, places],
          { hint: `${overview.fonte === "exemplo" ? "exemplo fictício" : "importada"} · atualizada em ${overview.atualizado_em.replace("T", " ")}` })),
      area === "pd" ? h("section", { class: "band" }, fold("Importar a posição de estoque (ERP/WMS)", importForm(() => window.dispatchEvent(new HashChangeEvent("hashchange"))))) : null);
  },
};
