# Guia da Ilza: o DNA da Máquina no AWS Kiro (com a Cora)

O código já roda com os dados reais. Seu trabalho no Kiro é **abrir, subir
o MVP e a Cora, conferir e ensaiar**. Não é preciso reescrever nada.

```
Kiro (editor + terminal, no seu computador)
  ├── terminal 1: kit da Cora   → http://localhost:<porta da Cora>   (credencial AWS só aqui)
  └── terminal 2: MVP           → http://localhost:8080               (nenhuma credencial)
                                      página Assistente = Cora dentro do MVP
```

## 1. Abrir o projeto (5 min)

1. Descompacte `dna-maquina-mvp-cora.zip` e abra a pasta no Kiro (**File → Open Folder**).
2. O Kiro lê sozinho a pasta `.kiro/`:
   - `.kiro/steering/` (product, tech, structure): contexto que o agente usa em toda conversa.
   - `.kiro/specs/dna-da-maquina/` (requirements, design, tasks): a spec no formato do Kiro.
3. Copie a planilha para `data/raw/`. Ela **não vem no zip** e nunca vai para repositório nem pacote.
4. Precisa de **Docker com Compose**. Nada mais é instalado na máquina.

## 2. Quem precisa de credencial

| Peça | Credencial | Onde |
|---|---|---|
| Kiro (editor e agente) | A conta do próprio Kiro | Login do Kiro |
| **Cora** (conversa) | **AWS** com acesso ao Bedrock (`us.anthropic.claude-sonnet-5-5`) | Terminal ou `.env` **do kit da Cora** |
| MVP (análises e `/mcp`) | Nenhuma | — |
| Login na Cora | Nenhuma no hackathon (`AUTH_BYPASS=true` cria um usuário administrador de teste) | `.env` do kit |

Nunca cole credencial no chat do Kiro nem em arquivo do projeto: exporte no
terminal. O MVP só usaria AWS se alguém ligar `DNA_USE_BEDROCK=1` para o
resumo em texto da página DNA, o que é opcional.

## 3. Subir a Cora e o MVP (15 min)

Siga [docs/CORA.md](CORA.md); em resumo, no terminal do Kiro:

```bash
# Terminal 1 — kit da Cora (uma vez: aplicar o patch do bug de conectores)
cd <pasta do kit>
patch -p1 < <pasta do MVP>/integracoes/cora/cora-fix-uuid-conectores.patch
export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_SESSION_TOKEN=...
docker compose up -d --build

# Terminal 2 — MVP
cd <pasta do MVP>
export DNA_CORA_URL=http://localhost:<porta da Cora>
make demo-ready                       # sobe, confere o /mcp e roda o pré-voo

# De volta ao terminal 1 — cadastrar o conector na Cora (idempotente)
cp <pasta do MVP>/integracoes/cora/seed_dna_maquina.py cora-backend/scripts/
docker compose exec -e DNA_MCP_URL=http://host.docker.internal:8080/mcp \
    backend python scripts/seed_dna_maquina.py
```

Confira:

- `make demo-check` termina em **PRONTO PARA O PALCO**.
- http://localhost:8080/#/assistente mostra a Cora dentro da página.
- Pergunte "O kit de adaptação hidráulica reduziu os retornos?": a resposta
  traz o selo **1 ferramenta** e os números 15,4% → 15,1%.
- Página **P&D → Melhorias → bandeja**: **19,6% → 14,2%, veredito "Funcionou"**.
- http://localhost:8080/ abre a entrada com **P&D** e **Pós-venda**; cada uma com o seu menu.
- **P&D → Estoque → Adaptação hidráulica**: 43 máquinas a atualizar (base de exemplo
  fictícia; aviso em vermelho até importar a posição real do ERP).
- **Pós-venda → Boletins**: só a lista, cada um com o código do projeto da melhoria.
- Fotos dos modelos: coloque `passione.webp` e `luna.webp` em
  `frontend/public/assets/modelos/` (ver `LEIA-ME.md` da pasta).

## 4. Prompts prontos para o chat do Kiro

O prompt da sessão de subida e verificação está em [docs/PROMPT_KIRO.md](PROMPT_KIRO.md).
Para tarefas abertas, use **"Start task"** em `tasks.md` ou cole:

**Tarefa 27, visual da Karen**
> Leia docs/GUIA_DESIGN_KAREN.md e aplique os tokens de cor e tipografia em frontend/public/css/styles.css. Não mude a lógica nem o JavaScript. Siga o tech.md (sem estilo inline; a CSP bloqueia). Rode `make check`.

**Tarefa 15, exportar para o P&D**
> Na página Melhorias (frontend/public/js/pages/improvements.js), adicione um botão que exporta a tabela antes/depois e as premissas em CSV (UTF-8 com BOM, separador ;) para abrir direto no Excel. Gere o CSV no navegador a partir do JSON de /api/impact/{id}; não crie rota nova. Rode `make check`.

**Nova pergunta para a Cora responder**
> Preciso que a Cora responda <pergunta>. Crie a função pura em src/dna_maquina/ (com teste), exponha no Toolbox de src/dna_maquina/assistant.py e publique como ferramenta `dna_<nome>` em backend/app/mcp_server.py, com docstring que explica ao modelo quando usar. Atualize EXPECTED_TOOLS em tests/test_mcp.py e a tabela de ferramentas em docs/CORA.md. Rode `make check` e `make mcp-check`.

## 5. Divisão do tempo (14/10)

| Bloco | Ilza | Karen | Cristiano |
|---|---|---|---|
| Manhã | Subir Cora + MVP (seção 3), `make demo-check` | Ajustes de visual e deck | Confirmar com os mentores a leitura da série e o kit da Cora |
| Início da tarde | Ensaiar a demo, incluindo 3 perguntas à Cora | Vídeo de backup da demo | Roteiro e números do caso |
| Antes do pitch | Congelar o código; deixar as abas na ordem do roteiro | Passador de slides | Ensaio cronometrado (2×) |

## 6. Se algo quebrar

| Sintoma | O que fazer |
|---|---|
| Página Assistente diz "A Cora ainda não foi configurada" | `export DNA_CORA_URL=...` e `make up` de novo |
| A Cora responde sem o selo de ferramenta | Patch não aplicado (log da Cora com `KeyError: UUID`) ou seed não rodou; ver tabela em docs/CORA.md |
| Erro de acesso ao modelo na Cora | Credencial AWS do kit, região ou modelo não liberado na conta |
| `make: command not found` (Windows) | Use WSL, ou os comandos `docker compose` de docs/PROMPT_KIRO.md |
| Nova planilha com colunas diferentes | Ajuste só `COLUMN_MAP` em `src/dna_maquina/config.py` |
| A Cora caiu no palco | Role a página Assistente: as **respostas prontas por regras** funcionam sem IA |
