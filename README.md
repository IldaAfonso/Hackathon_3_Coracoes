# DNA da Máquina ☕

**Desafio 01 · TRES® — Hackathon Cafeína Week 2026 (FIAP, 13–14/out)**

> Como criar um histórico confiável de cada máquina, identificar padrões e apoiar
> decisões de engenharia com evidências reais de campo?

O DNA da Máquina junta, para cada número de série, a voz do consumidor
(Customer Success), a voz do técnico (Pós-vendas) e o diretório de melhorias
do P&D. Com isso, responde a pergunta que hoje não volta para a engenharia:
**a melhoria funcionou?**

| Equipe | Papel |
|---|---|
| Cristiano Sacramento | Engenharia mecânica / confiabilidade: modos de falha, premissas, caso ponta a ponta |
| Ilza | Desenvolvimento no AWS Kiro (specs, código, deploy) |
| Karen | Design (UX das telas, identidade, deck do pitch) |

---

## MVP em containers (frontend + backend)

O número de série liga os três times que cuidam da mesma máquina:
Customer Success (ouve), Pós-vendas (resolve) e P&D (inova). Hoje o
histórico não atende; o MVP junta os três pela série.

```bash
export DNA_USE_BEDROCK=1 AWS_REGION=us-west-2   # assistente e resumos com Bedrock (opcional; sem isso, regras)
make up           # frontend em http://localhost:8080 (backend interno, sem porta pública)
make check        # testes e lint do backend e do frontend
make smoke        # todas as rotas na base real + conferência de privacidade
make bedrock-check  # confere credencial, região e modelo do Bedrock
make demo-ready   # tudo de uma vez antes do palco (sobe, /mcp, Bedrock se ligado, pré-voo)
make down
```

**Assistente = Amazon Bedrock.** A página **Assistente** (no menu das duas
áreas) recebe a pergunta em português e o modelo (padrão
`us.anthropic.claude-haiku-4-5-20251001-v1:0`, API Converse com *tool use*)
escolhe as análises do projeto, lê os números e redige. A resposta mostra
quais análises foram consultadas; **os números vêm do código, não do
modelo**. Sem Bedrock, a página oferece as respostas prontas e o parecer
técnico por regras. Credenciais: [docs/BEDROCK_E_AWS.md](docs/BEDROCK_E_AWS.md).

A integração com a **Cora** (IA corporativa do Grupo 3corações) continua no
código, mas saiu da interface: o servidor MCP (`/mcp`, 11 ferramentas
`dna_*`) segue no ar para quando houver um kit da Cora. Passo a passo:
[docs/CORA.md](docs/CORA.md).

A planilha real **não entra na imagem**: ela é montada de `data/raw/` em modo
somente leitura. Arquitetura, rotas e segurança: [docs/ARQUITETURA.md](docs/ARQUITETURA.md).
Revisão do projeto e dos arquivos do desafio: [docs/REVISAO_DO_PROJETO.md](docs/REVISAO_DO_PROJETO.md).
A interface antiga em Streamlit continua disponível: `make legacy`.

> As marcas Mercafé, 3corações e TRES pertencem aos seus titulares e são usadas
> só como referência visual do desafio, com atribuição
> ([frontend/public/assets/brand/ATRIBUICAO.md](frontend/public/assets/brand/ATRIBUICAO.md)).

## Entrada por área: P&D e Pós-venda

A página inicial (`#/`) tem duas áreas, e cada uma mostra só o menu que o
time usa. A área vai na URL (`#/pd/...`, `#/posvenda/...`), então um link
copiado abre na mesma área.

| Área | Menu | Diferença |
|---|---|---|
| **P&D** | Melhorias · Boletins · Estoque · DNA da Máquina · Riscos · Assistente | Insere boletins, importa a posição de estoque |
| **Pós-venda** | DNA da Máquina · Boletins · Estoque · Riscos · Assistente | Boletins só leitura (lista com o código); no Estoque, marca a melhoria como **aplicada** |

Na página inicial a barra de menu fica oculta: os cartões das áreas já
fazem esse papel. Dentro de uma área, o menu mostra só as páginas dela.

- **DNA da Máquina:** ao abrir uma série, o topo mostra o **nome e a foto do
  modelo** (TRES G5 Passione / TRES G4 Luna). As fotos oficiais vão em
  `frontend/public/assets/modelos/` (ver o `LEIA-ME.md` da pasta); enquanto
  faltarem, aparece a ilustração neutra de cada modelo, com aviso.
