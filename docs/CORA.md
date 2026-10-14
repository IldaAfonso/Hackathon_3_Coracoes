# Assistente com a Cora (substitui o assistente com Bedrock)

O assistente de engenharia do DNA da Máquina agora é a **Cora**, a IA
corporativa do Grupo 3corações. O MVP **não chama mais modelo de
linguagem para conversar**: ele publica as análises como ferramentas e a
Cora as usa.

```
Navegador ── página Assistente (MVP, :8080)
   │            └── iframe  <Cora>/embed  ←─ contexto da tela (série, melhorias)
   │
Cora (backend) ── modelo (Bedrock, configurado na Cora) decide a ferramenta
   │
   └── conector MCP "DNA da Máquina" ──► MVP  /mcp  (11 ferramentas dna_*)
                                            └── Toolbox → análises testadas
                                                (base MASCARADA, só leitura)
```

| Peça | Onde | O que faz |
|---|---|---|
| Servidor MCP | `backend/app/mcp_server.py` | Publica 11 ferramentas `dna_*` em `/mcp` (streamable HTTP, sem estado) |
| Ferramentas | `src/dna_maquina/assistant.py` (`Toolbox`) | As mesmas funções já testadas: impacto, DNA, duas vozes, radar, modos de falha… |
| Página Assistente | `frontend/public/js/pages/assistant.js` + `cora.js` | Abre a Cora num iframe e envia o contexto da tela; plano B por regras logo abaixo |
| Rota de configuração | `GET /api/assistant/cora` | Diz à página onde está a Cora (`DNA_CORA_URL`) |
| Seed da Cora | `integracoes/cora/seed_dna_maquina.py` | Cadastra o conector e libera o acesso (RBAC) |
| Diagnóstico | `make mcp-check` | Lista e chama as ferramentas em `/mcp`, como a Cora faz |

## O que já foi testado de ponta a ponta

Com a Cora real do kit (backend + Postgres + migrações + seed + frontend
compilado, `AUTH_BYPASS`) e o MVP atrás do nginx real com os templates:

1. o seed cadastrou o conector, a role e as 11 ferramentas (e rodou de
   novo sem duplicar); a tela de Conectores mostra **ok / Disponível para
   todos**;
2. a página Assistente abriu `<Cora>/embed` no iframe (CSP com `frame-src`
   só da Cora), a sessão foi aceita e o contexto da tela (série em foco,
   melhorias) chegou ao prompt da Cora dentro de `<embed_context>`;
3. uma pergunta digitada no chat da Cora virou chamada a
   `dna_avaliar_melhoria` pelo nginx (`POST /mcp`), a resposta trouxe os
   números reais (15,4% → 15,1%, p = 0,909), o chip "1 ferramenta"
   apareceu e a Cora gravou a auditoria (`tool_calls`, origem `mcp`).

Único pedaço simulado: o modelo de linguagem (sem credencial do Bedrock no
ambiente de teste, um modelo roteirizado pediu a ferramenta e escreveu a
resposta). No evento, o modelo é o Claude configurado no kit da Cora.

## Ferramentas que a Cora enxerga

| Ferramenta | Pergunta que responde |
|---|---|
| `dna_listar_melhorias` | Quais melhorias (boletins) existem e seus ids |
| `dna_listar_sintomas` | Grafia exata dos sintomas (para os filtros) |
| `dna_avaliar_melhoria` | A melhoria funcionou? Antes × depois, IC 95%, p-valor, premissas |
| `dna_historico_maquina` | DNA de uma máquina pelo número de série |
| `dna_contar_chamados` | Contagem com filtros (modelo, sintoma, ano de fabricação, meses) |
| `dna_duas_vozes` | O que o técnico encontrou para um sintoma do consumidor |
| `dna_radar` | O que mais cresceu nos últimos 3 meses |
| `dna_modos_de_falha` | Temas no texto dos técnicos (TF-IDF + NMF) e boletins citados |
| `dna_maquinas_cronicas` | Máquinas com 3 ou mais chamados |
| `dna_qualidade_dos_dados` | Quanto dá para confiar na base |
| `dna_parecer_tecnico` | Fatos + rascunho por regras para o parecer ao P&D |

