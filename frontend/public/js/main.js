// Ponto de entrada: busca por série, rodapé e roteador com as áreas
// (P&D e Pós-venda). As páginas ficam registradas por nome; o menu de
// cada área está em areas.js.

import { api } from "./api.js";
import { currentArea } from "./areas.js";
import { int } from "./format.js";
import { startRouter } from "./router.js";
import { assistantPage } from "./pages/assistant.js";
import { bulletinsPage } from "./pages/bulletins.js";
import { dataPage } from "./pages/data.js";
import { dnaPage } from "./pages/dna.js";
import { entryPage } from "./pages/entry.js";
import { graphPage } from "./pages/graph.js";
import { homePage } from "./pages/home.js";
import { improvementsPage } from "./pages/improvements.js";
import { patternsPage } from "./pages/patterns.js";
import { radarPage } from "./pages/radar.js";
import { riskPage } from "./pages/risk.js";
import { stockPage } from "./pages/stock.js";
import { voicesPage } from "./pages/voices.js";

// Todas as páginas, por nome de rota. As das áreas aparecem no menu da
// área; as demais (visão geral, grafo, vozes...) seguem acessíveis por link.
const routes = {
  "": entryPage,
  "visao-geral": homePage,
  melhorias: improvementsPage,
  boletins: bulletinsPage,
  estoque: stockPage,
  dna: dnaPage,
  risco: riskPage,
  grafo: graphPage,
  vozes: voicesPage,
  radar: radarPage,
  padroes: patternsPage,
  assistente: assistantPage,
  dados: dataPage,
};

const root = document.getElementById("conteudo");
const nav = document.getElementById("menu");

// Busca do topo: abre o DNA na área atual (ou no P&D, fora das áreas).
document.getElementById("busca").addEventListener("submit", (event) => {
  event.preventDefault();
  const serial = new FormData(event.target).get("serie").toString().trim();
  const area = currentArea() ?? "pd";
  window.location.hash = serial ? `#/${area}/dna/${encodeURIComponent(serial)}` : `#/${area}/dna`;
});

api.get("/meta").then((meta) => {
  document.getElementById("rodape-meta").textContent =
    `Base: ${int(meta.chamados)} chamados de ${int(meta.maquinas)} máquinas, de ${meta.periodo.inicio} a ${meta.periodo.fim} · IA: ${meta.ia_generativa}`;
}).catch(() => {});

startRouter({ root, nav, routes, fallback: "" });
