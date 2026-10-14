// Boletins: o P&D envia o PDF, revisa o que foi lido, vê os dados
// relacionados e registra a melhoria, que ganha o CÓDIGO DO PROJETO DA
// MELHORIA (MEL-...). Os dois times veem a lista de cadastrados; só o
// P&D insere (no Pós-venda a página é somente leitura).

import { api } from "../api.js";
import { hasPage, link } from "../areas.js";
import { badge, fold, metric, notice, pageHeader, table } from "../components.js";
import { h, render } from "../dom.js";
import { date, int } from "../format.js";

const TYPE_LABEL = { retrofit_campo: "Kit de campo", corte_serie: "Mudança de fábrica" };
const LINK_LABEL = {
  serie: ["por série", "good", "Ligado aos chamados pela série de fabricação."],
  registrada: ["registrado", "good", "Chamados já trazem este código."],
  inferida: ["inferido", "warn", "Nenhum chamado traz o código ainda; o vínculo é inferido por palavras."],
};

const MODELS = ["Passione", "Luna"];
const TYPES = [
  ["retrofit_campo", "Kit de campo (série indiferente)"],
  ["corte_serie", "Mudança de fábrica (a partir de uma série)"],
];

const field = (id, label, control) => h("div", { class: "field" }, h("label", { for: id, text: label }), control);
const input = (id, value = "", extra = {}) => h("input", { id, name: id, value, ...extra });
const select = (id, options, current) => h("select", { id, name: id },
  options.map(([value, label]) => h("option", { value, text: label, selected: value === current })));
const splitTerms = (text) => text.split(",").map((t) => t.trim()).filter((t) => t.length >= 3);

/** Um boletim cadastrado: o código do projeto em destaque e o detalhe ao abrir. */
function bulletinItem(item, area) {
  const [label, tone, explanation] = LINK_LABEL[item.vinculo.origem] ?? ["—", "neutral", ""];
  const details = h("dl", { class: "facts" },
    h("dt", { text: "Código do projeto da melhoria" }), h("dd", {}, h("code", { class: "code", text: item.codigo })),
    h("dt", { text: "Documento" }), h("dd", { text: item.documento }),
    h("dt", { text: "Tipo" }), h("dd", { text: TYPE_LABEL[item.tipo] ?? item.tipo }),
    item.serie_inicial ? [h("dt", { text: "Vale a partir da série" }), h("dd", { text: item.serie_inicial })] : null,
    h("dt", { text: "Objetivo" }), h("dd", { text: item.objetivo || "—" }),
    h("dt", { text: "Peças" }), h("dd", {}, item.pecas.length ? h("ul", {}, item.pecas.map((piece) => h("li", { text: piece }))) : "—"),
    h("dt", { text: "Vínculo com os chamados" }), h("dd", {}, badge(label, tone), ` ${explanation}`,
      item.vinculo.chamados_com_codigo ? ` (${int(item.vinculo.chamados_com_codigo)} chamados)` : ""));
  const summary = `${item.codigo} · ${item.titulo}`;
  return fold(summary, [details,
    hasPage(area, "melhorias") ? h("p", {}, h("a", { href: link("melhorias", item.id), text: "Ver se a melhoria funcionou" })) : null],
  { hint: `${item.modelo} · ${TYPE_LABEL[item.tipo] ?? item.tipo} · ${date(item.data_documento)}` });
}

/** Lista dos cadastrados, que abre e fecha; cada boletim também abre e fecha. */
async function registeredList(area, signal) {
  const rows = await api.get("/boletins/cadastrados", signal);
  const body = rows.length
    ? h("div", { class: "fold-list" }, rows.map((item) => bulletinItem(item, area)))
    : h("p", { class: "card__muted", text: "Nenhum boletim cadastrado ainda." });
  return fold("Boletins cadastrados", body, { open: true, count: rows.length, hint: "código do projeto da melhoria, modelo, tipo e data" });
}

