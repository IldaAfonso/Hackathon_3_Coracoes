// Constantes da interface (nada de números mágicos espalhados).

export const APP_TITLE = "DNA da Máquina";
export const SEARCH_DEBOUNCE_MS = 250;
export const REQUEST_TIMEOUT_MS = 120_000; // o 1º uso do modelo de ML treina na hora

export const COLORS = Object.freeze({
  orange: "#f15632",
  burgundy: "#4a1414",
  sand: "#c8a98a",
  grey: "#8a8178",
  good: "#2f7d4f",
  bad: "#b3261e",
});

// Rótulos legíveis dos status que a API devolve.
export const IMPROVEMENT_STATUS = Object.freeze({
  de_fabrica: { label: "De fábrica", tone: "good" },
  antes_da_melhoria: { label: "Fabricada antes da melhoria", tone: "warn" },
  aplicada_em_campo: { label: "Aplicada em campo", tone: "good" },
  sem_registro: { label: "Sem registro de aplicação", tone: "neutral" },
});

export const VERDICT_TONE = Object.freeze({
  Funcionou: "good",
  Piorou: "bad",
  "Sem efeito mensurável": "warn",
  "Amostra insuficiente": "neutral",
});

// Modelos de máquina: nome comercial e imagem mostrados no DNA. Cada modelo
// tem a SUA foto em /assets/modelos/ (ver LEIA-ME.md lá); enquanto a foto
// oficial faltar, aparece a ilustração neutra do próprio modelo.
export const MACHINE_MODELS = Object.freeze({
  Passione: { nome: "TRES G5 Passione", linha: "G5", imagem: "/assets/modelos/passione.webp", ilustracao: "/assets/modelos/passione-ilustracao.svg" },
  Luna: { nome: "TRES G4 Luna", linha: "G4", imagem: "/assets/modelos/luna.webp", ilustracao: "/assets/modelos/luna-ilustracao.svg" },
});
export const MODEL_FALLBACK_IMAGE = "/assets/modelos/passione-ilustracao.svg";
