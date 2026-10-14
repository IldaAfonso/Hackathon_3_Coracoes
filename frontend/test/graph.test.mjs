import assert from "node:assert/strict";
import test from "node:test";

import { buildGraph, placeColumn, truncate } from "../public/js/graph-layout.js";

const event = (consumidor, causa, voltou = false) => ({
  consumidor, voltou_em_90_dias: voltou,
  tecnico: { causa, conclusao: causa === "Sem registro técnico" ? null : "x" },
});

test("nós únicos não se sobrepõem", () => {
  const placed = placeColumn(new Map([["a", 100], ["b", 101], ["c", 102]]), 44);
  const ys = [...placed.values()];
  assert.ok(ys[1] - ys[0] >= 44 && ys[2] - ys[1] >= 44);
});

test("o grafo junta sintomas iguais e liga os chamados que voltaram", () => {
  const graph = buildGraph({ linha_do_tempo: [
    event("Máquina vazando", "Bico", true),
    event("Máquina vazando", "Sem registro técnico", true),
    event("Não extrai", "Bico"),
  ] });
  assert.equal(graph.calls.length, 3);
  assert.equal(graph.symptoms.size, 2);
  assert.equal(graph.causes.size, 2);
  assert.equal(graph.returns.length, 2);
  assert.equal(graph.edges.filter((e) => e.missing).length, 1);
});

test("só os chamados mais recentes entram no desenho", () => {
  const many = Array.from({ length: 30 }, () => event("Máquina vazando", "Bico"));
  const graph = buildGraph({ linha_do_tempo: many });
  assert.equal(graph.shown, 12);
  assert.equal(graph.total, 30);
});

test("truncate respeita o limite", () => {
  assert.equal(truncate("abcdefghij", 5), "abcd…");
  assert.equal(truncate(null, 5), "—");
});
