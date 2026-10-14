# Arquitetura do MVP

O número de série é a chave que liga os três times que cuidam da mesma
máquina: **Customer Success** (ouve), **Pós-vendas** (resolve) e **P&D**
(inova). Hoje cada um registra num lugar e ninguém enxerga a história
inteira. O MVP junta os três pela série e devolve a pergunta que nunca
voltava para a engenharia: a melhoria funcionou?

```
navegador ──HTTP──▶ frontend (nginx, :8080) ──/api──▶ backend (FastAPI, :8000)
   │                 estáticos: HTML, CSS, JS          núcleo dna_maquina
   │                 CSP e cabeçalhos de segurança     (pandas, scikit-learn)
   │                 proxy reverso em /api e /mcp             │      ▲
   │                                                          ▼      │ /mcp (11 ferramentas dna_*,
   │                              volumes: base processada,          │  só leitura, base mascarada)
   │                              modelos de ML, cache, catálogo     │
   │                              data/raw: planilha real, SOMENTE   │
   │                              LEITURA, nunca copiada p/ imagem   │
   │                                                                 │
   └─ iframe <Cora>/embed ──▶ Cora (kit dos organizadores) ──────────┘
      (página Assistente;     chat + modelo no Bedrock (credencial AWS do kit),
       contexto da tela)      RBAC: role connector:dna-da-maquina
```

O frontend abre numa **entrada com duas áreas** (P&D e Pós-venda); a área
vai na URL (`#/pd/...`, `#/posvenda/...`) e define o menu (`frontend/public/js/areas.js`).
O Pós-venda vê Boletins só como lista e marca melhorias aplicadas no Estoque;
o P&D insere boletins e importa a posição de estoque.

A conversa com IA é da **Cora**; o MVP só publica as análises como
ferramentas MCP e não chama modelo de linguagem para conversar. Detalhes,
passo a passo e testes de ponta a ponta: [CORA.md](CORA.md).

## Por que separar frontend e backend

| Decisão | Motivo |
|---|---|
| Dois containers | A interface troca sem tocar nas análises, e as análises viram uma API que o Salesforce ou o app do técnico podem consumir depois |
| Backend sem porta pública | Só o nginx o alcança, pela rede interna. A superfície de ataque é uma porta |
| Frontend estático, sem build | Menos peças para quebrar no evento; o nginx serve tudo, inclusive o proxy `/api` (mesma origem, sem CORS) |
| Assistente pela Cora, via MCP | A empresa já tem a plataforma de IA, com login, RBAC, auditoria e o modelo; o MVP só entrega números testados como ferramentas, sem segundo chat nem segunda credencial |
| Núcleo `src/dna_maquina` intocado pela API | As análises continuam funções puras e testadas; a API só decide quando calcular e guarda em cache |

## Rotas da API (`/api`)

| Rota | O que devolve |
|---|---|
| `GET /health`, `/meta` | Saúde, período da base, modo de IA |
| `GET /diagnostico` | Por que o histórico de hoje não atende: 8 sintomas calculados na base real e as melhorias a implantar |
| `GET /times` | O que cada time registra e como a série os liga |
| `GET /overview?modelos=` | Retrato da base |
| `GET /machines/search?q=`, `/machines/chronic`, `/machines/{serie}` | O DNA da máquina: ficha, melhorias que ela tem, confiabilidade, risco, causa provável e linha do tempo com a voz do consumidor e a do técnico |
| `GET /impact`, `/impact/{id}`; `POST /improvements` | Antes × depois de cada melhoria, com IC de 95%, p-valor e veredito; o P&D cadastra a próxima |
| `POST /boletins/analisar`, `POST /boletins/previa` | Lê o boletim em PDF (em memória, 5 MB) e mostra só contagens dos chamados relacionados; o código da melhoria nasce em `POST /improvements` |
| `GET /voices`, `/radar`, `/radar/serie`, `/patterns`, `/risk` | Duas vozes, radar, modos de falha no texto (IA) e risco de retorno (ML) |
| `GET /assistant/cora`, `/assistant/presets`; `POST /assistant/preset`, `/parecer` | Onde está a Cora (iframe da página Assistente) e o plano B por regras (perguntas prontas e parecer) |
| `POST /mcp` (fora de `/api`) | Servidor MCP com 11 ferramentas `dna_*` para a Cora; só leitura, base mascarada, hosts permitidos em `DNA_MCP_ALLOWED_HOSTS` ([CORA.md](CORA.md)) |
| `GET /boletins/cadastrados` | Boletins cadastrados, com o código do projeto da melhoria, peças e vínculo com os chamados |
| `GET /estoque`, `/estoque/melhoria/{id}`, `/estoque/modelo.csv`; `POST /estoque/importar`, `/estoque/aplicacoes` | Estoque × melhoria: posição de estoque por série (fonte nova; exemplo fictício até importar), levantamento das máquinas a atualizar antes da venda e marcação "aplicada" (gravada no volume `dna_state`) |
| `GET /quality`; `POST /import` | Qualidade da base; importação de nova planilha `.xlsx` |

