# Plano de implementação

As tarefas marcadas [x] já estão no repositório e validadas com os dados reais. As tarefas [ ] são para a Ilza executar no Kiro durante o hackathon, em ordem de prioridade para a banca.

- [x] 1. Estrutura do projeto, config e steering
- [x] 2. Ingestão com validação de schema e flags de qualidade — _R1_
- [x] 3. Decodificação da série e chave de ordem — _R3_
- [x] 4. Taxonomia da voz do técnico e flags de kits — _R4_
- [x] 5. DNA: sequência, reincidência e ficha por máquina — _R5_
- [x] 6. Melhoria × impacto: corte de série e retrofit, com IC e p-valor — _R6_
- [x] 7. Duas vozes e radar — _R7, R8_
- [x] 8. App Streamlit com 6 páginas — _R1–R8_
- [x] 9. Importação de nova base pela interface — _R2_
- [x] 10. Testes unitários e README com premissas
- [x] 10a. Modelo de risco de retorno (ML) + página — _R10_
- [x] 10b. Resumo para o técnico com LLM (Bedrock + cache + fallback) — _R11_
- [x] 10c. Histórico confiável com IA (coorte recuperada, causa provável, nota) — _R12_
- [x] 10d. Padrões no texto (TF-IDF + NMF, boletins citados) — _R13_
- [x] 10e. Assistente de engenharia com ferramentas + parecer (substituído pela Cora na tarefa 33) — _R14_
- [x] 19. Backend FastAPI separado, com rotas por domínio e cache — _R15_
- [x] 20. Frontend estático (nginx) com 9 telas, inspirado no Mercafé — _R16_
- [x] 21. Máscara de dado pessoal, CSP e cabeçalhos de segurança — _R15, R16_
- [x] 22. Containers (compose), dependências fixadas, `make check`, `make smoke`
- [x] 23. Correção do bug de grupo vazio em `impact`, com testes de regressão — _R6_
- [x] 24. Revisão do projeto, arquitetura e roteiro da demo (`docs/`) — _R9_
- [x] 24a. Máscara de privacidade também na ida ao LLM, e ferramentas para a outra máquina: `bedrock_check`, `bedrock_warm`, `demo-ready`, prompt do Kiro — _R15_

## Para fazer no Kiro (14/10)
Primeiro, no notebook da demo: cole o prompt de `docs/PROMPT_KIRO.md` (patch e subida do kit da Cora, `make demo-ready`,
seed do conector e pré-voo). Precisa da planilha em `data/raw/` e da credencial AWS **do kit da Cora** (o MVP não precisa
de nenhuma). Depois, por prioridade para a banca:
- [x] 32a. Boletins: leitura do PDF, tipo por série, código de melhoria, coluna `codigo_melhoria` na importação, selos no frontend (feito)
- [x] 32b. Base sintética de validação, `make sintetico` e `docs/VALIDACAO.md` (feito)
- [x] 32c. Tela Grafo (SVG, sem biblioteca): série no centro, voz do CS, voz do técnico, melhorias do P&D e retornos em 90 dias (feito)
- [x] 33. **Assistente = Cora**: análises publicadas como servidor MCP (`backend/app/mcp_server.py`, 11 ferramentas `dna_*`, base mascarada, só leitura), página Assistente incorporando `<Cora>/embed` com contexto da tela, seed do conector (`integracoes/cora/`), `make mcp-check`; agente com Bedrock removido do MVP (ver `docs/CORA.md`)
- [x] 36. Entrada com áreas P&D e Pós-venda, menus por área, listas que abrem e fecham, modelo com foto no DNA, boletins com código do projeto — _R17_
- [x] 37. Estoque × melhoria: fonte nova (posição por série), levantamento, peças, CSV, marcação "aplicada", base de exemplo fictícia — _R18_
- [ ] 38. Colocar as **fotos oficiais** dos modelos em `frontend/public/assets/modelos/` e confirmar qual modelo é a foto do briefing — _R17.5_
- [ ] 39. Pedir à empresa a **posição de estoque real** (ERP/WMS) e confirmar com o P&D as premissas P10/P11 (data de entrada de cada melhoria na linha) — _R18_
- [ ] 34. **Cora no dia**: confirmar com os organizadores se o kit roda local, a porta e a credencial AWS do kit; aplicar o patch `integracoes/cora/cora-fix-uuid-conectores.patch`; rodar o seed com a `DNA_MCP_URL` certa; 3 perguntas de ensaio com o selo de ferramenta
- [ ] 35. **Reportar aos organizadores** o bug de conectores do kit da Cora (id do usuário como texto × UUID no RBAC)
- [ ] 32. Recomendação à empresa (fora do protótipo): campo de lista "Código da melhoria" no chamado; já evidenciado na tela Início, em "Pontos de melhoria que identificamos"
- [ ] 31. (Opcional) Resumo da página DNA pelo Bedrock: `DNA_USE_BEDROCK=1` + `make bedrock-check`; nunca foi chamado com credenciais reais
- [ ] 25. **Avisar a organização** sobre o telefone real na linha 16165 da planilha (Conclusão Técnica)
- [ ] 26. **Confirmar com o P&D** a decodificação da série (premissa P1) e se o diretório oficial tem mais melhorias que os 3 cadastrados
- [ ] 27. Alinhar o visual com o guia da Karen (`docs/GUIA_DESIGN_KAREN.md`): o frontend usa o Mercafé como referência; ajustar os tokens em `frontend/public/css/styles.css` — _R16_
- [ ] 28. Montar o **pacote de entrega** sem `data/raw`, sem `demo-offline/` e sem o boletim interno (o `dna-maquina-mvp.zip` já faz isso)
- [ ] 29. (ver docs/CHECKLIST_DIA_DO_EVENTO.md) Ensaiar o pitch com `docs/ROTEIRO_DEMO.md` (5 min + 3 de perguntas) e rodar `make demo-check` antes de subir ao palco
- [ ] 15. Exportar o resultado de Melhoria × impacto para PDF ou CSV ("levar para a revisão de engenharia") — _R6_
- [ ] 17. (Opcional) Pré-gerar o cache dos resumos da página DNA (`make bedrock-warm`) — _R11_
- [ ] 16. Deploy **privado** na AWS (ECS ou App Runner, com login Cognito e dados no S3). Não publicar sem login: a API serve os dados do desafio — _R9_
- [ ] 18. (Opcional) Classificação da conclusão via Bedrock em amostra de 200 chamados, comparada às regras — _R9.3_
- [ ] 30. (Opcional) CI no GitHub Actions rodando `make check` — _qualidade_

Observações: as tarefas 11, 13 e 14 do plano original já estão atendidas (números conferidos, "Caso bandeja" é a tela
Melhorias aberta por padrão, testes de tela existem). Integração com a Cora testada com o kit real, exceto o modelo
(sem credencial no ambiente de teste). Bedrock do MVP (opcional) **não foi validado** com credenciais reais.
