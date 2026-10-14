# Prompt pronto para o Kiro (14/10): subir o MVP com a Cora

Antes de colar: abra a pasta do MVP no Kiro, copie a planilha para
`data/raw/` e tenha à mão a **pasta do kit da Cora**, a **porta** em que ela
roda e a **credencial AWS do kit** (só a Cora usa; o MVP não precisa).

Cole o bloco abaixo no chat do Kiro:

````
Você é meu assistente de engenharia no projeto DNA da Máquina (esta pasta).
Objetivo da sessão: deixar o MVP rodando com a Cora como assistente e confirmar que está pronto
para a demonstração, SEM alterar código de análise.

Antes de qualquer coisa, leia: .kiro/steering/*.md, docs/CORA.md e docs/GUIA_ILZA_KIRO.md.

REGRAS (não negociáveis)
1. Nunca imprima, grave em arquivo ou faça commit de credenciais AWS. Se precisar delas, peça para EU
   exportar no terminal.
2. Não altere src/dna_maquina, backend/ nem frontend/. Esta sessão é de execução e verificação.
   A única alteração permitida no kit da Cora é aplicar o patch integracoes/cora/cora-fix-uuid-conectores.patch.
3. A planilha fica somente em data/raw/ (está no .gitignore). Não a copie para outro lugar.
4. Se um passo falhar, PARE, mostre o diagnóstico que o próprio script imprimiu e me pergunte.
5. Só diga que algo funciona se o comando correspondente passou NESTA sessão. Informe o que não foi verificado.
6. Não faça deploy, não faça push, não publique nada na internet (a Cora em modo AUTH_BYPASS dá acesso de
   administrador a quem abrir; o /mcp não tem senha).

O QUE VOCÊ PRECISA DE MIM (pergunte se eu não tiver informado)
- o caminho da pasta do kit da Cora e a porta em que ela atende (ex.: 8000);
- se a credencial AWS do kit já está no .env do kit ou se vou exportá-la no terminal;
- se a Cora roda em container (padrão do kit) ou direto na máquina.

PASSOS
1. Pré-requisitos: `docker compose version`; `ls data/raw/*.xlsx` (sem planilha, PARE e me peça).
2. Kit da Cora: na pasta do kit, rode `patch -p1 --dry-run < <MVP>/integracoes/cora/cora-fix-uuid-conectores.patch`.
   Se o dry-run passar, aplique sem --dry-run. Se disser que já foi aplicado, siga. Suba o kit conforme o
   README dele (normalmente `docker compose up -d --build`) e confirme `curl -s localhost:<porta>/health`.
3. MVP: `export DNA_CORA_URL=http://localhost:<porta>` e `make demo-ready`.
   Sem make: `docker compose up -d --build`, depois
   `docker compose exec -T backend python backend/scripts/mcp_check.py` e
   `docker compose exec -T -e DEMO_BASE_URL=http://frontend:8080 backend python backend/scripts/preflight.py`.
4. Conector: copie integracoes/cora/seed_dna_maquina.py para cora-backend/scripts/ do kit e rode, na pasta do kit,
   `docker compose exec -e DNA_MCP_URL=<url> backend python scripts/seed_dna_maquina.py`, com <url> pela tabela de
   docs/CORA.md (Cora em container no Mac/Windows: http://host.docker.internal:8080/mcp). A saída deve terminar com
   "11 ferramentas". Se vier AVISO de que não alcançou o MVP, ajuste a URL pela tabela e rode de novo.
5. Confirme sem navegador: `curl -s localhost:<porta>/connectors` deve listar "DNA da Máquina" com status "ok".
6. `make check` (testes e lint) e `make demo-check` até PRONTO PARA O PALCO.
7. Relatório final em tabela: cada passo, o comando, o resultado (passou / falhou / não verificado) e as pendências.
   Termine pedindo que eu abra http://localhost:8080/#/assistente e pergunte à Cora
   "O kit de adaptação hidráulica reduziu os retornos?" — a resposta deve mostrar o selo de ferramenta.
````

## Se algo sair diferente

| Situação | O que fazer |
|---|---|
| O Kiro tenta "consertar" código | Lembre a regra 2 e peça para ele só reportar |
| O Kiro pede as credenciais no chat | Não cole: exporte no terminal do kit da Cora |
| `make: command not found` (Windows) | Use os comandos `docker compose` do passo 3, ou o WSL |
| Seed avisa que não alcançou o MVP | URL do `/mcp` errada para a rede da Cora: tabela em docs/CORA.md |
| A Cora responde sem chamar ferramenta | Patch não aplicado ou backend da Cora não reconstruído (`docker compose up -d --build backend`) |
| A Cora dá erro de acesso ao modelo | Credencial AWS do kit, região ou modelo não liberado na conta |
| Quer o resumo da página DNA por IA (opcional) | `DNA_USE_BEDROCK=1` + credencial AWS no terminal do MVP; ver docs/BEDROCK_E_AWS.md |
