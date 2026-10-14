// Dados: qualidade da base atual e importação de uma nova extração .xlsx.

import { api } from "../api.js";
import { notice, pageHeader, table } from "../components.js";
import { h, render } from "../dom.js";
import { int, pct } from "../format.js";

export const dataPage = {
  title: "Dados",
  menu: "Dados",
  async render({ signal }) {
    const quality = await api.get("/quality", signal);
    const result = h("div", { "aria-live": "polite" });
    const file = h("input", { id: "planilha", name: "file", type: "file", accept: ".xlsx", required: true });
    const button = h("button", { class: "btn", type: "submit", text: "Processar e atualizar" });
    const form = h("form", {},
      h("div", { class: "field" }, h("label", { for: "planilha", text: "Nova extração do Salesforce (.xlsx, mesmo layout)" }), file), button);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!file.files.length) return;
      button.disabled = true;
      render(result, notice("Processando a planilha e atualizando todas as análises…", "info"));
      try {
        const body = new FormData();
        body.append("file", file.files[0]);
        const done = await api.upload("/import", body);
        render(result, notice(`${int(done.lidos)} chamados lidos; a base passou de ${int(done.antes)} para ${int(done.depois)}. Chamados repetidos são atualizados, não duplicados.`, "ok"));
      } catch (error) {
        render(result, notice(error.message, "error"));
      } finally {
        button.disabled = false;
      }
    });
    return h("div", {},
      pageHeader("Dados", "Qualidade da base atual e importação de uma nova extração. Registros imperfeitos não são apagados: recebem uma marca de qualidade e aparecem aqui."),
      table([
        { key: "controle", label: "Controle de qualidade" },
        { key: "registros", label: "Registros", num: true, render: (r) => int(r.registros) },
        { key: "percentual", label: "% da base", num: true, render: (r) => pct(r.percentual) },
      ], quality.itens, "Qualidade dos dados"),
      h("section", { class: "band" }, h("h2", { text: "Importar nova base" }),
        h("p", { class: "page-lead", text: "Envie uma nova extração. As análises são atualizadas na hora." }), form, result));
  },
};
