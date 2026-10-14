#!/bin/sh
# api (padrão) | pipeline | test | <qualquer comando>
set -e
RAW=/app/data/raw
PROCESSED=/app/data/processed/chamados.parquet
SEED=/app/data/melhorias.json
STATE_FILE="${DNA_IMPROVEMENTS_FILE:-/app/state/melhorias.json}"

case "${1:-api}" in
  pipeline) shift; exec python -m dna_maquina.pipeline "$@" ;;
  test)     shift; exec python -m pytest "$@" ;;
  api)
    # catálogo de melhorias: semeia o volume na primeira vez (depois, o que o P&D cadastrar fica preservado)
    [ -f "$STATE_FILE" ] || cp "$SEED" "$STATE_FILE"
    if ! ls "$RAW"/*.xlsx >/dev/null 2>&1 && [ ! -f "$PROCESSED" ]; then
      echo "ERRO: nenhuma planilha .xlsx em $RAW. Ela não vai dentro da imagem: use 'docker compose up' (monta data/raw)." >&2
      exit 1
    fi
    if [ ! -f "$PROCESSED" ] || [ -n "$(find "$RAW" -name '*.xlsx' -newer "$PROCESSED" 2>/dev/null)" ]; then
      echo ">> processando a base (≈10 s)..."
      python -m dna_maquina.pipeline
    fi
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  *) exec "$@" ;;
esac