A documentação interativa (OpenAPI) está em `/docs` do backend, acessível
só de dentro da rede dos containers.

## Segurança e privacidade

- **Dado pessoal nunca sai pela API.** A base é anonimizada, mas um técnico
  digitou um telefone real num texto livre. `app/privacy.py` mascara
  telefone, e-mail, CPF e CEP em toda string que sai, e o `smoke_api.py`
  confere, na base real, que a ficha dessa máquina não vaza o número.
  **Limite:** nomes próprios e endereços por extenso não são detectados por
  expressão regular; seria preciso um modelo de reconhecimento de entidades.
- **O que vai para um modelo de linguagem também é mascarado.** As ferramentas MCP que a Cora chama
  calculam sobre a cópia mascarada da base (`state.masked()`) e mascaram de novo na saída
  (`tests/test_mcp.py`); o resumo opcional da página DNA usa a mesma cópia, com teste que captura o
  prompt enviado.
- **`/mcp` sem login, mas restrito:** só leitura, hosts aceitos em `DNA_MCP_ALLOWED_HOSTS` (proteção contra
  DNS rebinding; host estranho recebe 421) e uso apenas em rede local. Quem pode usar o conector é decidido
  pelo RBAC da Cora.
- **Os dados do desafio não vão para a imagem.** A planilha é montada como
  volume somente leitura; `.dockerignore` e `.gitignore` a excluem.
- **Sem XSS:** o frontend nunca usa `innerHTML` com dado da API (o texto vem
  de pessoas); tudo entra como nó de texto.
- **Cabeçalhos:** CSP restrita a recursos próprios (única exceção: `frame-src` com a origem da Cora,
  vinda de `DNA_CORA_URL`; `'none'` quando não configurada), `X-Frame-Options: DENY`,
  `nosniff`, `Referrer-Policy` e `Permissions-Policy`, em toda resposta.
  Fonte e Chart.js são servidos localmente (a CSP bloqueia terceiros).
- Containers sem privilégios (`app` e `nginx`), `HEALTHCHECK` em ambos.
- Erro inesperado devolve mensagem neutra; o detalhe vai só para o log.

## Qualidade

| Verificação | Comando | Resultado |
|---|---|---|
| Testes do backend e do núcleo | `make test` | 122 passam, incluindo 7 do servidor MCP e 10 do estoque (9 de tela do Streamlit são lentos e opcionais) |
| Ferramentas da Cora | `make mcp-check` | 11 ferramentas listadas e `dna_radar` chamada em `/mcp` |
| PEP 8 oficial e `ruff` | `make lint` | `pycodestyle` com 79 colunas e docstrings de 72: 0 violações |
| Testes do frontend | `make test-js` | 27 passam (formatação pt-BR, roteador, áreas e menus, ponte com a Cora) |
| ESLint | `make lint-js` | limpo |
| Todas as rotas na base real | `make smoke` | 17 verificações, incluindo privacidade |

Builds reproduzíveis: imagem-base e 58 pacotes fixados em
`backend/requirements.lock`.

## Limitações conhecidas

- **Deploy AWS não feito.** Os containers estão prontos para ECS ou App
  Runner, mas nada foi implantado.
- **Assistente = Cora.** A conversa depende do kit da Cora no ar; sem ela,
  a página Assistente mostra o plano B por regras. O `/mcp` não tem login
  próprio: só rede interna (ver [CORA.md](CORA.md)).
- **Bedrock não validado** com credenciais reais; hoje ele só gera o
  resumo em texto da página DNA, que funciona por regras sem internet.
- **Sem autenticação.** Para uso fora do evento, colocar Cognito ou SSO na
  frente do nginx e OAuth no `/mcp` (a Cora já suporta conector OAuth).
- **Bug no kit da Cora** (conectores sem ferramentas para quem está em grupo
  explícito): corrigido pelo patch em `integracoes/cora/`; precisa ser
  aplicado no kit e reportado aos organizadores.
- **Métricas de ML não recalculadas de forma independente** (ver
  `REVISAO_DO_PROJETO.md`).
