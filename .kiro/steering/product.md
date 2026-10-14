---
inclusion: always
---

# Produto: DNA da Máquina

## Contexto
Desafio 01 da TRES® (Grupo 3corações) no Hackathon Cafeína Week 2026, realizado na FIAP em 13 e 14/out.
Máquinas de café em cápsula **G5 Passione** e **G4 Luna**. Três times cuidam de cada máquina:
Customer Success (ouve o consumidor), Pós-vendas (repara) e P&D (melhora o projeto). Os registros
de cada um ficam soltos no Salesforce e não existe histórico por máquina.

## Pergunta-desafio
Como criar um histórico confiável de cada máquina, identificar padrões e apoiar decisões de
engenharia com evidências reais de campo?

## Usuária principal
**Marina, engenheira de produto do P&D.** "Eu sei o que mudei na máquina. Não sei se funcionou."
Para ela, sucesso é abrir o histórico de um modelo e ver, com dados confiáveis, se as ocorrências
caíram depois de cada melhoria, e decidir com isso a próxima melhoria.

Personas secundárias:
- **Carlos (técnico):** consultar o histórico da máquina antes do atendimento.
- **Rafael (CS):** saber, durante a ligação, se a máquina já teve o mesmo problema.
- **Juliana (consumidora):** o problema não voltar.
- O foco é exclusivamente o P&D: CS e pós-vendas entram como fonte de dados e como executores das decisões de engenharia.

## Narrativa do produto (acordada pela equipe)
1. **O histórico de hoje não atende:** cada time registra num lugar e nenhum recebe a história dos outros.
   A Visão geral (`#/visao-geral`) mostra isso com números reais (chamados sem conclusão do técnico, máquinas que voltam em 90 dias,
   máquinas crônicas, séries ilegíveis, boletins fora do diretório).
2. **O número de série é a chave que liga os três times:** Customer Success (ouve), Pós-vendas (resolve) e P&D (inova).
   Toda análise parte da série.
3. **O que implantar** para o histórico passar a servir: validar a série na abertura do chamado, campo estruturado de
   peça trocada, ligar chamado e laudo, cadastrar cada melhoria com a série de corte.
4. O produto responde à pergunta que nunca voltava para a engenharia: *a melhoria funcionou?*

## Foco (dores priorizadas pelo desafio)
- Dor 04: correlação melhoria × impacto
- Dor 06: dados lentos de tratar
- Dor 07: sem histórico por máquina
- Diferencial: importar nova base .xlsx e atualizar as análises

## Entregáveis do hackathon
1. Protótipo funcional rodando com os dados reais fornecidos
2. Um caso de ponta a ponta: melhoria do G5 Passione com antes e depois (**bandeja de cápsulas**)
3. Pitch de 5 minutos
4. Código, README e especificações (premissas sobre os dados)

## Critérios de avaliação
Aderência 25% · Impacto 25% · Criatividade 20% · Viabilidade 20% · Protótipo e comunicação 10%

## Princípios
- Toda análise explica as próprias premissas na tela. A banca precisa confiar no número.
- Dados imperfeitos são marcados e não apagados.
- Linguagem de negócio na interface ("Funcionou", "Voltou em 90 dias"); a estatística fica no detalhe.
- Interface e textos em português do Brasil.
- **Dado pessoal nunca sai pela API.** Texto digitado por pessoas passa por `backend/app/privacy.py` (a base real tem
  um telefone escrito à mão pelo técnico). Nomes e endereços por extenso não são detectados: dizer isso, não esconder.
- **Os dados reais do desafio não entram em imagem, repositório nem pacote de entrega** (regulamento, Art. 37).
- Honestidade estatística: amostra pequena vira "Amostra insuficiente"; associação não é causa; o indicador é de *mix*.
- Marcas de terceiros (Mercafé, 3corações, TRES) só com atribuição (regulamento, Art. 32); o protótipo não é produto oficial.

## Áreas: P&D e Pós-venda
A entrada (`#/`) separa os times. **P&D:** Melhorias, Boletins (inserir + cadastrados, sempre com o código do
projeto da melhoria), Estoque, DNA da Máquina, Riscos. **Pós-venda:** DNA da Máquina, Boletins (só a lista),
Estoque (marcar aplicada), Riscos. No DNA, o modelo aparece com nome e foto. Toda lista abre e fecha.

## Estoque × melhoria
Ao implantar uma melhoria, levantar as máquinas ainda em estoque que saíram da fábrica sem ela, para atualizar
antes da venda. Fonte nova: posição de estoque por série (ERP/WMS). Até a posição real chegar, a tela usa base de
EXEMPLO fictícia e avisa. Premissas P10/P11 do README.

## Assistente = Cora (IA corporativa)
A conversa com IA é da **Cora**, a plataforma de IA do Grupo 3corações. O produto entrega a evidência de campo
como **ferramentas MCP** (`dna_*`, em `/mcp`) e incorpora a Cora na página Assistente, enviando o contexto da tela
(série em foco, melhorias). O MVP não chama modelo de linguagem para conversar. Frase do produto: "a Cora pergunta,
o nosso código responde". Detalhes: `docs/CORA.md`.

## Boletins e código de melhoria
O P&D insere o boletim em PDF (tela Boletins); o sistema gera o código `MEL-<modelo>-<RF|CS>-<seq>-<letra>`. O vínculo é registrado quando o chamado traz `codigo_melhoria`; senão, inferido por palavras. Ver `docs/BOLETINS_E_CODIGO.md`.
