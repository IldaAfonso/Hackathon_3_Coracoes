# Frontend estático da DNA da Máquina (nginx sem privilégios).
#   docker build -f frontend/Dockerfile -t dna-frontend frontend
# Fala só com a API, via proxy reverso em /api (mesma origem: sem CORS),
# e repassa /mcp (ferramentas para a Cora) ao backend.
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Templates: o entrypoint oficial do nginx roda envsubst nos *.template
# de /etc/nginx/templates e grava em /etc/nginx/conf.d/ (só as variáveis
# que existem no ambiente são trocadas).
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY security-headers.inc /etc/nginx/templates/security-headers.inc.template
# Origem da Cora liberada no iframe; 'none' = nenhuma (sem Cora).
ENV CORA_FRAME_SRC="'none'"
COPY public /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s \
  CMD wget -q --spider http://127.0.0.1:8080/healthz || exit 1
