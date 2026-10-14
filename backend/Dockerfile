# Backend da DNA da Máquina. Build a partir da RAIZ do projeto:
#   docker build -f backend/Dockerfile -t dna-backend .
# A planilha real NÃO entra na imagem: é montada em /app/data/raw (somente leitura).
FROM python:3.12.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src:/app/backend DNA_IMPROVEMENTS_FILE=/app/state/melhorias.json \
    DNA_STOCK_FILE=/app/state/estoque.csv DNA_STOCK_MARKS=/app/state/estoque_aplicacoes.json
WORKDIR /app

# requirements.txt diz O QUE usamos; requirements.lock fixa as VERSÕES testadas
# (build reproduzível: o 'mais novo' de hoje não muda o comportamento de amanhã).
COPY backend/requirements.txt backend/requirements.lock ./backend/
RUN pip install -r backend/requirements.txt -c backend/requirements.lock

RUN useradd --create-home --uid 1000 app
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app src ./src
COPY --chown=app:app backend ./backend
COPY --chown=app:app tests ./tests
COPY --chown=app:app data/melhorias.json ./data/melhorias.json
COPY --chown=app:app scripts/make_synthetic_base.py ./scripts/make_synthetic_base.py
COPY --chown=app:app data/synthetic ./data/synthetic
COPY backend/entrypoint.sh /usr/local/bin/dna-backend-entrypoint

# estado gravável (base processada, cache de LLM, modelos, catálogo de melhorias): volumes herdam este dono
RUN mkdir -p data/raw data/processed data/cache models state && chown -R app:app /app \
    && chmod +x /usr/local/bin/dna-backend-entrypoint
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=120s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

ENTRYPOINT ["dna-backend-entrypoint"]
CMD ["api"]