- **Boletins:** cada cadastrado mostra o **código do projeto da melhoria**
  (`MEL-...`), documento, tipo, série de corte, peças e vínculo com os chamados.
- **Todas as listas abrem e fecham** (fechadas por padrão, com a contagem no
  título) e cada página com 2+ listas tem "Abrir todas / Fechar todas".
- As telas de apoio do pitch seguem por link: Visão geral (`#/visao-geral`),
  Grafo, Duas vozes, Radar, Padrões e Importar base.
- **Assistente:** na página DNA, "Perguntar ao assistente sobre esta máquina"
  abre o Assistente na mesma área, já com a série como contexto.

## Estoque × melhoria (fonte de dados nova)

Ao implantar uma melhoria, a tela **Estoque** levanta as máquinas **ainda em
estoque** que saíram da fábrica sem ela, para atualizar **antes da venda**:
quantas, quais séries (as que entraram primeiro aparecem primeiro), em que
local e quantas peças do boletim separar, com exportação em CSV para a ordem
de serviço. O Pós-venda marca cada máquina como **aplicada**, e a lista do P&D
se atualiza.

A fonte é a **posição de estoque por número de série**, exportada do ERP/WMS
(.xlsx ou .csv; só "Número de série" é obrigatório). Ela se liga ao resto pelo
mesmo número de série. **Enquanto a posição real não for importada, a tela usa
uma base de exemplo FICTÍCIA** (`data/synthetic/estoque_exemplo.csv`, gerada
por `make estoque-exemplo`) e avisa em vermelho. Regras e premissas: P10 e P11
abaixo; código em `src/dna_maquina/stock.py`.

## Boletins e código de melhoria

Na tela **Boletins** (`#/pd/boletins`) o P&D envia o boletim técnico em PDF. O
sistema lê modelo, data, assunto, peças e o campo "Número de Série"
(**Indiferente** = kit de campo; **uma série** = mudança de fábrica), mostra os
dados relacionados e, ao registrar, gera o **código da melhoria**
(`MEL-G5-RF-0002-R`). A importação `.xlsx` aceita a coluna opcional
"Código da melhoria": com ela o vínculo é **registrado**; sem ela, **inferido**
por palavras. O PDF não é guardado. Detalhes e limites:
[docs/BOLETINS_E_CODIGO.md](docs/BOLETINS_E_CODIGO.md).

## Validação com base sintética

`make sintetico` sobe, em http://localhost:8090 e isolada da base real, uma
base sintética com efeitos plantados (bandeja funciona, kit não), catálogo de
melhorias e boletins em PDF; dá para importar a base e inserir os boletins
na tela, passo a passo (`make sintetico-e2e` faz o mesmo sozinho). `make test`
confere que o protótipo recupera o plantado. Detalhes: [docs/VALIDACAO.md](docs/VALIDACAO.md).

