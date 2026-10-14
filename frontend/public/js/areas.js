// Áreas de trabalho: cada time vê só o menu que usa.
//
// A URL carrega a área: "#/pd/dna/G5PS..." ou "#/posvenda/boletins".
// Assim um link copiado abre na mesma área, e a mesma página (ex.: DNA)
// serve aos dois times. Rotas sem área ("#/grafo/...", "#/visao-geral")
// continuam valendo para as telas de apoio do pitch.
// Módulo puro (sem DOM): testado em test/areas.test.mjs.

export const AREAS = Object.freeze({
  pd: Object.freeze({
    label: "P&D",
    persona: "Marina, engenharia de produto",
    pergunta: "A melhoria funcionou?",
    pages: Object.freeze([
      ["melhorias", "Melhorias"],
      ["boletins", "Boletins"],
      ["estoque", "Estoque"],
      ["dna", "DNA da Máquina"],
      ["risco", "Riscos"],
      ["assistente", "Assistente"],
    ]),
  }),
  posvenda: Object.freeze({
    label: "Pós-venda",
    persona: "Carlos, técnico de assistência",
    pergunta: "O que já foi feito nesta máquina?",
    pages: Object.freeze([
      ["dna", "DNA da Máquina"],
      ["boletins", "Boletins"],
      ["estoque", "Estoque"],
      ["risco", "Riscos"],
      ["assistente", "Assistente"],
    ]),
  }),
});

const pageNames = (area) => AREAS[area].pages.map(([name]) => name);

/**
 * Traduz a rota lida do hash na área, na página e nos parâmetros.
 * @param {{name: string, params: string[]}} route  saída de parseHash
 * @returns {{area: string|null, page: string, params: string[]}}
 */
export function resolveRoute({ name, params }) {
  if (!Object.hasOwn(AREAS, name)) return { area: null, page: name, params };
  const [first, ...rest] = params;
  if (first && pageNames(name).includes(first)) return { area: name, page: first, params: rest };
  return { area: name, page: pageNames(name)[0], params: [] };
}

/** A página existe na área? (ex.: Melhorias não existe no Pós-venda) */
export const hasPage = (area, page) => Boolean(area) && Object.hasOwn(AREAS, area) && pageNames(area).includes(page);

/**
 * Link interno que respeita a área atual: dentro da área quando a
 * página existe nela; senão, a rota sem área.
 */
export function hrefFor(area, page, ...parts) {
  const tail = parts.filter((p) => p !== undefined && p !== null && p !== "")
    .map((p) => `/${encodeURIComponent(p)}`).join("");
  return hasPage(area, page) ? `#/${area}/${page}${tail}` : `#/${page}${tail}`;
}

// Área da tela atual, definida pelo roteador a cada navegação. As páginas
// usam `link()` em vez de montar "#/..." à mão.
let current = null;
export const setCurrentArea = (area) => { current = area; };
export const currentArea = () => current;
export const link = (page, ...parts) => hrefFor(current, page, ...parts);