Garantias (com teste em `tests/test_mcp.py`): só leitura; base mascarada
na entrada e máscara de novo na saída (telefone, e-mail, CPF, CEP); erro
vira mensagem para o modelo, não queda; só hosts da lista
`DNA_MCP_ALLOWED_HOSTS` são aceitos (proteção contra *DNS rebinding*).

## Passo a passo (ambiente do hackathon, tudo local)

Pré-requisito: o kit da Cora rodando (README da raiz do kit), com
`AUTH_BYPASS=true` e `ENVIRONMENT=local` — o modo de desenvolvimento em
que o `/embed` funciona sem o login corporativo.

**Credenciais:** só uma, a **AWS do kit da Cora** (o modelo dela,
`us.anthropic.claude-sonnet-5-5`, roda no Bedrock), exportada no terminal
ou no `.env` do kit antes de subi-lo. Não há login nem chave da Cora no
modo de teste, e o MVP não precisa de credencial nenhuma. Detalhes em
[BEDROCK_E_AWS.md](BEDROCK_E_AWS.md). No Kiro, tudo isso roda no terminal
do próprio Kiro ([GUIA_ILZA_KIRO.md](GUIA_ILZA_KIRO.md)).

**1. Suba o MVP dizendo onde está a Cora** (a URL que o NAVEGADOR usa):

```bash
export DNA_CORA_URL=http://localhost:8000     # ajuste para a porta da Cora no kit
make up
make mcp-check                                # deve listar 11 ferramentas
# ou, de uma vez antes do palco: make demo-ready
```

`DNA_CORA_URL` faz duas coisas: a página Assistente abre `<url>/embed` e
o nginx libera **só essa origem** no iframe (`frame-src` da CSP).

**2. Corrija um bug do kit da Cora (uma linha, obrigatório).** No kit
recebido, o `/chat` passa o id do usuário como texto e o RBAC dos
conectores espera UUID: para quem está em algum grupo explícito — o
usuário do bypass está em Administradores — o turno **sobe sem nenhuma
ferramenta MCP** (no log: `[MCP] kit indisponível` com `KeyError: UUID(...)`).
A correção está em `integracoes/cora/cora-fix-uuid-conectores.patch`:

```bash
cd <kit>    # pasta que contém cora-backend/
patch -p1 < <mvp>/integracoes/cora/cora-fix-uuid-conectores.patch
docker compose up -d --build backend
```

Vale avisar os organizadores: afeta qualquer conector MCP, não só o nosso.

**3. Cadastre o conector na Cora** (uma vez; o script é idempotente):

```bash
cp integracoes/cora/seed_dna_maquina.py <kit>/cora-backend/scripts/
cd <kit>
docker compose exec -e DNA_MCP_URL=http://host.docker.internal:8080/mcp \
    backend python scripts/seed_dna_maquina.py
# [seed-dna] ok — conector 'DNA da Máquina' em ..., role connector:dna-da-maquina concedida a 'default', 11 ferramentas
```

`DNA_MCP_URL` é a URL do `/mcp` **como o container da Cora enxerga o
MVP**:

| Onde a Cora roda | `DNA_MCP_URL` |
|---|---|
| Container (Docker Desktop: Mac/Windows) | `http://host.docker.internal:8080/mcp` |
| Container no Linux | idem, com `extra_hosts: ["host.docker.internal:host-gateway"]` no serviço da Cora |
| Mesma rede Docker do MVP (`docker network connect dna-maquina_default <container da cora>`) | `http://frontend:8080/mcp` |
| Fora de container (uvicorn direto) | `http://localhost:8080/mcp` |

