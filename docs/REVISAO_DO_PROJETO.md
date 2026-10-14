# Revisão: arquivos do desafio e do projeto

Data: 13/10/2026. Escopo: a pasta `docs_desafio` e o projeto da equipe
(`dna-maquina.zip`, feito no evento com o Kiro).

## 1. O que a organização forneceu

| Arquivo | O que é | Avaliação |
|---|---|---|
| `DNA da Máquina.html` | Briefing oficial (19 slides): desafio, personas (Marina, Carlos, Rafael, Juliana), três pontos onde a informação escapa, sete dores do P&D, dados, entregas e critérios | É a fonte de verdade do que será avaliado. Pede **quatro entregas**: protótipo com os dados reais, **um caso ponta a ponta** (uma melhoria do G5 Passione, antes e depois), pitch de 5 min e código com README e premissas. O diferencial é **importar uma nova base .xlsx**. O foco são as dores **04** (melhoria × impacto), **06** (dados lentos) e **07** (sem histórico por máquina) |
| `Relatório Reclamações 2025 a 2026 (G5 Passione + G4 Luna).xlsx` | 30.481 chamados × 16 colunas, de 2025 a set/2026 | Rico, mas imperfeito de propósito: 21% sem conclusão técnica; 164 chamados abertos antes da instalação; 21.079 séries brutas. **Contém 1 telefone real** em texto livre (coluna Conclusão Técnica, linha 16165), embora o briefing prometa base sem dado pessoal. Vale avisar a organização |
| `BTG5 - Adaptação Hidraulica.pdf` | Boletim técnico **INTERNO**, G5 Passione, 11/10/2022 (rev. 21/09/2023), para eliminar vazamentos: troca de mangueiras, conector e junção "T" (peças 3002832, 3002821, 3000053) | É o "kit" cuja eficácia o projeto mede. Por estar marcado INTERNO, **não deve ser publicado** |
| `dna-maquina.zip` | O projeto da equipe: 14 módulos, app Streamlit de 9 telas, 25 testes, specs do Kiro | Ver seções 2 e 3 |

Faltou na pasta o **Documento 02 do briefing** (diretório de melhorias do G5
Passione). A equipe o reconstruiu em `data/melhorias.json` com três itens, a
partir de boletins. Confirmar com o P&D se o diretório oficial tem outros.

## 2. O que eu verifiquei, e como

Recalculei **direto da planilha**, sem usar o código da equipe:

| Afirmação do README | Recálculo independente | Resultado |
|---|---|---|
| 30.481 chamados | 30.481 | Confere |
| 20,9% sem conclusão técnica | 20,9% | Confere |
| 164 chamados abertos antes da instalação | 164 | Confere |
| 22% dos chamados são a mesma máquina voltando em 90 dias | 22,7% pela série crua; 22,1% pela série normalizada do pipeline | Confere; a diferença vem da normalização |
| 2.019 máquinas com 3 ou mais chamados | 2.068 pela série crua | **Explicado:** 2.068 inclui agrupamentos de série ilegível; só séries válidas dão 2.019, como no README |

**Não recalculei de forma independente:** os 19,6% × 14,2% da bandeja, os
15,1% × 15,4% do kit, as métricas dos modelos de ML (AUC 0,70; 69% no top 3)
e os modos de falha. Vêm do código da equipe, que tem testes, e a API os
reproduz (bandeja "Funcionou", kit "Sem efeito mensurável"), mas isso prova
consistência, não correção independente.

## 3. Achados do projeto

