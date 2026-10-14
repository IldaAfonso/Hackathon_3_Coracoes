# Como continuar no Kiro (14/10)

## 1. Abrir e subir (5 minutos)

1. Descompacte `dna-maquina-mvp-cora.zip` e abra a pasta no Kiro.
   O steering (`.kiro/steering/`) é lido automaticamente e já descreve o projeto de hoje.
2. **Coloque a planilha em `data/raw/`.** Ela NÃO vem no zip (são dados do desafio, Art. 37).
   Use o arquivo da pasta `docs_desafio` (`Relatório Reclamações 2025 a 2026 ...xlsx`).
3. Precisa de **Docker** com Compose. Nada mais é instalado na máquina.
4. `export DNA_CORA_URL=http://localhost:<porta da Cora>`, `make demo-ready`, depois abra
   http://localhost:8080 e rode `make demo-check`. Só vá para o palco quando aparecer
   **PRONTO PARA O PALCO**.

**A interface abre na entrada com duas áreas:** P&D (Melhorias, Boletins, Estoque, DNA, Riscos) e
Pós-venda (DNA, Boletins só lista, Estoque, Riscos). A Visão geral do pitch fica em `#/visao-geral`.
O **Estoque** é uma fonte nova (posição por série do ERP/WMS): até a real ser importada, a tela usa uma
base de exemplo fictícia e avisa. Fotos dos modelos: `frontend/public/assets/modelos/LEIA-ME.md`.

**O assistente é a Cora.** Ela roda pelo kit dos organizadores e chama as análises do MVP
pelo servidor MCP (`/mcp`). Passo a passo, patch do kit e cadastro do conector:
[`docs/CORA.md`](CORA.md). Prompt pronto para o Kiro: [`docs/PROMPT_KIRO.md`](PROMPT_KIRO.md).
Guia da Ilza: [`docs/GUIA_ILZA_KIRO.md`](GUIA_ILZA_KIRO.md).

**Credencial:** só a Cora precisa de credencial AWS (o modelo dela roda no Bedrock); ela vai no
terminal ou no `.env` **do kit da Cora**. O MVP não precisa de nenhuma. O Bedrock do MVP é
opcional e só redige o resumo em texto da página DNA ([`docs/BEDROCK_E_AWS.md`](BEDROCK_E_AWS.md)).

## 2. O que tem no zip

| Pasta ou arquivo | O que é |
|---|---|
| `backend/`, `frontend/`, `compose.yaml` | API FastAPI e interface web, em containers separados |
| `src/dna_maquina/` | Núcleo analítico da equipe (só `impact.py` foi corrigido) |
| `.kiro/` | Steering e specs **atualizados**: stack, estrutura, regras de privacidade e as tarefas em `tasks.md` |
| `backend/app/mcp_server.py`, `integracoes/cora/` | Ferramentas para a Cora (MCP), seed do conector e patch do kit da Cora |
| `docs/CORA.md` | Como a Cora entra no MVP, passo a passo, testes feitos e solução de problemas |
| `docs/ROTEIRO_DEMO.md` | Roteiro do pitch de 5 minutos, perguntas da banca e plano B |
| `docs/REVISAO_DO_PROJETO.md`, `docs/ARQUITETURA.md` | O que foi verificado e como o MVP é montado |
| `backend/scripts/`, `scripts/demo_ready.sh`, `Makefile` | Pré-voo, `mcp-check` (ferramentas da Cora), diagnóstico opcional do Bedrock e comandos de rotina |
| `docs/PROMPT_KIRO.md`, `docs/BEDROCK_E_AWS.md` | Prompt pronto para o Kiro e guia de credenciais (Cora e Bedrock opcional) |

**Não vêm no zip, de propósito:** a planilha real, o boletim técnico interno (PDF) e as imagens
de reserva da demo (`demo-offline/`, têm trechos de dados reais).

## 3. Para pedir ao Kiro

As tarefas abertas estão em `.kiro/specs/dna-da-maquina/tasks.md` (itens 25 a 34 e os antigos 15 a 18).
Ao abrir cada uma, lembre ao Kiro as regras do steering:

- **Não** criar página Streamlit: tela nova é um módulo em `frontend/public/js/pages/` mais uma rota em `backend/app/routers/`.
- Texto digitado por pessoas passa pela máscara de privacidade e **nunca** entra com `innerHTML`.
- Conferir com `make check` antes de dar a tarefa por pronta (PEP 8: 79 colunas, docstrings de 72).
- Pergunta nova para a Cora = função pura no núcleo + método no `Toolbox` + ferramenta `dna_*` em `backend/app/mcp_server.py` + teste em `tests/test_mcp.py`. **Não** chamar modelo de linguagem dentro do MVP.
- Não colocar a planilha em imagem, repositório nem pacote.

## 4. O que ainda depende de pessoas (não do código)

- Avisar a organização sobre o **telefone real na linha 16165** da planilha.
- Confirmar com o P&D a decodificação da série (premissa P1) e se o diretório oficial de melhorias tem mais que os 3 itens cadastrados.
- **Confirmar com os organizadores** como o kit da Cora roda (local ou hospedado), a porta, e se a credencial AWS do kit já vem pronta. Avisar sobre o bug de conectores do kit (patch em `integracoes/cora/`).
- A integração com a Cora foi testada de ponta a ponta com o kit real, **exceto o modelo** (sem credencial no ambiente de teste). Ensaie 3 perguntas no dia.
- O Bedrock do MVP (resumo da página DNA) **não foi validado** com credenciais reais; é opcional e cai para regras.
- **Não há deploy na AWS.** Se fizer um, só **privado e com login** (a API e o `/mcp` não têm autenticação; a Cora do kit roda em modo de teste).
- O frontend usa o Mercafé como referência visual; alinhar com o guia da Karen (`docs/GUIA_DESIGN_KAREN.md`).
