// Ponte com a Cora incorporada (iframe em <cora>/embed).
//
// Contrato da Cora (cora-frontend/src/embedBridge.ts, versão 1):
//   Cora  -> host: cora.ready, cora.context.accepted|rejected,
//                  cora.auth.accepted|rejected
//   host  -> Cora: embed.context { screen, screenTitle?, screenContext? }
// Toda mensagem é um envelope { channel: "cora-embed", version: 1, type,
// requestId?, payload? }, enviado como JSON em texto.
//
// O contexto da tela só ORIENTA o modelo da Cora (onde a pessoa está, que
// máquina está olhando). Identidade e permissões continuam com a sessão
// da Cora; os números vêm das ferramentas dna_* pelo conector MCP.
// Funções puras (sem DOM): testadas em test/cora.test.mjs.

export const EMBED_CHANNEL = "cora-embed";
export const EMBED_VERSION = 1;
export const SCREEN_CONTEXT_MAX_BYTES = 16 * 1024; // limite da Cora
export const SCREEN_ID = "dna-maquina.assistente"; // até 80 caracteres
const SERIAL_PATTERN = /^[A-Z0-9]{8,24}$/;

/** Série digitada -> forma canônica, ou null se não parece uma série. */
export function cleanSerial(value) {
  const serial = String(value ?? "").toUpperCase().replace(/\s+/g, "");
  return SERIAL_PATTERN.test(serial) ? serial : null;
}

/**
 * Contexto da tela que a Cora recebe.
 * @param {{serial?: string|null, improvements?: Array<{id: string, titulo: string}>, connector?: string}} options
 */
export function screenContext({ serial = null, improvements = [], connector = "DNA da Máquina" } = {}) {
  const context = {
    sistema: "DNA da Máquina (TRES · Grupo 3corações)",
    publico: "Engenharia de P&D das máquinas de café G5 Passione e G4 Luna",
    conector: connector,
    orientacao: `Para qualquer número sobre chamados, máquinas, melhorias ou falhas, use as ferramentas dna_* do conector "${connector}" e responda só com o que elas devolverem.`,
    melhorias_cadastradas: improvements.slice(0, 30).map((item) => ({ id: item.id, titulo: item.titulo })),
  };
  if (serial) context.serie_em_foco = serial;
  return context;
}

/** Tamanho em bytes do JSON (o limite da Cora é em UTF-8). */
export function jsonBytes(value) {
  return new TextEncoder().encode(JSON.stringify(value)).length;
}

/** Envelope embed.context pronto para postMessage. */
export function contextMessage(requestId, context, serial = null) {
  if (jsonBytes(context) > SCREEN_CONTEXT_MAX_BYTES) {
    throw new Error("Contexto da tela grande demais para a Cora (16 KB).");
  }
  return {
    channel: EMBED_CHANNEL,
    version: EMBED_VERSION,
    type: "embed.context",
    requestId,
    payload: {
      screen: SCREEN_ID,
      screenTitle: serial ? `DNA da Máquina · série ${serial}` : "DNA da Máquina · Assistente de engenharia",
      screenContext: context,
    },
  };
}

/** Lê uma mensagem vinda da Cora; null se não for do contrato. */
export function parseCoraMessage(data) {
  let message = data;
  if (typeof data === "string") {
    try { message = JSON.parse(data); } catch { return null; }
  }
  if (!message || typeof message !== "object") return null;
  if (message.channel !== EMBED_CHANNEL || message.version !== EMBED_VERSION) return null;
  if (typeof message.type !== "string") return null;
  return message;
}

/** Texto de status para cada evento da Cora (null = nada a mostrar). */
export function statusFor(message) {
  const reason = message.payload?.reason;
  switch (message.type) {
    case "cora.ready": return { tone: "info", text: "Cora carregada. Enviando o contexto da tela…" };
    case "cora.context.accepted": return { tone: "info", text: "A Cora recebeu o contexto desta tela." };
    case "cora.context.rejected": return { tone: "error", text: "A Cora recusou o contexto da tela (formato inválido)." };
    case "cora.auth.accepted": return null;
    case "cora.auth.rejected":
      return {
        tone: "error",
        text: reason === "missing_token"
          ? "A Cora não encontrou uma sessão. Entre na Cora em outra aba (ou ligue AUTH_BYPASS no ambiente local) e recarregue esta página."
          : "A Cora não validou a sessão. Entre de novo na Cora e recarregue esta página.",
      };
    default: return null;
  }
}
