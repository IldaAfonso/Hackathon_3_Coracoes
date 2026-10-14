// Duas vozes: o que o consumidor relatou × o que o técnico encontrou.

import { api } from "../api.js";
import { card, heatTable, pageHeader, autoTable } from "../components.js";
import { h } from "../dom.js";
import { pct } from "../format.js";

export const voicesPage = {
  title: "Duas vozes",
  menu: "Duas vozes",
  async render({ signal }) {
    const data = await api.get("/voices", signal);
    return h("div", {},
      pageHeader("Duas vozes", "O mesmo chamado, duas histórias: o Customer Success registra o sintoma com as palavras do consumidor; o técnico registra o que encontrou. Quando não batem, quem analisa não sabe em qual confiar."),
      card({ title: "Para cada sintoma relatado, o que o técnico encontrou", body: "Cada linha soma 100%. Quanto mais forte a cor, mais frequente a causa." },
        heatTable({ rowLabels: data.sintomas, colLabels: data.causas, values: data.valores, format: (v) => pct(v, 0), corner: "Sintoma relatado" })),
      h("section", { class: "section" }, h("h2", { text: "Quando as vozes batem" }),
        autoTable(data.concordancia, { concordancia: (v) => pct(v, 0), sem_defeito: (v) => pct(v, 0) }, "Concordância por sintoma", {
          sintoma_cs: "Sintoma relatado", chamados: "Chamados", concordancia: "Consumidor e técnico concordam", sem_defeito: "Técnico não achou defeito" })));
  },
};
