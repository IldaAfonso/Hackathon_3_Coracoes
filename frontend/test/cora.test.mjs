import assert from "node:assert/strict";
import test from "node:test";

import {
  EMBED_CHANNEL, SCREEN_CONTEXT_MAX_BYTES, cleanSerial, contextMessage,
  jsonBytes, parseCoraMessage, screenContext, statusFor,
} from "../public/js/cora.js";

test("série: normaliza e recusa o que não é série", () => {
  assert.equal(cleanSerial(" g5ps 0002 2046 5809 "), "G5PS000220465809");
  assert.equal(cleanSerial("<script>"), null);
  assert.equal(cleanSerial(undefined), null);
});

test("contexto segue o contrato da Cora (screen, título, JSON pequeno)", () => {
  const context = screenContext({ serial: "G5PS000220465809", improvements: [{ id: "G5-ADAPT-HIDR-2022", titulo: "Adaptação hidráulica" }] });
  const message = contextMessage("r1", context, "G5PS000220465809");
  assert.equal(message.channel, EMBED_CHANNEL);
  assert.equal(message.type, "embed.context");
  assert.ok(message.payload.screen.length <= 80);
  assert.ok(message.payload.screenTitle.length <= 120);
  assert.equal(message.payload.screenContext.serie_em_foco, "G5PS000220465809");
  assert.ok(jsonBytes(message.payload.screenContext) <= SCREEN_CONTEXT_MAX_BYTES);
});

test("contexto grande demais é recusado antes de sair", () => {
  assert.throws(() => contextMessage("r2", { lixo: "x".repeat(SCREEN_CONTEXT_MAX_BYTES) }));
});

test("só mensagens do canal da Cora são lidas", () => {
  assert.equal(parseCoraMessage("não é json"), null);
  assert.equal(parseCoraMessage({ channel: "outro", version: 1, type: "x" }), null);
  const ready = JSON.stringify({ channel: EMBED_CHANNEL, version: 1, type: "cora.ready" });
  assert.equal(parseCoraMessage(ready).type, "cora.ready");
});

test("sessão recusada vira instrução clara", () => {
  const state = statusFor({ type: "cora.auth.rejected", payload: { reason: "missing_token" } });
  assert.equal(state.tone, "error");
  assert.match(state.text, /AUTH_BYPASS/);
  assert.equal(statusFor({ type: "cora.auth.accepted" }), null);
});
