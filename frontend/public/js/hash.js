// Leitura da rota a partir do hash da URL. Módulo puro (sem DOM): testável no Node.

/** "#/dna/G5PS123" -> { name: "dna", params: ["G5PS123"] } */
export function parseHash(hash) {
  let decoded;
  try {
    decoded = decodeURIComponent(hash.replace(/^#\/?/, ""));
  } catch {
    decoded = ""; // hash malformado (ex.: "%E0%A4%A"): cai na página inicial
  }
  const parts = decoded.split("/").filter(Boolean);
  return { name: parts[0] ?? "", params: parts.slice(1) };
}
