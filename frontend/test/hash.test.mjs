import assert from "node:assert/strict";
import test from "node:test";

import { parseHash } from "../public/js/hash.js";

test("rota e parâmetros", () => {
  assert.deepEqual(parseHash("#/dna/G5PS000210224033"), { name: "dna", params: ["G5PS000210224033"] });
  assert.deepEqual(parseHash("#/melhorias/G5-BANDEJA-2022"), { name: "melhorias", params: ["G5-BANDEJA-2022"] });
});

test("início: hash vazio, só # ou #/", () => {
  for (const hash of ["", "#", "#/"]) assert.deepEqual(parseHash(hash), { name: "", params: [] });
});

test("decodifica espaços e acentos da série digitada", () => {
  assert.equal(parseHash("#/dna/g5ps%20000210224033").params[0], "g5ps 000210224033");
});

test("hash malformado não derruba a página", () => {
  assert.deepEqual(parseHash("#/dna/%E0%A4%A"), { name: "", params: [] });
});
