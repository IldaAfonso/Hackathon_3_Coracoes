// DNA da máquina: a história de uma série, com as vozes dos três times.

import { api } from "../api.js";
import { link } from "../areas.js";
import { badge, card, fold, metric, notice, pageHeader, table } from "../components.js";
import { IMPROVEMENT_STATUS, MACHINE_MODELS, MODEL_FALLBACK_IMAGE } from "../config.js";
import { h, render } from "../dom.js";
import { date, int, pct, plural } from "../format.js";

function voice(who, children) {
  return h("div", { class: "voice" }, h("div", { class: "voice__who", text: who }), children);
}

function eventCard(event) {
  const tech = event.tecnico;
  const technicalText = [tech.causa, tech.conclusao].filter(Boolean);
  const flags = [
    event.voltou_em_90_dias ? badge("Voltou em até 90 dias", "bad") : null,
    event.vozes_concordam === true ? badge("Vozes batem", "good") : null,
    event.vozes_concordam === false ? badge("Vozes divergem", "warn") : null,
    event.adaptacao_hidraulica ? badge("Kit hidráulico", "neutral") : null,
  ];
  return h("li", { class: "event" },
    h("div", { class: "event__head" },
      h("span", { class: "event__date", text: `${date(event.data)} · caso ${event.caso ?? "—"}` }),
      h("span", {}, flags)),
    h("div", { class: "voices" },
      voice("Customer Success · o consumidor disse", h("p", { text: event.consumidor ?? "—" })),
      voice("Pós-vendas · o técnico encontrou",
        technicalText.length
          ? technicalText.map((line) => h("p", { text: line }))
          : h("p", { class: "card__muted", text: "Sem registro técnico neste chamado." }))),
    event.dias_desde_anterior != null
      ? h("p", { class: "card__muted", text: `${plural(event.dias_desde_anterior, "dia", "dias")} desde o chamado anterior` }) : null);
}

/**
 * Modelo da máquina com nome comercial e imagem. Se a imagem oficial não
 * estiver em /assets/modelos/, troca pelo desenho neutro (sem quebrar).
 */
function modelCard(model, sheet) {
  const info = MACHINE_MODELS[model] ?? { nome: model ?? "Modelo não identificado", linha: "", imagem: MODEL_FALLBACK_IMAGE, ilustracao: MODEL_FALLBACK_IMAGE };
  const picture = h("img", { class: "model__img", src: info.imagem, alt: `Máquina ${info.nome}`, width: 120, height: 150, loading: "lazy" });
  const caption = h("div", { class: "metric__hint" });
  picture.addEventListener("error", () => {
    if (picture.src.endsWith(info.ilustracao)) return;
    picture.src = info.ilustracao; // foto oficial ainda não colocada
    picture.alt = `Ilustração da linha ${info.linha} (não é a foto do produto)`;
    caption.textContent = "Ilustração: a foto oficial do modelo ainda não foi colocada.";
  });
  return h("div", { class: "model" },
    picture,
    h("div", { class: "model__text" },
      h("div", { class: "metric__label", text: "Modelo" }),
      h("div", { class: "model__name", text: info.nome }),
      h("div", { class: "metric__hint", text: `Série ${sheet.serie} · fabricada em ${sheet.ano_fabricacao}, semana ${String(sheet.semana_fabricacao).padStart(2, "0")}` }),
      caption));
}

function improvementBadges(improvements) {
  if (!improvements.length) return null;
  return card({ kicker: "P&D · versões da máquina", title: "Que melhorias esta máquina tem" },
    improvements.map((item) => {
      const status = IMPROVEMENT_STATUS[item.status] ?? { label: item.status, tone: "neutral" };
      return h("p", {}, badge(status.label, status.tone), " ", item.titulo);
    }));
}

