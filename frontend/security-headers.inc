# Cabeçalhos de segurança. Incluído em TODO bloco que usa add_header, porque
# no nginx um add_header dentro de um location SUBSTITUI os do nível acima.
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "no-referrer" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
# Só recursos próprios: nada de script, estilo ou imagem de terceiros.
# Única exceção: o iframe da Cora (frame-src), cuja origem vem de
# CORA_FRAME_SRC na partida do container ('none' quando não configurada).
add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-src ${CORA_FRAME_SRC}; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
