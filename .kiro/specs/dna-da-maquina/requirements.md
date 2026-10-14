# Requisitos: DNA da Máquina

Notação EARS (WHEN / WHILE / IF … THE SYSTEM SHALL …). Status: ✅ implementado no protótipo · 🔜 próximo passo.

## R1. Ingestão da extração de chamados ✅
**História:** Como Marina, quero carregar a extração do Salesforce sem tratar a planilha à mão, para responder perguntas em minutos.

1. WHEN uma planilha .xlsx é carregada THE SYSTEM SHALL validar as colunas obrigatórias (Número do caso, Detalhamento CS, Data de abertura, Número de série, Modelo da Máquina).
2. IF faltar coluna obrigatória THEN THE SYSTEM SHALL exibir mensagem listando as colunas faltantes e não alterar a base atual.
3. THE SYSTEM SHALL recalcular mês e ano a partir da data de abertura (as colunas originais são fórmulas).
4. THE SYSTEM SHALL normalizar o número de série (maiúsculas, sem espaços, "G5P5" → "G5PS").
5. THE SYSTEM SHALL manter registros imperfeitos e marcá-los com flags de qualidade (série inválida, instalação impossível, abertura antes da instalação, sem conclusão).

## R2. Importar nova base (diferencial) ✅
1. WHEN o usuário envia um novo .xlsx pela interface THE SYSTEM SHALL juntar à base existente usando o Número do caso como chave.
2. WHEN o mesmo caso existir nas duas bases THE SYSTEM SHALL manter a versão mais recente.
3. WHEN a importação termina THE SYSTEM SHALL recalcular todas as análises e informar quantos chamados foram lidos e o novo total.

## R3. Decodificação da série ✅
1. THE SYSTEM SHALL decodificar séries legado `G5PS000AASSNNNNN` e novas `MMMMVVVAASSNNNNN` em ano e semana de fabricação.
2. THE SYSTEM SHALL gerar uma chave de ordem que permita comparar qualquer série com a série de corte de uma melhoria.
3. IF a semana estiver fora de 1–53 ou o ano fora de 2018–2035 THEN THE SYSTEM SHALL marcar a série como inválida.

## R4. Leitura da voz do técnico ✅
1. THE SYSTEM SHALL extrair do motivo e da conclusão técnica a lista de componentes citados e uma causa principal por prioridade (peça trocada > ajuste > limpeza > orientação > sem defeito).
2. THE SYSTEM SHALL marcar se a conclusão cita os kits de campo (adaptação hidráulica, O-ring/anel, bandeja).
3. THE SYSTEM SHALL indicar se a causa encontrada é compatível com o sintoma relatado (concordância das duas vozes).

## R5. DNA da máquina ✅
**História:** Como Carlos (técnico), quero ver o que já foi feito nesta máquina antes de sair, para chegar sabendo onde olhar.

1. WHEN o usuário informa um número de série THE SYSTEM SHALL mostrar modelo, data de fabricação, número de chamados, voltas em 90 dias e se recebeu a adaptação hidráulica.
2. THE SYSTEM SHALL mostrar a linha do tempo com o sintoma relatado, a causa encontrada e o texto do técnico.
3. THE SYSTEM SHALL indicar quais melhorias de fábrica a máquina já tem (pela série) e quais kits de campo têm registro de aplicação.
4. THE SYSTEM SHALL listar as máquinas crônicas (3 ou mais chamados).

## R6. Melhoria × impacto ✅
**História:** Como Marina, quero provar, com dados, se uma melhoria reduziu as ocorrências.

1. WHERE a melhoria é do tipo corte de série THE SYSTEM SHALL comparar coortes fabricadas até 52 semanas antes e depois do corte, no mesmo período de chamados.
2. WHERE a melhoria é um kit de campo THE SYSTEM SHALL comparar a taxa de retorno em 90 dias dos reparos com o kit e sem o kit, excluindo os últimos 90 dias da base.
3. THE SYSTEM SHALL exibir as taxas com IC de 95% (Wilson), o p-valor e um veredito: Funcionou / Sem efeito mensurável / Piorou / Amostra insuficiente (n < 100).
4. THE SYSTEM SHALL mostrar na tela as premissas da análise.
5. WHEN o P&D cadastra uma nova melhoria THE SYSTEM SHALL salvá-la no diretório e disponibilizá-la para análise.