| # | Achado | Gravidade | Tratamento |
|---|---|---|---|
| 1 | **Bug no núcleo:** `impact` quebrava com `ValueError: cannot convert float NaN to integer` quando um dos grupos (antes ou depois) ficava vazio, por exemplo após importar uma base parcial. A tela "Melhoria × impacto" cairia | Alta | **Corrigido** (`_compare_groups`): vira "Amostra insuficiente". Dois testes de regressão |
| 2 | **Dado pessoal:** o telefone real aparece no texto que o app mostra na linha do tempo; não havia nenhum tratamento de dado pessoal | Alta | **Corrigido na API** (mascaramento) com testes. Nomes próprios e endereços não são detectados |
| 3 | **A planilha real está dentro do zip** e fora do `.gitignore` (estava comentada). Publicar o repositório vazaria os dados do desafio | Alta | `.gitignore` e `.dockerignore` agora a excluem; no container ela é montada, nunca copiada. O regulamento (Art. 37) limita o uso dos dados ao evento |
| 4 | Tela e análise no mesmo processo (Streamlit): não há API para o Salesforce ou o app do técnico consumirem | Média | **Separado** em backend (API) e frontend, como pedido |
| 5 | Contagem por máquina incluía séries ilegíveis como se fossem máquinas | Média | Corrigido no diagnóstico novo, com teste |
| 6 | O `requirements.txt` não fixa versões: o `pip` de hoje instala pandas 3 e numpy 2.5 | Baixa | Código testado nessas versões (25 testes passam); o container fixa as versões |
| 8 | **Dado pessoal indo para a AWS:** o resumo da máquina envia ao Bedrock o texto digitado pelo técnico, sem máscara (`str(conclusion)[:160]` em `llm.build_machine_facts`). Para a máquina com o telefone real, o número sairia da máquina e ficaria no cache. O assistente também tenta o Bedrock sem consultar `DNA_USE_BEDROCK` | Alta | **Corrigido na API:** resumo, assistente e parecer recebem uma cópia mascarada da base (`state.masked()`), com teste que captura o prompt. O núcleo da equipe não foi alterado |
| 9 | **Bug no kit da Cora** (achado no teste de integração): o `/chat` passa o id do usuário como texto e o RBAC dos conectores espera UUID; para quem está em grupo explícito (ex.: o usuário de teste, que é administrador), a conversa sobe **sem nenhuma ferramenta MCP** | Alta | Patch de uma linha em `integracoes/cora/cora-fix-uuid-conectores.patch`, testado com o kit real; reportar aos organizadores |
| 7 | Numeração: o README diz "Desafio 01" e o regulamento chama DNA das Máquinas de desafio 2 | Informativa | O próprio briefing diz "Desafio 01 · TRES®"; o README está coerente com ele |

O núcleo passa na configuração `ruff` da própria equipe (E, F, W, I, 79 colunas).

## 4. Pontos fortes

- Cada premissa de negócio vira um teste que a documenta.
- Dado inferido nunca se mistura com dado registrado, e a tela diz qual é qual.
- Honestidade estatística: amostra pequena vira "insuficiente", e o kit
  hidráulico aparece como "sem efeito mensurável" em vez de ser vendido.
- As análises funcionam sem internet e trazem o diferencial de importar `.xlsx`.
- O assistente é a **Cora** da empresa, usando as análises como ferramentas MCP: testado de ponta a ponta com o kit real (cadastro do conector, iframe, chamada da ferramenta e auditoria), exceto o modelo, que exige a credencial AWS do kit.

## 5. Para o pitch (o enquadramento combinado)

1. **O histórico de hoje não atende.** Mostre os números reais: 20,8% dos
   chamados sem conclusão do técnico; 22,1% voltando em 90 dias; 2.019
   máquinas crônicas; 3,1% de séries ilegíveis; 29 boletins citados em campo
   fora do diretório. A Visão geral (`#/visao-geral`) já traz isso.
2. **O número de série liga os três times** (CS, Pós-vendas, P&D). É a chave
   que já existe nos três.
3. **O caso ponta a ponta:** bandeja de cápsulas, de 19,6% para 14,2% (−28%,
   p < 0,001). Em contraste, o kit hidráulico não mostrou efeito: dizer isso é
   um ponto a favor da credibilidade.
4. **O que implantar:** validar a série na entrada, campo estruturado de peça
   trocada, ligar chamado e laudo, cadastrar cada melhoria com a série de corte.
5. **Limites ditos em voz alta:** associação não é causa; o indicador é de
   *mix*, não de taxa por máquina instalada (falta a base instalada); a
   Cora é o kit local do hackathon (login de teste); sem deploy AWS ainda.

## 6. Pendências antes da entrega

- Confirmar com o P&D a premissa P1 (decodificação da série) e o diretório de melhorias.
- Avisar a organização sobre o telefone na linha 16165.
- Decidir o que vai no pacote de entrega: **sem** `data/raw` e **sem** o boletim interno.
- Subir o kit da Cora com a credencial AWS do kit, aplicar o patch e ensaiar 3 perguntas (docs/CORA.md).
- Reportar aos organizadores o bug de conectores do kit da Cora (`integracoes/cora/`).