function aiBlock(data) {
  const { confiabilidade: trust, ia } = data;
  const tiles = [];
  if (trust) tiles.push(metric("Confiabilidade do DNA", `${int(trust.nota)}/100`, trust.rotulo));
  if (ia.disponivel && ia.risco_ultimo_chamado != null) {
    tiles.push(metric("Risco de voltar em 90 dias", pct(ia.risco_ultimo_chamado, 0), "estimado pelo modelo de ML"));
  }
  const guesses = ia.causas_provaveis ?? [];
  return h("div", {},
    h("div", { class: "grid" }, tiles),
    !ia.disponivel ? notice("A camada de IA (risco e causa provável) está indisponível para esta máquina. O histórico abaixo continua valendo.", "info") : null,
    guesses.length ? card({ title: `Causa provável (IA) nos ${guesses.length} chamados sem laudo`,
      body: ia.acerto_top3 != null ? `A IA acerta entre as 3 sugestões em ${pct(ia.acerto_top3, 0)} dos casos (teste 2026). Sempre exibida como inferida.` : "" },
      table([
        { key: "abertura", label: "Abertura", render: (r) => date(r.abertura) },
        { key: "consumidor", label: "Consumidor disse" },
        { key: "causa_provavel", label: "Causa provável (IA)" },
      ], guesses, "Chamados sem laudo e a causa provável")) : null);
}

async function loadMachine(serial, signal) {
  const data = await api.get(`/machines/${encodeURIComponent(serial)}`, signal);
  const sheet = data.ficha;
  const events = data.linha_do_tempo;
  const returns = events.filter((e) => e.voltou_em_90_dias).length;
  return h("div", {},
    modelCard(sheet.modelo, sheet),
    h("div", { class: "grid section" },
      metric("Chamados", int(sheet.chamados)),
      metric("Voltas em 90 dias", int(sheet.voltas_em_90_dias)),
      metric("Máquina crônica", sheet.cronica ? "Sim" : "Não")),
    h("div", { class: "section" }, improvementBadges(data.melhorias),
      h("p", {}, h("a", { class: "btn btn--outline", href: link("assistente", sheet.serie), text: "Perguntar ao assistente sobre esta máquina" }), " ",
        h("a", { class: "btn btn--outline", href: link("grafo", sheet.serie), text: "Ver como grafo" }))),
    h("div", { class: "section" }, card({ kicker: "Resumo para o técnico", title: sheet.serie },
      h("p", { text: data.resumo.texto }),
      h("p", { class: "card__muted", text: { bedrock: "Gerado por IA (Amazon Bedrock)", cache: "Gerado por IA (em cache)", regras: "Resumo automático por regras (IA generativa desligada)" }[data.resumo.fonte] ?? data.resumo.fonte }))),
    h("div", { class: "section" }, aiBlock(data)),
    h("section", { class: "section" },
      fold("Linha do tempo · as duas vozes de cada chamado", h("ol", { class: "timeline" }, events.map(eventCard)),
        { count: plural(events.length, "chamado", "chamados"), hint: returns ? `${returns} voltaram em até 90 dias` : "" })));
}

export const dnaPage = {
  title: "DNA da Máquina",
  async render({ params, signal }) {
    const serial = params[0] ?? "";
    const result = h("div", { "aria-live": "polite" });
    const picks = h("div", {});
    const input = h("input", { id: "dna-serie", name: "serie", type: "text", value: serial, autocomplete: "off", placeholder: "Ex.: G5PS000210224033" });
    const form = h("form", { class: "field--inline" },
      h("div", { class: "field" }, h("label", { for: "dna-serie", text: "Número de série (aceita minúsculas e espaços)" }), input),
      h("button", { class: "btn", type: "submit", text: "Abrir o DNA" }));
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const value = input.value.trim();
      window.location.hash = link("dna", value);
    });

    const chronic = await api.get("/machines/chronic?limit=8", signal);
    render(picks, fold("Máquinas crônicas para experimentar",
      h("div", {}, h("p", { class: "card__muted", text: `${int(chronic.total)} máquinas têm 3 ou mais chamados. As 8 com mais chamados:` }),
        chronic.maquinas.map((m) => h("a", { class: "chip chip--orange", href: link("dna", m.serie), text: `${m.serie} · ${m.chamados} chamados` }))),
      { count: chronic.maquinas.length, open: !serial }));

    if (serial) {
      try {
        render(result, await loadMachine(serial, signal));
      } catch (error) {
        if (signal.aborted) return h("div");
        render(result, notice(error.status === 404 ? `Não achei a série "${serial}" na base. Confira o número.` : error.message, "error"));
      }
    } else {
      render(result, notice("Digite um número de série ou escolha uma máquina crônica acima.", "info"));
    }
    return h("div", {},
      pageHeader("DNA da Máquina", "Para o técnico consultar antes de sair e para o CS saber, durante a ligação, se a máquina já teve o mesmo problema. A história inteira, ligada pelo número de série."),
      form, picks, h("div", { class: "section" }, result));
  },
};