## Como rodar sem container (interface antiga em Streamlit)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=src python -m dna_maquina.pipeline        # processa data/raw/*.xlsx (≈20 s)
streamlit run app/streamlit_app.py                   # abre em http://localhost:8501
```

Testes: `pytest` (cada um documenta uma premissa de negócio; inclui os do servidor MCP da Cora). Teste do app Streamlit: `RUN_APP_TESTS=1 pytest tests/test_app.py` (lento).

Modelo de risco: treinado automaticamente na 1ª abertura da página **Risco de retorno** (~10 s), ou com `PYTHONPATH=src python -m dna_maquina.risk`.

## O que o protótipo faz

| Página | Dor do P&D | Persona | O que responde |
|---|---|---|---|
| Visão geral | 06 — tratar dados é lento | Marina (P&D) | Retrato da base em segundos |
| DNA da máquina | 07 — sem histórico | Carlos, Rafael | Linha do tempo da série, voltas em 90 dias, quais melhorias a máquina tem |
| Melhoria × impacto | 04 — melhoria × impacto | Marina (P&D) | Antes × depois com IC 95% e p-valor; veredito direto para o P&D |
| Duas vozes | 05 — histórias diferentes | Rafael, Marina | Sintoma relatado × causa encontrada; % de concordância |
| Radar | 03 — problemas despercebidos | Marina | O que cresceu nos últimos 3 meses sem ninguém perguntar |
| Risco de retorno (ML) | Reincidência (Juliana) | Rafael, Carlos | Chance de o problema voltar em 90 dias; lista de chamados recentes para acompanhar |
| Padrões no texto (IA) | 03: despercebidos | Marina | Modos de falha descobertos no texto, temas em alta e boletins citados |
| Assistente (Bedrock) | 06: dados lentos | Marina (P&D), Carlos | Pergunta livre respondida pelo Bedrock com as análises do projeto, citando quais usou; respostas prontas e parecer técnico por regras |
| Importar base | 06 + diferencial | Marina | Upload de nova extração .xlsx, deduplicada por nº do caso, e relatório de qualidade |

## Principais achados (base real: 30.481 chamados, jan/2025–set/2026)

1. **Bandeja de cápsulas (caso ponta a ponta).** As máquinas fabricadas antes
   do corte G5PS000210224033 têm 19,6% dos chamados por vazamento; as fabricadas
   depois, 14,2% (‑28% relativo, p ≈ 3·10⁻⁷). Por semana de fabricação há um
   degrau (S01/2021 = 19,9% → S02 = 15,8%), e depois as coortes de 2021 a 2024 ficam entre 13% e 16%, sem tendência de alta com a idade.
2. **Adaptação hidráulica (kit de campo).** A taxa de retorno em 90 dias após um
   reparo de vazamento é igual com e sem o kit (15,1% × 15,4%, p = 0,9), e o kit
   foi citado em 23% dos reparos no início de 2025 contra 3% no fim do ano.
   Uma explicação de engenharia: cerca de 40% dos "Máquina vazando" são, segundo o
   técnico, **bico entupido** (transbordo), um modo de falha que o kit não ataca.
3. **Duas vozes.** "Botões piscando/Luz acesa", o sintoma nº 1, só tem causa
   elétrica em 11% dos casos. Na maioria é hidráulico (contador volumétrico 29%,
   bico 14%, bomba 11%).
4. **Radar.** O G4 Luna "Não extrai" foi de ~7 chamados/mês (início de 2025)
   para 109–157/mês (mai–jul/2026).
5. **DNA.** 22% dos chamados são a mesma máquina voltando em até 90 dias.
   2.019 máquinas têm 3 ou mais chamados no período.

## Inteligência artificial no projeto: uma camada para cada parte da pergunta

> *Como criar um histórico **confiável** de cada máquina, **identificar padrões** e **apoiar decisões de engenharia** com evidências reais de campo?*

| Parte da pergunta | IA aplicada | Módulo | Resultado na base real |
|---|---|---|---|
| **Histórico confiável** | Recuperação de coorte para séries ilegíveis (uma correção de digitação, aceita só se plausível e única) | `reliability.py` | Coorte recuperada em **241 dos 942** chamados com série ilegível |
| | Causa provável (ML) para chamados **sem laudo** | `reliability.py` | A causa real está entre as 3 sugestões em **69%** dos casos (teste 2026). A 1ª sugestão acerta 39%, contra 37% de "chutar a causa mais comum do sintoma". Sempre exibida como *inferida* |
| | Nota de confiabilidade 0–100 por chamado e por máquina (pesos explícitos) | `reliability.py` | Média de 90/100; 84% das máquinas com confiabilidade alta. Máquina demo: 79/100 |
| | Resumo da máquina para o técnico (LLM) | `llm.py` | 3–4 frases a partir dos fatos, com cache e alternativa sem rede |
| **Identificar padrões** | Descoberta não supervisionada de modos de falha no texto (TF-IDF + NMF) | `patterns.py` | 12 modos de falha. **"Bomba colada" pesa quase 2× mais no Luna** (9,3% × 4,8%) |
| | Boletins citados no texto livre | `patterns.py` | **230 citações de "boletim técnico do bico" no G5** desde abr/2025 e boletins de câmara/unidade no Luna desde mai/2026. **Nenhum deles está no diretório fornecido** |
| | Risco de retorno em 90 dias (ML) | `risk.py` | AUC 0,70 (regra simples: 0,64). Nos 10% de maior risco, 65,5% voltam |
| **Apoiar decisões** | Assistente com **Amazon Bedrock** (API Converse + *tool use*). As análises viram ferramentas (`Toolbox`); o modelo escolhe a ferramenta, recebe o JSON e redige só com esses números (até 6 rodadas por pergunta) | `agent.py`, `assistant.py`, rota `POST /api/assistant/perguntar` | 10 ferramentas (impacto, DNA, duas vozes, radar, modos de falha…). A resposta lista as análises consultadas |
| | As mesmas ferramentas para a Cora, via servidor **MCP** (`/mcp`) | `backend/app/mcp_server.py` | 11 ferramentas `dna_*`, prontas para o conector da Cora. Guia: [docs/CORA.md](docs/CORA.md) |
| | Parecer técnico para o P&D | `assistant.py` | Pelo assistente ("escreva o parecer da melhoria …") ou por regras, pronto para baixar |

Princípio comum: **os números vêm do código, a IA só lê, agrupa ou redige.** Dado inferido nunca se mistura com dado registrado. As análises e o ML rodam localmente, sem internet; o assistente e o resumo da página DNA dependem do Bedrock, e sem ele a interface cai para as respostas por regras.

**Ligar o Bedrock** (assistente e resumo da página DNA; credenciais AWS no terminal ou papel IAM):

```bash
export DNA_USE_BEDROCK=1
export AWS_REGION=us-west-2                       # região onde o modelo está habilitado
export BEDROCK_MODEL_ID="<ID do console Bedrock>" # opcional; padrão: Claude Haiku 4.5 (perfil us.)
PYTHONPATH=src python -m dna_maquina.llm G5PS000220465809 G5PS000210486548   # aquece o cache dos resumos
PYTHONPATH=src python -m dna_maquina.assistant                                  # perguntas prontas, por regras (sem IA)
```

Os resumos ficam em `data/cache/` e aparecem mesmo sem internet. O
assistente não tem cache: cada pergunta é uma chamada ao Bedrock.

## Deploy na AWS (EC2)

`scripts/deploy_ec2.py` publica o MVP numa EC2 Amazon Linux 2023
(t3.medium, us-west-2) e imprime a URL. Ele lê as credenciais **só do
ambiente** (nada é gravado no projeto) e:

1. compacta o projeto (incluindo `data/raw/`) e envia a um bucket S3 privado;
   a instância baixa por URL pré-assinada (1 h);
2. cria o security group `dna-maquina-mvp` com as portas 80 e 8080;
3. cria o papel IAM `dna-maquina-mvp`, **só com `bedrock:InvokeModel`**, e o
   liga à instância: o Bedrock continua funcionando depois que a credencial
   de quem publicou expira;
4. sobe a instância com `docker compose` (frontend na porta 80,
   `DNA_USE_BEDROCK=1`) e encerra a instância anterior do mesmo deploy.

```bash
pip install boto3
export AWS_DEFAULT_REGION=us-west-2 AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=...
python scripts/deploy_ec2.py .        # ~4 min até a aplicação responder
```

> **Atenção:** o deploy é **público e sem login**. A API, o `/mcp` e o
> assistente ficam abertos a qualquer pessoa com o link, e cada pergunta ao
> assistente gera custo de Bedrock. Use só para a demo e apague os recursos
> depois (instância, security group, bucket e papel IAM `dna-maquina-mvp`).
> Para produção, ver "Caminho para POC" abaixo.

## Premissas sobre os dados (leia antes de apresentar)

| # | Premissa | Evidência / impacto |
|---|---|---|
| P1 | **Série legado** `G5PS000 AA SS NNNNN` = ano, semana de fabricação e sequencial. **Série nova** `MMMM VVV AA SS NNNNN` (G5 de 2024 em diante e todo G4) inclui a tensão. | 99,95% das "semanas" ficam entre 01 e 53, e a mediana da data de instalação cresce com o ano. **Confirmar com o P&D.** |
| P2 | A comparação antes × depois de uma mudança de fábrica é feita por **coorte de fabricação** e não por calendário. | A base é de 2025–26 e as melhorias são de 2022. |
| P3 | O indicador é de **mix**: % dos chamados da coorte que são vazamento. | Não temos a base instalada por coorte. Com ela, o mesmo código calcula falhas por 1.000 máquinas. |
| P4 | Reincidência = novo chamado da mesma série em até **90 dias**. | Prazo de garantia de serviço (CDC art. 26). Configurável em `config.py`. |
| P5 | A causa principal sai do texto livre do técnico por regras de palavra-chave, com peça trocada > ajuste > limpeza > orientação. | Regras auditáveis em `taxonomy.py`. A POC pode trocar por um classificador Bedrock. |
| P6 | Kits de campo são detectados pelo texto ("adapta", "oring/anel", "bandeja"). | O uso pode estar subnotificado. Recomendação para a POC: campo estruturado de peça trocada. |
| P7 | Registros imperfeitos **não são apagados**: recebem flags `dq_*` e aparecem no relatório de qualidade. | 942 séries inválidas (3,1%), 6.362 chamados sem conclusão (20,9%), 164 abertos antes da instalação. |
| P9 | O modelo de risco usa só informação conhecida no encerramento do chamado. Os chamados dos últimos 90 dias ficam fora do treino porque o desfecho ainda é desconhecido. | `risk.build_features`, teste `test_features_use_only_information_known_at_case_close` |
| P8 | As colunas "Mês" e "Ano" da planilha são fórmulas não calculadas e são recalculadas a partir da data de abertura. | — |
| P10 | **Estoque, mudança de fábrica:** máquina com série igual ou posterior à série de corte já sai com a melhoria; anterior, precisa recebê-la antes da venda. | Mesma chave `AAAASSNNNNN` do caso da bandeja (`stock.cutoff_key`). |
| P11 | **Estoque, kit de campo:** a **semana do boletim** é o corte de fábrica; fabricada antes dela (semana/ano da série), aplicar o kit antes de vender. Código do projeto na coluna "Melhorias aplicadas" ou marcação na tela = já aplicada. | Decisão da equipe ("usar a data da ficha de melhoria e relacionar com a semana/ano da série"). **Confirmar com o P&D** a data real de entrada de cada melhoria na linha. |

## Estrutura

```
dna-maquina/
├── backend/app/                # API FastAPI (routers/), privacidade, mcp_server.py (ferramentas da Cora)
├── frontend/                   # interface web (nginx + JS), página Assistente com Bedrock (pages/assistant.js)
├── scripts/deploy_ec2.py       # deploy da demo numa EC2 (S3 + papel IAM só com Bedrock)
├── integracoes/cora/           # seed do conector "DNA da Máquina" e patch do kit da Cora
├── compose.yaml, Makefile      # subir, testar, pré-voo
├── app/streamlit_app.py        # interface ANTIGA (make legacy)
├── src/dna_maquina/
│   ├── config.py               # colunas, caminhos, parâmetros
│   ├── serial.py               # normalização e decodificação da série
│   ├── ingest.py               # leitura, validação, limpeza, merge de bases
│   ├── taxonomy.py             # voz do técnico → componentes/causa
│   ├── history.py              # DNA: sequência, reincidência, ficha por máquina
│   ├── impact.py               # melhoria × impacto (coorte e retrofit)
│   ├── analytics.py            # duas vozes, radar, lotes anômalos
│   ├── risk.py                 # ML: risco de retorno em 90 dias
│   ├── llm.py                  # LLM: resumo para o técnico (Bedrock, opcional)
│   ├── agent.py                # assistente: Bedrock (Converse + tool use) sobre as ferramentas
│   ├── reliability.py          # IA: coorte recuperada, causa provável, nota de confiabilidade
│   ├── patterns.py             # IA: modos de falha no texto, boletins citados
│   ├── assistant.py            # ferramentas das análises (Bedrock e Cora/MCP) + plano B por regras
│   └── pipeline.py             # CLI: xlsx → parquet
├── data/raw/                   # planilhas originais (fora do git: .gitignore)
├── data/melhorias.json         # diretório de melhorias (3 boletins do G5)
├── tests/                      # pytest
├── docs/                       # CORA, ARQUITETURA, roteiros, guias da equipe, screenshots
└── .kiro/                      # steering + spec para o AWS Kiro
```

## Caminho para POC na 3corações

1. **Dados:** conector Salesforce → Amazon S3 (AppFlow), processado diariamente (Glue/Lambda executando este pipeline), consultado via Athena.
2. **Base instalada:** cruzar com vendas e produção por série para passar de *mix* para *taxa de falha por 1.000 máquinas*.
3. **Campo estruturado de peça trocada** no formulário do técnico, com código de peça (ex.: 3000017), para medir os boletins sem depender do texto livre.
4. **Classificador da conclusão técnica** com Amazon Bedrock, treinado e validado contra as regras atuais.
5. **DNA no atendimento:** card da máquina dentro do Salesforce (CS) e no app do técnico.
6. **Cora em produção:** conector `DNA da Máquina` na Cora corporativa (login Entra ID, acesso só para o grupo do P&D), `/mcp` protegido por OAuth ou rede privada, e o iframe autenticado pela chave de integração da Cora.
7. **Deploy:** container no AWS App Runner com login corporativo (Cognito/SSO).
