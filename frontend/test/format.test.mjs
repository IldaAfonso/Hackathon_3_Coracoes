// Funções puras de formatação: o padrão brasileiro é fácil de errar e
// aparece em todo número da tela.
import assert from "node:assert/strict";
import test from "node:test";

import { date, decimal, int, month, pValue, pct, plural, signedPct } from "../public/js/format.js";

test("pct formata proporção no padrão brasileiro", () => {
  assert.equal(pct(0.1234), "12,3%");
  assert.equal(pct(0.196, 0), "20%");
  assert.equal(pct(1), "100,0%");
});

test("valores ausentes viram travessão, nunca 'NaN' ou 'null'", () => {
  for (const fn of [pct, int, signedPct, pValue, decimal]) {
    assert.equal(fn(null), "—");
    assert.equal(fn(undefined), "—");
    assert.equal(fn(Number.NaN), "—");
  }
  assert.equal(date(null), "—");
  assert.equal(month(""), "—");
});

test("int usa ponto como separador de milhar", () => {
  assert.equal(int(30481), "30.481");
  assert.equal(int(21073.4), "21.073");
});

test("signedPct mostra o sinal e usa o menos tipográfico", () => {
  assert.equal(signedPct(-0.28), "−28%");
  assert.equal(signedPct(0.05), "+5%");
  assert.equal(signedPct(0), "0%");
});

test("date não depende do fuso horário", () => {
  assert.equal(date("2026-10-13T00:00:00.000"), "13/10/2026");
  assert.equal(date("2026-01-01"), "01/01/2026");
  assert.equal(month("2026-10-01T00:00:00.000"), "10/2026");
});

test("pValue não mostra zero para p muito pequeno", () => {
  assert.equal(pValue(3e-7), "< 0,001");
  assert.equal(pValue(0.9), "0,900");
});

test("plural concorda com o número", () => {
  assert.equal(plural(1, "dia", "dias"), "1 dia");
  assert.equal(plural(3, "dia", "dias"), "3 dias");
  assert.equal(plural(0, "dia", "dias"), "0 dias");
});

test("decimal usa vírgula", () => {
  assert.equal(decimal(0.7), "0,70");
  assert.equal(decimal(0.7, 1), "0,7");
});
