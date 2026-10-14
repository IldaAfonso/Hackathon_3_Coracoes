# Comandos de rotina do DNA da Máquina. Tudo roda em container: nada é instalado na sua máquina.
.DEFAULT_GOAL := help
COMPOSE := docker compose
BACKEND_RUN := docker run --rm -v $(CURDIR):/work -w /work --entrypoint sh dna-maquina-backend:mvp -c
PY_FILES := backend integracoes tests/conftest.py tests/test_api.py tests/test_mcp.py tests/test_privacy.py tests/test_impact_robustness.py tests/test_bedrock_check.py tests/test_boletim.py tests/test_synthetic_validation.py

.PHONY: help up down logs test lint smoke demo-check demo-ready bedrock-check bedrock-warm mcp-check estoque-exemplo test-js lint-js check legacy sintetico sintetico-down sintetico-e2e pacote

help:  ## lista os comandos
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

up:  ## sobe frontend (http://localhost:8080) e backend, reconstruindo se preciso
	$(COMPOSE) up -d --build

down:  ## derruba tudo (os volumes com a base processada são preservados)
	$(COMPOSE) down

logs:  ## acompanha os logs
	$(COMPOSE) logs -f --tail=50

test:  ## testes do backend e do núcleo (pytest)
	$(COMPOSE) build backend
	$(COMPOSE) run --rm --no-deps backend test -p no:warnings

lint:  ## PEP 8 oficial (pycodestyle: 79 colunas, docstrings 72) + ruff
	$(BACKEND_RUN) "pycodestyle --max-line-length=79 --max-doc-length=72 $(PY_FILES) && ruff check --line-length 79 --select E,F,W,I,N,B,UP $(PY_FILES) && ruff check src app --select E,F,W,I && echo 'PEP 8 + ruff: limpo'"

smoke:  ## chama todas as rotas na base real e confere que nenhum dado pessoal vaza (precisa do 'make up')
	$(COMPOSE) exec backend python backend/scripts/smoke_api.py

demo-ready:  ## tudo de uma vez: sobe, confere o /mcp da Cora e roda o pré-voo (Bedrock só se DNA_USE_BEDROCK=1; veja docs/CORA.md)
	bash scripts/demo_ready.sh

estoque-exemplo:  ## regenera a posição de estoque FICTÍCIA de exemplo (data/synthetic/estoque_exemplo.csv)
	$(BACKEND_RUN) "PYTHONPATH=src python scripts/make_stock_example.py"

mcp-check:  ## confere o servidor MCP que a Cora usa (lista e chama as ferramentas em /mcp)
	$(COMPOSE) exec backend python backend/scripts/mcp_check.py

bedrock-check:  ## (opcional) diagnostica o Bedrock dos resumos da página DNA e diz o que consertar
	$(COMPOSE) exec backend python backend/scripts/bedrock_check.py

bedrock-warm:  ## (opcional) grava no cache os resumos da página DNA (funciona mesmo se a rede da AWS falhar no palco)
	$(COMPOSE) exec backend python backend/scripts/bedrock_warm.py

demo-check:  ## pré-voo da demonstração: serviços, números do roteiro, privacidade, /mcp da Cora e modo offline
	$(COMPOSE) exec -e DEMO_BASE_URL=http://frontend:8080 backend python backend/scripts/preflight.py

sintetico:  ## sobe a validação com a base sintética em http://localhost:8090 (isolada da real)
	docker compose -f compose.yaml -f compose.synthetic.yaml up -d --build

sintetico-e2e:  ## roda a demonstração ponta a ponta na pilha sintética (precisa do 'make sintetico')
	docker compose -f compose.yaml -f compose.synthetic.yaml exec backend python backend/scripts/e2e_synthetic.py

sintetico-down:  ## derruba a validação sintética e apaga os volumes dela
	docker compose -f compose.yaml -f compose.synthetic.yaml down -v

pacote:  ## gera ../dna-maquina-mvp.zip sem planilha real, sem demo-offline e sem segredos
	rm -f ../dna-maquina-mvp.zip
	zip -qr ../dna-maquina-mvp.zip . -x 'data/raw/*' 'demo-offline/*' '.git/*' '*node_modules*' '*__pycache__*' '.env' 'data/processed/*' 'data/cache/*' '.ruff_cache/*' '.pytest_cache/*'
	@unzip -Z1 ../dna-maquina-mvp.zip | grep -E 'data/raw|demo-offline|\.env$$' && echo 'ERRO: arquivo proibido no pacote' && exit 1 || echo 'pacote ok'

test-js:  ## testes do frontend (node --test)
	docker run --rm -v $(CURDIR)/frontend:/src:ro node:22-alpine sh -c "cp -r /src /app && cd /app && npm install --no-audit --no-fund --loglevel=error >/dev/null 2>&1 && npm test"

lint-js:  ## ESLint do frontend
	docker run --rm -v $(CURDIR)/frontend:/src:ro node:22-alpine sh -c "cp -r /src /app && cd /app && npm install --no-audit --no-fund --loglevel=error >/dev/null 2>&1 && npm run lint"

check: test lint test-js lint-js  ## tudo que dá para verificar sem subir os serviços

legacy:  ## interface antiga em Streamlit (http://localhost:8501), opcional
	$(COMPOSE) --profile legacy up -d --build streamlit
