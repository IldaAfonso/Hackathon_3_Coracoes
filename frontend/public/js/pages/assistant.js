// Assistente de engenharia com Amazon Bedrock.
//
// A pessoa pergunta em português; o modelo (API /assistant/perguntar)
// escolhe as análises do projeto, lê os números e redige. A resposta mostra
// quais análises foram usadas. Sem Bedrock (desligado ou fora do ar), as
// respostas prontas e o parecer técnico por regras continuam funcionando.

import { api } from "../api.js";
import { notice, pageHeader } from "../components.js";
import { cleanSerial } from "../cora.js";
import { h, render } from "../dom.js";

// Nome legível de cada análise (ferramenta) que o modelo pode chamar.
const TOOL_LABELS = {
  listar_melhorias: "lista de melhorias",
  listar_sintomas: "lista de sintomas",
  avaliar_melhoria: "avaliação da melhoria",
  historico_maquina: "DNA da máquina",
  contar_chamados: "contagem de chamados",
  duas_vozes: "duas vozes",
  radar: "radar",
  modos_de_falha: "modos de falha",
  maquinas_cronicas: "máquinas crônicas",
  qualidade_dos_dados: "qualidade dos dados",
};

const SUGGESTIONS = [
  "O kit de adaptação hidráulica reduziu os retornos? Cite as premissas.",
  "A bandeja de cápsulas funcionou?",
  "O que está crescendo no Luna nos últimos 3 meses?",
  "O que o técnico encontra quando o consumidor diz 'Máquina vazando'?",
];

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  const link = h("a", { href: url, download: name });
  link.click();
  URL.revokeObjectURL(url);
}

function toolsUsed(names) {
  const unique = [...new Set(names)].map((n) => TOOL_LABELS[n] ?? n);
  return unique.length ? `Análises consultadas: ${unique.join(", ")}.` : "Nenhuma análise consultada.";
}

/** Chat com o Bedrock: o modelo escolhe as análises e redige. */
function chatPanel(serial) {
  const chat = h("div", { class: "chat", "aria-live": "polite" });
  const input = h("textarea", { id: "pergunta", rows: 3, maxlength: 500, required: true,
    placeholder: serial ? "Ex.: Resuma o DNA desta máquina e diga quais melhorias se aplicam."
      : "Ex.: O kit de adaptação hidráulica reduziu os retornos?" });
  const send = h("button", { class: "btn", type: "submit", text: "Perguntar" });

  async function ask(question) {
    send.disabled = true;
    chat.append(h("div", { class: "bubble bubble--user", text: question }));
    const waiting = h("div", { class: "bubble bubble--bot", text: "Consultando as análises…" });
    chat.append(waiting);
    try {
      const reply = await api.post("/assistant/perguntar", { pergunta: question, serie: serial || null });
      waiting.replaceWith(h("div", { class: "bubble bubble--bot" }, reply.texto,
        h("span", { class: "bubble__meta", text: `Amazon Bedrock · ${toolsUsed(reply.ferramentas)}` })));
    } catch (error) {
      waiting.replaceWith(notice(error.message, "error"));
    } finally {
      send.disabled = false;
    }
  }

  const form = h("form", {},
    h("div", { class: "field" }, h("label", { for: "pergunta", text: "Sua pergunta" }), input), send);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (question.length < 3 || send.disabled) return;
    input.value = "";
    ask(question).then(() => input.focus());
  });

  const suggestions = h("div", { class: "section" },
    h("p", { class: "card__muted", text: "Sugestões:" }),
    SUGGESTIONS.map((q) => h("button", { class: "btn btn--outline", type: "button", text: q,
      onClick: () => { if (!send.disabled) ask(q); } })));

  return h("section", { class: "section", "aria-labelledby": "chat-titulo" },
    h("h2", { id: "chat-titulo", text: "Pergunte ao assistente" }),
    h("p", { class: "card__muted", text: serial
      ? `Contexto: máquina de série ${serial}.`
      : "Os números vêm das análises do projeto; a resposta diz quais foram consultadas." }),
    form, suggestions, chat);
}

function aiOff() {
  return h("section", { class: "section" },
    notice("A IA generativa está desligada neste ambiente (DNA_USE_BEDROCK=1 liga). As respostas prontas abaixo funcionam sem ela."));
}

/** Plano B sem IA: perguntas prontas e parecer por regras. */
function rulesFallback(presets, catalog) {
  const answers = h("div", { class: "chat", "aria-live": "polite" });

  async function answer(question) {
    const waiting = h("div", { class: "bubble bubble--bot", text: "Consultando as análises…" });
    answers.prepend(waiting);
    try {
      const reply = await api.post("/assistant/preset", { pergunta: question });
      waiting.replaceWith(h("div", { class: "bubble bubble--bot" }, `${question}\n\n${reply.texto}`,
        h("span", { class: "bubble__meta", text: "Resposta por regras, direto das análises (sem IA)." })));
    } catch (error) {
      waiting.replaceWith(notice(error.message, "error"));
    }
  }

  const memoOut = h("div", { "aria-live": "polite" });
  const select = h("select", { id: "parecer-melhoria" }, catalog.map((i) => h("option", { value: i.id, text: i.titulo })));
  const memoButton = h("button", { class: "btn", type: "button", text: "Gerar parecer" });
  memoButton.addEventListener("click", async () => {
    memoButton.disabled = true;
    try {
      const memo = await api.post("/assistant/parecer", { id_melhoria: select.value });
      render(memoOut, h("pre", { class: "card", text: memo.texto }),
        h("button", { class: "btn btn--outline", type: "button", text: "Baixar parecer (.txt)", onClick: () => download(`parecer_${select.value}.txt`, memo.texto) }));
    } catch (error) {
      render(memoOut, notice(error.message, "error"));
    } finally {
      memoButton.disabled = false;
    }
  });

  return h("div", {},
    h("section", { class: "section" }, h("h2", { text: "Respostas prontas (sem IA)" }),
      h("div", {}, presets.map((question) => h("button", { class: "btn btn--outline", type: "button", text: question, onClick: () => answer(question) }))),
      answers),
    h("section", { class: "band" }, h("h2", { text: "Parecer técnico para o P&D (por regras)" }),
      h("p", { class: "card__muted", text: "Para um parecer redigido pela IA, pergunte acima: \"escreva o parecer técnico da melhoria G5-ADAPT-HIDR-2022\"." }),
      h("div", { class: "field--inline" }, h("div", { class: "field" }, h("label", { for: "parecer-melhoria", text: "Melhoria" }), select), memoButton),
      memoOut));
}

export const assistantPage = {
  title: "Assistente",
  menu: "Assistente",
  async render({ params, signal }) {
    const serial = cleanSerial(params[0]);
    const [bedrock, presets, catalog] = await Promise.all([
      api.get("/assistant/bedrock", signal).catch(() => ({ ligado: false })),
      api.get("/assistant/presets", signal), api.get("/impact", signal)]);

    return h("div", {},
      pageHeader("Assistente de engenharia",
        "Pergunte em português sobre melhorias, sintomas e máquinas. A IA (Amazon Bedrock) não calcula nada: ela escolhe as análises já testadas do projeto, lê os números e responde citando de onde vieram."),
      bedrock.ligado ? chatPanel(serial) : aiOff(),
      rulesFallback(presets, catalog));
  },
};
