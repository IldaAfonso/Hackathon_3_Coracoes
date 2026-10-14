#!/usr/bin/env bash
# Deixa o MVP pronto para a demonstração.
#
#   export DNA_CORA_URL=http://localhost:<porta da Cora>   # assistente (docs/CORA.md)
#   make demo-ready
#
# O assistente é a Cora: o MVP não precisa de credencial AWS. O Bedrock do
# MVP é OPCIONAL e só redige o resumo em texto da página DNA. Para ligá-lo:
#   export DNA_USE_BEDROCK=1 AWS_REGION=us-east-1 BEDROCK_MODEL_ID=<id>
#   export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=...
# Para pelo primeiro problema e mostra o diagnóstico; nunca imprime credenciais.
set -euo pipefail
cd "$(dirname "$0")/.."

step() { printf '\n== %s\n' "$*"; }
warn() { printf 'AVISO %s\n' "$*"; }
fail() { printf '\nFALHOU: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "Docker não encontrado."
docker compose version >/dev/null 2>&1 || fail "Docker Compose não encontrado."
ls data/raw/*.xlsx >/dev/null 2>&1 \
  || fail "coloque a planilha .xlsx em data/raw/ (ela não vem no zip)."

export DNA_USE_BEDROCK="${DNA_USE_BEDROCK:-0}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
# Sem Bedrock = resumos por regras (modo padrão). DEMO_ALLOW_OFFLINE=1
# continua aceito e força o modo sem Bedrock.
offline=1
[ "$DNA_USE_BEDROCK" = "1" ] && offline=0
[ "${DEMO_ALLOW_OFFLINE:-0}" = "1" ] && offline=1 && export DNA_USE_BEDROCK=0
[ -n "${DNA_CORA_URL:-}" ] \
  || warn "DNA_CORA_URL vazio: a página Assistente mostra só o plano B (docs/CORA.md)."

files=(-f compose.yaml)
if [ -z "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_PROFILE:-}" ]; then
  files+=(-f compose.aws.yaml)
fi
if [ "$offline" != "1" ] && [ -z "${AWS_ACCESS_KEY_ID:-}" ] \
   && [ -z "${AWS_PROFILE:-}" ]; then
  warn "DNA_USE_BEDROCK=1 mas sem AWS_ACCESS_KEY_ID nem AWS_PROFILE neste terminal."
fi

step "subindo os serviços"
docker compose "${files[@]}" up -d --build

step "esperando o backend ficar saudável"
for _ in $(seq 1 90); do
  if curl -fs http://localhost:8080/api/health >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fs http://localhost:8080/api/health >/dev/null 2>&1 \
  || fail "o backend não ficou saudável: veja 'docker compose logs backend'."

if [ "$offline" = "1" ]; then
  warn "Bedrock do MVP desligado: resumos da página DNA por regras (normal)."
else
  step "Bedrock: diagnóstico"
  docker compose "${files[@]}" exec -T backend \
    python backend/scripts/bedrock_check.py \
    || fail "Bedrock não está pronto. Leia o diagnóstico acima e docs/BEDROCK_E_AWS.md."
  step "Bedrock: aquecendo o cache da demonstração"
  docker compose "${files[@]}" exec -T backend \
    python backend/scripts/bedrock_warm.py \
    || fail "nem tudo entrou no cache. Rode 'make bedrock-check' para ver por quê."
fi

step "ferramentas para a Cora (/mcp)"
docker compose "${files[@]}" exec -T backend \
  python backend/scripts/mcp_check.py \
  || fail "o /mcp não respondeu: veja 'docker compose logs backend'."

step "pré-voo da demonstração"
docker compose "${files[@]}" exec -T \
  -e DEMO_BASE_URL=http://frontend:8080 \
  -e DEMO_REQUIRE_BEDROCK="$([ "$offline" = "1" ] && echo 0 || echo 1)" \
  backend python backend/scripts/preflight.py

printf '\nPRONTO. Abra http://localhost:8080\n'