## R7. Duas vozes ✅
1. THE SYSTEM SHALL mostrar a matriz sintoma relatado × causa encontrada (% por linha).
2. THE SYSTEM SHALL mostrar a % de concordância e de "sem defeito" por sintoma.

## R8. Radar ✅
1. THE SYSTEM SHALL comparar, para cada combinação modelo × sintoma × causa, a média dos últimos 3 meses com a média histórica (escore z de Poisson) e listar as maiores altas com pelo menos 15 casos recentes.
2. THE SYSTEM SHALL apontar os lotes de fabricação (ano/semana) com participação anômala de algum sintoma.

## R10. Risco de retorno (ML) ✅
**História:** Como Rafael (CS), quero saber quais chamados encerrados têm mais chance de voltar, para ligar antes da consumidora.

1. THE SYSTEM SHALL estimar a probabilidade de novo chamado da mesma série em até 90 dias usando só informação conhecida no encerramento.
2. THE SYSTEM SHALL validar o modelo com divisão temporal (treino 2025, teste 2026) e exibir AUC, a taxa de retorno nos 10% de maior risco e a comparação com a regra simples.
3. THE SYSTEM SHALL listar os chamados dos últimos 90 dias ordenados por risco.
4. WHEN o usuário pedir THE SYSTEM SHALL retreinar o modelo com a base atual.

## R11. Resumo para o técnico (LLM) ✅
**História:** Como Carlos (técnico), quero um resumo da máquina em poucas frases antes de sair para o atendimento.

1. THE SYSTEM SHALL montar os fatos da máquina a partir dos dados e pedir ao LLM que redija usando SOMENTE esses fatos.
2. IF o Bedrock estiver desligado ou indisponível THEN THE SYSTEM SHALL exibir um resumo por regras, informando a fonte.
3. THE SYSTEM SHALL guardar em cache as respostas do LLM por série e por conteúdo dos fatos.

## R12. Histórico confiável com IA ✅
1. THE SYSTEM SHALL recuperar ano e semana de fabricação de séries ilegíveis quando existir uma ÚNICA correção plausível de um caractere, marcando o dado como recuperado.
2. THE SYSTEM SHALL sugerir as 3 causas mais prováveis para chamados sem laudo, exibidas como inferidas, com a acurácia medida em teste temporal.
3. THE SYSTEM SHALL calcular uma nota de confiabilidade (0–100) por chamado e por máquina com pesos explícitos.

## R13. Padrões no texto com IA ✅
1. THE SYSTEM SHALL agrupar as conclusões técnicas em modos de falha sem regras pré-definidas e exibir os termos que definem cada grupo.
2. THE SYSTEM SHALL mostrar os modos de falha por modelo e os que mais cresceram nos últimos 3 meses.
3. THE SYSTEM SHALL listar os boletins técnicos citados no texto livre, com primeira e última ocorrência.

## R14. Assistente de engenharia pela Cora ✅
**História:** Como Marina (P&D), quero perguntar em português na Cora, a IA da empresa, e receber a resposta com os números do DNA da Máquina e a ferramenta que os gerou.

1. THE SYSTEM SHALL publicar as análises como ferramentas MCP (`dna_*`, streamable HTTP em `/mcp`), somente leitura, calculadas sobre a base mascarada e mascaradas de novo na saída.
2. WHEN a Cora chamar uma ferramenta com argumento inválido THE SYSTEM SHALL devolver `{"erro": ...}` legível pelo modelo, sem derrubar a conversa.
3. THE SYSTEM SHALL aceitar no `/mcp` apenas os hosts de `DNA_MCP_ALLOWED_HOSTS` (proteção contra DNS rebinding).
4. WHEN `DNA_CORA_URL` estiver configurada THE SYSTEM SHALL incorporar `<Cora>/embed` na página Assistente, liberar só essa origem na CSP e enviar o contexto da tela (série em foco, melhorias), aceitando mensagens apenas da origem da Cora.
5. IF a Cora não estiver configurada ou disponível THEN THE SYSTEM SHALL oferecer perguntas prontas e o parecer técnico por regras, sem IA.
6. THE SYSTEM SHALL fornecer um seed idempotente que cadastra o conector na Cora e concede o acesso a um grupo.
7. THE SYSTEM SHALL NOT chamar modelo de linguagem para conversar dentro do MVP.

