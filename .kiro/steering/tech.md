---
inclusion: always
---

# Stack e padrões técnicos

## Stack
- **Backend:** Python 3.12, FastAPI (rotas em `backend/app/routers/`), núcleo analítico `src/dna_maquina`
- pandas, openpyxl (leitura .xlsx), pyarrow (Parquet), scikit-learn + joblib (modelos de ML)
- Cora (IA corporativa) como assistente: o backend publica as análises por MCP (`mcp==1.29`, streamable HTTP em /mcp) e a página Assistente incorpora `<Cora>/embed`
- boto3 / Amazon Bedrock, API Converse (só o resumo da página DNA; opcional, liga com DNA_USE_BEDROCK=1)
- **Frontend:** HTML, CSS e JavaScript (módulos ES) estáticos, **sem build**, servidos por nginx; Chart.js local
- **Containers:** `compose.yaml` com `backend` (sem porta pública) e `frontend` (porta 8080); a planilha é MONTADA, nunca copiada
- Versões fixadas em `backend/requirements.lock` (build reproduzível)
- Interface antiga em Streamlit mantida só como alternativa (`make legacy`); não evoluir mais
- Testes: pytest (backend/núcleo), `node --test` (frontend). Lint: pycodestyle, ruff, ESLint

## Padrões de código (obrigatórios)
- **PEP 8 oficial e Clean Code**: linhas de 79 colunas e **docstrings/comentários de 72**, verificado por `pycodestyle`; funções pequenas, nomes descritivos, sem números mágicos (usar `config.py` / `settings.py`).
- **Docstrings detalhadas em português** em todo módulo, classe e função pública, explicando o
  *porquê* da regra de negócio e não só o *o quê*. Formato Google (Args/Returns/Raises).
- Type hints em todas as assinaturas.
- Nenhuma coluna "crua" da planilha fora de `config.COLUMN_MAP`. O resto do código usa nomes canônicos.
- Funções de análise são **puras**: recebem DataFrame e devolvem DataFrame ou dataclass, sem I/O.
  O I/O fica em `ingest.py` e `pipeline.py`.
- Toda premissa nova sobre os dados entra em: (1) docstring, (2) tabela de premissas do README e
  (3) um teste em `tests/`.

## Regras de IA
- ML: validação SEMPRE temporal (treino 2025, teste 2026) e comparação com a regra simples; nunca usar informação posterior ao encerramento do chamado.
- LLM: o código monta os FATOS e o modelo só redige; o prompt proíbe inventar. Toda chamada passa por cache e tem fallback por regras. Credenciais nunca no código.
- **Conversa = Cora.** Não criar chat nem agente com LLM dentro do MVP. Pergunta nova = função pura no núcleo + método no `Toolbox` (`src/dna_maquina/assistant.py`) + ferramenta `dna_<nome>` em `backend/app/mcp_server.py` (docstring explica ao modelo QUANDO usar) + teste em `tests/test_mcp.py` (atualizar `EXPECTED_TOOLS`) + linha na tabela de `docs/CORA.md`.
- Ferramentas MCP: só leitura, saída JSON compacta e mascarada, erro vira `{"erro": ...}` (nunca exceção para a Cora), parâmetro `n` limitado a 50, análise pesada em thread (`anyio.to_thread`).
- Credenciais: o MVP não precisa de nenhuma. A credencial AWS é do kit da Cora (modelo dela). Nunca pedir credencial no chat nem gravar em arquivo.

## Regras do frontend e da API
- **Nunca `innerHTML` com dado da API** (o texto vem de pessoas): use `dom.js` (`h()`), que só cria nós de texto.
- Sem estilo inline nem script inline: a CSP do nginx só aceita recursos próprios. Fonte e gráficos são locais.
- Todo texto livre que sai da API passa por `mask_text`/`mask_frame` (`backend/app/privacy.py`).
- **O que vai para um modelo de linguagem também é mascarado:** o resumo e as ferramentas MCP da Cora recebem `state.masked()`, nunca `state.df` (e o MCP mascara de novo na saída).
- Nova página = módulo em `frontend/public/js/pages/` + rota no `main.js` + (se for de menu) item em `areas.js` + endpoint em `backend/app/routers/` + teste.
- Links internos sempre com `link(pagina, ...partes)` de `areas.js` (mantém a área na URL); nunca montar `"#/..."` à mão.
- Listas longas sempre com `fold()`/`table(..., legenda)` de `components.js`: abrem e fecham, fechadas por padrão, contagem no título.
- Erro inesperado devolve mensagem neutra; o detalhe vai para o log.

## Comandos (tudo roda em container; nada é instalado na máquina)
```bash
make up           # frontend em http://localhost:8080
make check        # testes e lint do backend e do frontend
make smoke        # todas as rotas na base real + conferência de privacidade
make mcp-check    # as 11 ferramentas que a Cora usa respondem em /mcp
make demo-check   # pré-voo da demonstração (roda dentro do container; inclui o /mcp)
make demo-ready   # sobe tudo, confere o /mcp e roda o pré-voo (Bedrock só com DNA_USE_BEDROCK=1)
make bedrock-check  # (opcional) diagnostica o Bedrock do resumo da página DNA
make down
```
A planilha vai em `data/raw/` (está no `.gitignore`; não vem no zip nem no repositório).
Variáveis: `DNA_CORA_URL` (onde o navegador abre a Cora; libera só essa origem no `frame-src` da CSP) e
`DNA_MCP_ALLOWED_HOSTS` (hosts aceitos no `/mcp`; padrão: localhost, host.docker.internal e nomes da rede).

## AWS (caminho para POC; não é obrigatório no hackathon)
- S3 (raw/processed) + Glue ou Lambda executando `pipeline.py` + Athena
- Amazon Bedrock para classificar a conclusão técnica (usar `taxonomy.py` como baseline/rótulo)
- Cora corporativa: conector "DNA da Máquina" com acesso só do grupo do P&D, `/mcp` atrás de OAuth ou rede privada, iframe com a chave de integração (`X-Cora-Embed-Key`, do lado do servidor)
- Os containers estão prontos para ECS ou App Runner. **Não publicar sem login** (Cognito): a API e o `/mcp` não têm autenticação e servem os dados do desafio
