// Layout do grafo da máquina, em função pura (sem DOM), para poder testar.
// Colunas: consumidor (esquerda) · chamados (centro) · técnico (direita).

export const GRAPH = Object.freeze({
  width: 1100, left: 175, center: 550, right: 925,
  top: 150, row: 58, gap: 44, maxCalls: 12,
});

export function truncate(text, limit) {
  const value = String(text ?? "—");
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

/** Posições verticais de nós únicos: média dos chamados ligados, sem sobrepor. */
export function placeColumn(wanted, gap = GRAPH.gap) {
  const order = [...wanted.entries()].sort((a, b) => a[1] - b[1]);
  const placed = new Map();
  let last = -Infinity;
  for (const [key, y] of order) {
    const at = Math.max(y, last + gap);
    placed.set(key, at);
    last = at;
  }
  return placed;
}

/** Monta nós e arestas a partir da resposta de /machines/{serie}. */
export function buildGraph(machine) {
  const events = machine.linha_do_tempo.slice(-GRAPH.maxCalls);
  const calls = events.map((event, index) => ({
    id: `c${index}`, y: GRAPH.top + index * GRAPH.row, event,
  }));
  const wantSymptom = new Map();
  const wantCause = new Map();
  const collect = (map, key, y) => map.set(key, [...(map.get(key) ?? []), y]);
  for (const call of calls) {
    collect(wantSymptom, call.event.consumidor ?? "—", call.y);
    collect(wantCause, call.event.tecnico.causa ?? "Sem registro técnico", call.y);
  }
  const mean = (list) => list.reduce((a, b) => a + b, 0) / list.length;
  const symptoms = placeColumn(new Map([...wantSymptom].map(([k, v]) => [k, mean(v)])));
  const causes = placeColumn(new Map([...wantCause].map(([k, v]) => [k, mean(v)])));
  const edges = [];
  for (const call of calls) {
    edges.push({ kind: "voz-cs", from: ["c", call.y], to: ["s", symptoms.get(call.event.consumidor ?? "—")] });
    const cause = call.event.tecnico.causa ?? "Sem registro técnico";
    edges.push({ kind: "voz-pos", from: ["c", call.y], to: ["t", causes.get(cause)], missing: !call.event.tecnico.conclusao && cause === "Sem registro técnico" });
  }
  const returns = calls.slice(0, -1)
    .map((call, i) => ({ from: call.y, to: calls[i + 1].y, event: call.event }))
    .filter((link) => link.event.voltou_em_90_dias);
  const height = Math.max(
    calls.at(-1)?.y ?? GRAPH.top, ...symptoms.values(), ...causes.values()) + 70;
  return { calls, symptoms, causes, edges, returns, height, shown: events.length, total: machine.linha_do_tempo.length };
}
