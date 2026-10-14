#!/bin/sh
# Entry point of the DNA da Máquina container.
#   app       (default) process data/raw if needed, then serve the Streamlit app on :8501
#   pipeline  reprocess data/raw -> data/processed (Parquet)
#   test      run the test suite (add RUN_APP_TESTS=1 for the slow app smoke tests)
#   <other>   run any command (for example: sh)
set -e
cmd="${1:-app}"
RAW=/app/data/raw
PROCESSED=/app/data/processed/chamados.parquet

case "$cmd" in
  pipeline) shift; exec python -m dna_maquina.pipeline "$@" ;;
  test)     shift; exec python -m pytest "$@" ;;
  app)
    if ! ls "$RAW"/*.xlsx >/dev/null 2>&1 && [ ! -f "$PROCESSED" ]; then
      echo "ERRO: nenhuma planilha .xlsx em $RAW." >&2
      echo "A planilha NÃO vai dentro da imagem (dados do desafio). Monte a pasta com:" >&2
      echo "  -v \"\$PWD/data/raw:/app/data/raw:ro\"   (ou use: docker compose up)" >&2
      exit 1
    fi
    # reprocess when there is no processed base yet, or a spreadsheet is newer than it
    if [ ! -f "$PROCESSED" ] || [ -n "$(find "$RAW" -name '*.xlsx' -newer "$PROCESSED" 2>/dev/null)" ]; then
      echo ">> processando a base (≈20 s)..."
      python -m dna_maquina.pipeline
    fi
    exec streamlit run app/streamlit_app.py --server.address=0.0.0.0 --server.port=8501 \
         --server.headless=true --browser.gatherUsageStats=false
    ;;
  *) exec "$@" ;;
esac