function reviewForm(read, result, onSaved) {
  const title = input("titulo", read.titulo, { required: true, maxlength: "120" });
  const model = select("modelo", MODELS.map((m) => [m, m]), read.modelo ?? MODELS[0]);
  const kind = select("tipo", TYPES, read.tipo);
  const serial = input("serie", read.serie_inicial ?? "", { placeholder: "G5PS000210224033" });
  const date = input("data", read.data_documento ?? "", { type: "date", required: true });
  const terms = input("termos", read.termos_sugeridos.join(", "));
  const preview = h("div", { "aria-live": "polite" });
  const registerButton = h("button", { class: "btn", type: "submit", text: "Registrar melhoria" });
  const previewButton = h("button", { class: "btn btn--outline", type: "button", text: "Ver dados relacionados" });

  previewButton.addEventListener("click", async () => {
    const list = splitTerms(terms.value);
    if (!list.length) return render(preview, notice("Informe ao menos um termo de 3 letras ou mais.", "error"));
    render(preview, notice("Procurando nos chamados…", "info"));
    try {
      const data = await api.post("/boletins/previa", { modelo: model.value, termos: list, pecas: read.pecas });
      render(preview, relatedData(data));
    } catch (error) {
      render(preview, notice(error.message, "error"));
    }
  });

  const form = h("form", {},
    field("titulo", "Assunto do boletim", title),
    field("modelo", "Modelo", model), field("tipo", "Tipo (definido pelo campo Número de Série)", kind),
    field("serie", "Série inicial (só para mudança de fábrica)", serial),
    field("data", "Data do boletim", date),
    field("termos", "Termos para buscar no texto do técnico (separe por vírgula)", terms),
    h("p", { class: "page-lead", text: `Peças do boletim: ${read.pecas.length ? read.pecas.join(" · ") : "nenhuma lida"}` }),
    previewButton, preview, registerButton);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    registerButton.disabled = true;
    try {
      const done = await api.post("/improvements", {
        titulo: title.value, modelo: model.value, tipo: kind.value,
        serie_inicial: kind.value === "corte_serie" ? serial.value || null : null,
        data_documento: date.value, pecas: read.pecas, termos_evidencia: splitTerms(terms.value),
        documento: `Boletim Técnico ${date.value}${read.revisao ? `, rev. ${read.revisao}` : ""}`,
      });
      render(result, notice(`Boletim cadastrado. Código do projeto da melhoria: ${done.codigo}.`, "ok"),
        h("p", {}, "Imprima este código no boletim e na etiqueta do kit; o técnico o escolhe no chamado. ",
          h("a", { href: link("melhorias", done.id), text: "Ver o resultado da melhoria" })));
      onSaved();
    } catch (error) {
      render(result, notice(error.message, "error"));
    } finally {
      registerButton.disabled = false;
    }
  });
  return form;
}

function relatedData(data) {
  return h("div", {},
    h("div", { class: "grid" },
      metric("Chamados relacionados", int(data.chamados_relacionados), `de ${int(data.chamados_modelo)} do modelo`),
      metric("Máquinas", int(data.maquinas), "com série válida")),
    h("p", {}, badge("inferido", "warn"), ` ${data.aviso}`),
    data.pecas_citadas.length ? table([
      { key: "peca", label: "Peça do boletim" },
      { key: "chamados", label: "Chamados que citam o código", num: true, render: (r) => int(r.chamados) },
    ], data.pecas_citadas, "Peças citadas nos chamados") : null,
    data.mensal.length ? table([
      { key: "mes", label: "Mês" },
      { key: "chamados", label: "Chamados", num: true, render: (r) => int(r.chamados) },
    ], data.mensal, "Chamados relacionados por mês") : null);
}

export const bulletinsPage = {
  title: "Boletins",
  async render({ area, signal }) {
    const canInsert = area !== "posvenda"; // Pós-venda: somente a lista
    const listBox = h("div", {}, await registeredList(area, signal));
    const refresh = async () => render(listBox, await registeredList(area));
    if (!canInsert) {
      return h("div", {},
        pageHeader("Boletins cadastrados", "Os boletins técnicos do P&D, cada um com o código do projeto da melhoria. Use o código no chamado quando aplicar o kit ou a correção: é assim que o P&D mede se a melhoria funcionou."),
        listBox);
    }
    const result = h("div", { "aria-live": "polite" });
    const review = h("div");
    const file = h("input", { id: "boletim", name: "file", type: "file", accept: ".pdf", required: true });
    const button = h("button", { class: "btn", type: "submit", text: "Ler boletim" });
    const upload = h("form", {}, field("boletim", "Boletim técnico (PDF, até 5 MB)", file), button);
    upload.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!file.files.length) return;
      button.disabled = true;
      render(result);
      render(review, notice("Lendo o PDF…", "info"));
      try {
        const body = new FormData();
        body.append("file", file.files[0]);
        const read = await api.upload("/boletins/analisar", body);
        render(review, ...read.avisos.map((a) => notice(a, "info")), reviewForm(read, result, refresh));
      } catch (error) {
        render(review, notice(error.message, "error"));
      } finally {
        button.disabled = false;
      }
    });
    return h("div", {},
      pageHeader("Boletins", "Insira o boletim técnico em PDF: eu leio modelo, data, assunto e peças; você revisa, vê os dados relacionados e cadastra. Cada boletim cadastrado ganha o código do projeto da melhoria. O PDF não é guardado."),
      h("section", { class: "band" }, fold("Inserir novo boletim", [upload, review, result], { open: true, hint: "PDF até 5 MB" })),
      h("section", { class: "section" }, listBox));
  },
};