Sem o script, dá para fazer o mesmo pela interface da Cora (o usuário do
bypass é administrador): **Conectores → novo conector** com a URL acima
(a Cora sonda, vê que não pede login e grava `auth_type = none`), depois
**Acesso → grupo `default` → conceder `connector:dna-da-maquina`**.

**4. Use.** Abra http://localhost:8080/#/assistente (ou, na página DNA de
uma máquina, **Perguntar à Cora sobre esta máquina**, que já envia a
série como contexto). Perguntas para a demo:

- "O kit de adaptação hidráulica reduziu os retornos? Cite as premissas."
- "A bandeja de cápsulas funcionou? Monte o parecer técnico para o P&D."
- "O que está crescendo no Luna nos últimos 3 meses?"
- "Resuma o DNA desta máquina e diga quais melhorias se aplicam a ela."

A Cora mostra, no chip de cada resposta, quais ferramentas `dna_*` usou.

## Quando algo não aparece

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Página mostra "A Cora ainda não foi configurada" | `DNA_CORA_URL` vazio | `export DNA_CORA_URL=...` e `make up` |
| Iframe em branco / bloqueado pelo navegador | CSP com outra origem | `DNA_CORA_URL` precisa ser exatamente a origem que o navegador abre (esquema, host e porta) |
| "A Cora não encontrou uma sessão" | Cora sem `AUTH_BYPASS` e sem login | Entrar na Cora em outra aba, ou ligar o bypass no ambiente local |
| Cora responde sem chamar `dna_*` e o log da Cora tem `KeyError: UUID` | Bug do kit (passo 2) | Aplicar o patch e reconstruir o backend da Cora |
| Cora responde sem chamar `dna_*` | Conector sem concessão ou inalcançável | Rodar o seed de novo e ler o aviso; na Cora, tela Conectores deve mostrar status **ok** |
| `make mcp-check` dá 421 | Host fora da lista | Acrescente o host em `DNA_MCP_ALLOWED_HOSTS` (ex.: `minha-maquina:*`) |

## Se a Cora for hospedada (e não o kit local)

Se os organizadores oferecerem uma Cora já hospedada em vez do kit local,
o passo a passo acima não se aplica:

1. Cada pessoa entra com o **login corporativo** (não existe bypass).
2. O conector é cadastrado por um **administrador da Cora** (tela
   Conectores), que também concede `connector:dna-da-maquina` ao grupo.
3. O iframe exige a **chave de integração** (ver "Produção" abaixo).
4. A Cora hospedada precisa **alcançar** o `/mcp` do MVP — um notebook na
   rede do evento normalmente não é alcançável, e expor o `/mcp` sem login
   na internet não é seguro.

Por isso, pergunte aos organizadores primeiro: "o kit roda local na nossa
máquina?". O kit recebido (scripts, seed, `AUTH_BYPASS`) indica que sim.

## Produção (fora do hackathon)

- O `/mcp` não tem login próprio (é o que permite `auth_type = none`):
  manter só na rede interna, nunca exposto à internet. Para expor, a Cora
  já suporta conector com OAuth2 — seria preciso pôr OAuth na frente do
  `/mcp`.
- Trocar o grupo `default` por um grupo do P&D: `DNA_CORA_GRUPO=custom:...`
  no seed.
- Sem `AUTH_BYPASS`, o host gera a sessão do iframe por
  `POST /auth/embed/session` com a chave de integração (`X-Cora-Embed-Key`,
  tabela `embed_integrations`), sempre do lado do servidor — a chave nunca
  vai para o navegador.

## O que continua com Bedrock (opcional)

Só o **resumo em texto da página DNA** (`llm.py`), ligado por
`DNA_USE_BEDROCK=1`; desligado, sai por regras. Se a equipe quiser, ele
também pode virar pergunta à Cora ("resuma o DNA desta máquina"), que já
funciona pela ferramenta `dna_historico_maquina`.