## R15. API com privacidade e diagnóstico do histórico atual ✅
- A API expõe cada análise como rota JSON e o diagnóstico do histórico de hoje (sintomas calculados na base real) e a ligação dos três times pela série.
- Nenhum dado pessoal sai pela API: telefone, e-mail, CPF e CEP em texto livre são mascarados.
- Erro inesperado devolve mensagem neutra, sem detalhe interno.
- Grupo vazio em uma comparação antes × depois resulta em "Amostra insuficiente", nunca em erro.

## R16. Interface web separada ✅
- Frontend estático servido por nginx, falando só com a API; backend sem porta pública.
- Nenhum texto da API é inserido como HTML; CSP restrita a recursos próprios.
- A demonstração funciona sem internet.

## R17. Entrada por área e listas que abrem e fecham ✅
**História:** Como pessoa do P&D ou do Pós-venda, quero entrar na minha área e ver só o que o meu time usa.

1. THE SYSTEM SHALL abrir numa entrada com as áreas P&D e Pós-venda, e a área SHALL ir na URL.
2. WHILE na área P&D THE SYSTEM SHALL mostrar no menu Melhorias, Boletins, Estoque, DNA da Máquina e Riscos.
3. WHILE na área Pós-venda THE SYSTEM SHALL mostrar DNA da Máquina, Boletins, Estoque e Riscos, e Boletins SHALL ser somente a lista de cadastrados.
4. THE SYSTEM SHALL mostrar em cada boletim cadastrado o código do projeto da melhoria.
5. WHEN o DNA de uma série for aberto THE SYSTEM SHALL mostrar o nome e a foto do modelo (ilustração neutra, com aviso, enquanto a foto oficial faltar).
6. THE SYSTEM SHALL exibir toda lista como bloco que abre e fecha, com a contagem no título.

## R18. Estoque × melhoria ✅
**História:** Como P&D, ao implantar uma melhoria quero saber quais máquinas ainda em estoque precisam dela, para o Pós-venda atualizar antes da venda.

1. THE SYSTEM SHALL importar a posição de estoque por número de série (.xlsx ou .csv; só a série é obrigatória).
2. THE SYSTEM SHALL classificar cada máquina do modelo em estoque como pendente, já aplicada, já de fábrica ou verificar (série ilegível), pelas premissas P10 e P11.
3. THE SYSTEM SHALL listar as pendentes (mais antigas no estoque primeiro), por local, e as peças do boletim a separar, com exportação em CSV.
4. WHEN o Pós-venda marcar uma máquina como aplicada THE SYSTEM SHALL tirá-la dos pendentes e guardar a marcação.
5. IF a posição real não tiver sido importada THEN THE SYSTEM SHALL usar a base de exemplo fictícia e avisar na tela.

## R9. Próximos passos para a POC 🔜
1. WHEN houver base instalada por coorte THE SYSTEM SHALL calcular falhas por 1.000 máquinas.
2. THE SYSTEM SHALL aceitar o código da peça trocada como campo estruturado.
3. THE SYSTEM SHALL oferecer classificação da conclusão via Amazon Bedrock, comparada às regras.
4. WHILE um atendimento de CS estiver aberto THE SYSTEM SHALL exibir o card do DNA da máquina no Salesforce.
6. THE SYSTEM SHALL receber a posição de estoque diretamente do ERP/WMS (integração), sem arquivo manual.
5. WHERE a Cora corporativa for usada THE SYSTEM SHALL exigir login corporativo, acesso ao conector só para o grupo do P&D, `/mcp` protegido por OAuth ou rede privada e iframe autenticado pela chave de integração.
