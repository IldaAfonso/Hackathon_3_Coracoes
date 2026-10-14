import assert from "node:assert/strict";
import test from "node:test";

import { AREAS, hasPage, hrefFor, resolveRoute } from "../public/js/areas.js";
import { parseHash } from "../public/js/hash.js";

const route = (hash) => resolveRoute(parseHash(hash));

test("menus: P&D e Pós-venda com os itens pedidos", () => {
  assert.deepEqual(AREAS.pd.pages.map(([p]) => p), ["melhorias", "boletins", "estoque", "dna", "risco", "assistente"]);
  assert.deepEqual(AREAS.posvenda.pages.map(([p]) => p), ["dna", "boletins", "estoque", "risco", "assistente"]);
});

test("rota com área: página e parâmetros", () => {
  assert.deepEqual(route("#/pd/dna/G5PS000210224033"), { area: "pd", page: "dna", params: ["G5PS000210224033"] });
  assert.deepEqual(route("#/posvenda/boletins"), { area: "posvenda", page: "boletins", params: [] });
});

test("área sem página abre a primeira do menu", () => {
  assert.equal(route("#/pd").page, "melhorias");
  assert.equal(route("#/posvenda").page, "dna");
});

test("página que não é da área cai na primeira (Pós-venda não tem Melhorias)", () => {
  assert.deepEqual(route("#/posvenda/melhorias/X"), { area: "posvenda", page: "dna", params: [] });
});

test("rotas sem área continuam valendo (entrada, grafo, visão geral)", () => {
  assert.deepEqual(route("#/"), { area: null, page: "", params: [] });
  assert.deepEqual(route("#/grafo/G5PS1"), { area: null, page: "grafo", params: ["G5PS1"] });
});

test("links respeitam a área quando a página existe nela", () => {
  assert.equal(hrefFor("posvenda", "dna", "G5PS 1"), "#/posvenda/dna/G5PS%201");
  assert.equal(hrefFor("posvenda", "melhorias", "X"), "#/melhorias/X");
  assert.equal(hrefFor(null, "grafo", "A"), "#/grafo/A");
  assert.equal(hrefFor("pd", "dna", ""), "#/pd/dna");
  assert.ok(hasPage("pd", "estoque") && !hasPage("posvenda", "melhorias"));
});
