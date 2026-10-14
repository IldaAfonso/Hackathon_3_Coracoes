---
inclusion: always
---

# Estrutura do repositório

```
backend/app/              API FastAPI: main.py, routers/ (um por domínio), state.py (cache), privacy.py, settings.py
frontend/public/          Interface estática: index.html, css/, js/ (módulos ES), js/pages/ (uma por tela), vendor/ (Chart.js)
frontend/nginx.conf       TEMPLATE do nginx: proxy /api e /mcp + cabeçalhos (security-headers.inc, frame-src = CORA_FRAME_SRC)
frontend/public/js/areas.js Áreas P&D e Pós-venda: menus, resolveRoute e link() que respeita a área (puro, testado)
frontend/public/js/pages/  entry (entrada), improvements, bulletins, stock, dna, risk + telas de apoio (home = visão geral, grafo...)
frontend/public/assets/modelos/ Fotos dos modelos (passione.webp, luna.webp) e ilustrações neutras; ver LEIA-ME.md
frontend/public/js/cora.js Ponte com a Cora incorporada (contrato embed v1: cora.ready → embed.context), funções puras
compose.yaml, Makefile    Subir, testar, lint, smoke e pré-voo
app/streamlit_app.py      Interface ANTIGA (alternativa, `make legacy`). Não evoluir.
src/dna_maquina/
  config.py               Mapeamento de colunas, caminhos, janelas (90 dias), sintoma-alvo
  serial.py               Normaliza e decodifica a série (ano/semana de fabricação, chave de ordem)
  ingest.py               Lê .xlsx, valida schema (SchemaError), limpa, flags dq_*, merge sem duplicar
  taxonomy.py             Texto do técnico → componentes, causa principal, família, flags de kit
  history.py              DNA: ordem na máquina, reincidência 90 d, ficha e linha do tempo
  impact.py               Melhoria × impacto: corte_serie (coorte) e retrofit_campo (retorno 90 d)
  analytics.py            Duas vozes (matriz e concordância), radar (z de Poisson), lotes anômalos
  risk.py                 ML: risco de retorno em 90 dias (treino, avaliação temporal, scores)
  llm.py                  LLM: resumo para o técnico via Bedrock, com cache e fallback
  reliability.py          IA p/ histórico confiável: coorte recuperada, causa provável (ML), nota 0–100
  patterns.py             IA p/ padrões: modos de falha no texto (TF-IDF+NMF), boletins citados
  stock.py                Estoque × melhoria: limpa a posição de estoque, levanta pendentes por melhoria (P10/P11)
  assistant.py            Toolbox: análises como ferramentas (a Cora chama via MCP) + perguntas prontas e parecer por regras
  pipeline.py             enrich() + CLI xlsx → data/processed/chamados.parquet
data/raw/                 Planilhas originais (nunca editar)
data/processed/           Parquet gerado (pode apagar; é recriado)
data/melhorias.json       Diretório de melhorias do P&D (editável pelo app)
tests/                    pytest: uma premissa de negócio por teste (test_api, test_privacy, test_core...)
frontend/test/            node --test: formatação pt-BR, roteador e ponte com a Cora
backend/app/mcp_server.py Servidor MCP (/mcp) com as 11 ferramentas dna_* para a Cora (docs/CORA.md)
tests/test_stock.py       Regras do levantamento de estoque e rotas /api/estoque
scripts/make_stock_example.py  Gera a posição de estoque FICTÍCIA de exemplo (data/synthetic/estoque_exemplo.csv)
tests/test_mcp.py         Contrato com a Cora: catálogo, protocolo HTTP, privacidade, erros, hosts
integracoes/cora/         Seed do conector "DNA da Máquina" (roda no backend da Cora) e patch do bug de conectores do kit
backend/scripts/          Pré-voo, smoke test, mcp_check (ferramentas da Cora), diagnóstico opcional do Bedrock e cache
scripts/demo_ready.sh     `make demo-ready`: sobe, confere o /mcp e roda o pré-voo (Bedrock só com DNA_USE_BEDROCK=1)
docs/                     CORA, ARQUITETURA, BEDROCK_E_AWS (credenciais), REVISAO_DO_PROJETO, ROTEIRO_DEMO, guias da equipe
```

Fluxo de dados: `xlsx → ingest.clean_complaints → taxonomy.classify_repairs →
analytics.add_voice_agreement → history.add_machine_sequence → parquet → app`.

Para adicionar uma tela: lógica analítica em `src/dna_maquina/` (função pura, com teste); rota em
`backend/app/routers/<domínio>.py` (texto livre passa pela máscara de privacidade); página em
`frontend/public/js/pages/<nome>.js` registrada em `main.js`; teste da rota em `tests/test_api.py`.
