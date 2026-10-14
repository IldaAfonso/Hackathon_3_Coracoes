// Entrada: cada time escolhe a sua área e passa a ver só o menu dela.
// P&D decide e mede as melhorias; Pós-venda executa no campo e no estoque.

import { AREAS } from "../areas.js";
import { h } from "../dom.js";

// O que cada item do menu resolve, em uma linha (na língua de quem usa).
const WHAT = {
  pd: {
    melhorias: "A melhoria funcionou? Antes × depois com intervalo de confiança.",
    boletins: "Inserir o boletim em PDF e consultar os cadastrados, com o código do projeto da melhoria.",
    estoque: "Máquinas ainda em estoque que precisam da melhoria antes de serem vendidas.",
    dna: "A história de uma máquina pelo número de série, com modelo e imagem.",
    risco: "Chamados recentes com maior chance de voltar em 90 dias.",
    assistente: "Pergunte em português; a IA consulta as análises e cita os números.",
  },
  posvenda: {
    dna: "Antes de sair para o atendimento: o que já foi feito nesta máquina.",
    boletins: "Os boletins cadastrados e o código a registrar no chamado.",
    estoque: "Máquinas em estoque a atualizar antes da venda; marcar como aplicada.",
    risco: "Quem acompanhar antes de o consumidor ligar de novo.",
    assistente: "Tire dúvidas sobre uma máquina ou um sintoma antes do atendimento.",
  },
};

function areaCard(key) {
  const info = AREAS[key];
  return h("article", { class: `area area--${key}` },
    h("div", { class: "card__kicker", text: info.persona }),
    h("h2", { class: "area__title", text: info.label }),
    h("p", { class: "area__question", text: `“${info.pergunta}”` }),
    h("ul", { class: "area__list" }, info.pages.map(([page, label]) => h("li", {},
      h("a", { href: `#/${key}/${page}`, text: label }),
      h("span", { class: "card__muted", text: ` — ${WHAT[key][page] ?? ""}` })))),
    h("a", { class: "btn", href: `#/${key}`, text: `Entrar no ${info.label}` }));
}

export const entryPage = {
  title: "",
  async render() {
    return h("div", {},
      h("section", { class: "entry__head" },
        h("h1", { text: "DNA da Máquina" }),
        h("p", { class: "page-lead", text: "O histórico de cada máquina TRES, ligado pelo número de série. Escolha a sua área: cada uma mostra só o que o seu time usa." })),
      h("div", { class: "areas" }, Object.keys(AREAS).map(areaCard)),
      h("p", { class: "entry__more" },
        h("a", { href: "#/visao-geral", text: "Visão geral do desafio (os números da base)" }), " · ",
        h("a", { href: "#/dados", text: "Importar base de chamados" })));
  },
};
