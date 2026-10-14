# Roteiro da demonstração (5 minutos + 3 de perguntas)

Para quem vai apresentar. Todos os números abaixo foram lidos da base real
em 13/10/2026 e são conferidos pelo `make demo-check`.

## Antes de subir ao palco (10 minutos antes)

1. Kit da Cora no ar (com o patch, ver `docs/CORA.md`), depois
   `export DNA_CORA_URL=http://localhost:<porta>`, `make demo-ready` e
   `make demo-check`. Só entre quando aparecer **PRONTO PARA O PALCO**. Se
   um número mudou (nova importação), o pré-voo avisa; releia o roteiro.
   Faça **uma pergunta de aquecimento** à Cora (a 1ª chamada a
   `dna_modos_de_falha` treina o modelo de texto e leva alguns segundos).
2. Abra `http://localhost:8080` em tela cheia, zoom 100%, e deixe estas abas
   prontas, na ordem:
   `#/visao-geral` · `#/grafo/G5PS000220465809` · `#/grafo/G5PS000220465809/depois` · `#/pd/dna/G5PS000220465809` ·
   `#/pd/melhorias/G5-BANDEJA-2022` · `#/pd/melhorias/G5-ADAPT-HIDR-2022` · `#/pd/estoque/G5-ADAPT-HIDR-2022` ·
   `#/pd/boletins` · `#/vozes` · `#/radar` · `#/assistente/G5PS000220465809` · `#/` (entrada, para o fechamento)
   A entrada (`#/`) mostra as duas áreas, **P&D** e **Pós-venda**, cada uma com o seu menu. As telas do
   roteiro que não estão nos menus (visão geral, grafo, duas vozes, radar, Cora) abrem pelos links acima.
3. Deixe `demo-offline/` aberta numa janela à parte (plano B, abaixo).
4. As telas de análise **não dependem de internet**: fonte, gráficos e logos
   vêm do próprio servidor. **Só a conversa com a Cora** precisa de rede até o
   Bedrock (modelo dela); se cair, use as respostas prontas por regras na
   mesma página.

## O fio da história

> Três times cuidam da mesma máquina e cada um registra num lugar. **O
> histórico de hoje não atende.** A chave que já existe nos três é o **número
> de série**. Ligando por ela, o P&D finalmente responde: *a melhoria
> funcionou?*

Frase da Marina (P&D), do briefing: *"Eu sei o que mudei na máquina. Não sei
se funcionou."* O produto responde a essa frase.

## Tempo e o que mostrar

| Tempo | Tela | O que dizer | Número |
|---|---|---|---|
| 0:00 a 0:40 | **Visão geral** `#/visao-geral` (topo e os três times) | "Customer Success ouve, Pós-vendas resolve, P&D inova. Cada um registra num lugar e **hoje nenhum recebe a história dos outros**. A chave comum é o número de série." | 30.481 chamados, 20.379 máquinas com série válida |
| 0:40 a 1:30 | **Visão geral**, descer até "Por que o histórico de hoje não atende" | Aponte 4 cartões, só 4. | **20,8%** dos chamados sem conclusão do técnico · **22,1%** são a mesma máquina voltando em 90 dias · **2.019** máquinas com 3+ chamados · **29** boletins citados em campo fora do diretório de melhorias |
| 1:30 a 2:45 | **Grafo** `#/grafo/G5PS000220465809` e depois **DNA da Máquina** `#/pd/dna/G5PS000220465809` (aponte o **modelo com a foto** no topo) | "É a Juliana: *já consertaram, por que vazou de novo?* Esta máquina abriu **10 chamados e 8 voltaram**. O consumidor diz 'vazando' toda vez, e **cada técnico registrou uma causa diferente**. Quem chega não sabe o que já foi feito. Aqui está a história inteira, ligada pela série." Comece pelo **grafo**: "a série é o centro; à esquerda o que o consumidor disse, à direita o que cada técnico achou, e as setas vermelhas são o chamado que voltou". Clique em **Depois das melhorias** (`#/grafo/G5PS000220465809/depois`): é uma **ilustração** (diga isso) do mesmo histórico real com os pontos de melhoria funcionando: série validada, laudo ligado a cada chamado e o P&D recebendo a resposta de cada melhoria (bandeja: funcionou; kit: sem efeito). Depois, no DNA, mostre: as duas vozes lado a lado, "Voltou em até 90 dias", "de fábrica: bandeja", confiabilidade e risco | 10 chamados, 8 voltas, confiabilidade 79/100 |
| 2:45 a 3:45 | **Melhorias** (P&D): bandeja, depois kit; botão **Levantar máquinas em estoque** | **Bandeja:** "Funcionou." **Kit hidráulico:** "Aqui o dado diz *não*, e dizemos isso." **Estoque (10 s):** "E quando o P&D implanta uma melhoria, o sistema levanta as máquinas ainda em estoque que saíram da fábrica sem ela, para atualizar **antes de vender**. Aqui com uma base de estoque de exemplo, fictícia: a posição real vem do ERP." | Bandeja **19,6% → 14,2%** (−28%, p < 0,001; 1.334 chamados antes, 8.054 depois). Kit **15,4% × 15,1%**, p = 0,91: "Sem efeito mensurável" |
| 3:45 a 4:10 | **Duas vozes**, depois **Radar** | "O CS registra o sintoma; o técnico, a causa. Em 'Botões piscando' as vozes só concordam **11%** das vezes: a causa mais comum é o contador volumétrico, não a elétrica. E o radar achou sozinho o que ninguém perguntou." | Luna "Não extrai": **7 por mês** em jan/2025 → **157** em jul/2026 |
| 4:10 a 4:30 | **Assistente (Cora)** `#/assistente/G5PS000220465809` | "E a Marina não precisa de nós para perguntar: a **Cora**, a IA da própria 3corações, usa as nossas análises como ferramentas." Digite: *"O kit de adaptação hidráulica reduziu os retornos?"* e aponte o selo **1 ferramenta**: "o número vem do nosso código, não do modelo." | 15,4% → 15,1%, p = 0,91 |
| (opcional) | **Boletins** `#/pd/boletins` (se houver tempo) | "O P&D sobe o boletim em PDF, o sistema lê tudo e gera o **código do projeto da melhoria**; o Pós-venda vê a lista com o código. O técnico escolhe esse código no chamado e o vínculo deixa de ser adivinhado." Hoje o vínculo é **inferido** por palavras. | Código `MEL-G5-RF-0002-R` |
| 4:30 a 5:00 | **Visão geral**, "Pontos de melhoria que identificamos" (feche na **entrada** `#/`: "cada time com o seu menu") (cada um com evidência e o que o protótipo já mostra) | "Para o histórico passar a servir: **validar a série na abertura do chamado**, **campo estruturado de peça trocada**, ligar chamado e laudo, e **cadastrar cada melhoria com a série de corte**. Para virar POC: Salesforce → S3, base instalada, e o DNA dentro do atendimento." | 5 prioridades |

## Frases que você NÃO deve dizer

- "O kit não funciona." → Diga **"não há efeito mensurável nestes dados"**. Pode haver
  outra causa (cerca de 38% dos "Máquina vazando" têm bico entupido, que o kit
  não ataca), mas isso é **hipótese**, não resultado.
- "A bandeja causou a queda." → É associação por coorte de fabricação. A
  coorte "antes" é mais velha, o que tende a **subestimar** o ganho.
- "Taxa de falha por máquina." → O indicador é de **mix** (parcela dos
  chamados). Falta a base instalada para a taxa por 1.000 máquinas.
- "Este é o estoque da empresa." → É uma **base de exemplo fictícia** (a tela avisa
  em vermelho). A posição real vem do ERP/WMS, pelo botão Importar.
- "A Cora calcula / a IA descobriu o número." → A Cora **chama** as nossas
  ferramentas; os números são do código, testados. Diga "a Cora pergunta, o
  nosso código responde".
- "A Cora já está em produção com o DNA." → É o **kit do hackathon**, local,
  com usuário de teste. Em produção, falta login corporativo, acesso só do
  P&D e o `/mcp` protegido.
- "Usamos Bedrock no MVP." → O MVP não chama modelo para conversar; o
  Bedrock é da Cora. O resumo opcional da página DNA só cite se o
  `bedrock_check` tiver dado ok.
- "Está implantado na AWS." → Não está. Os containers estão prontos.

## Perguntas prováveis da banca (3 minutos)

| Pergunta | Resposta curta |
|---|---|
| Os dados são reais? | Reais e anonimizados, fornecidos pelo desafio. Usados só no evento; **a planilha nunca entra na imagem do container**. |
| E dado pessoal? | A API mascara telefone, e-mail, CPF e CEP. Achamos **um telefone real** num texto de técnico e já o bloqueamos. Nomes por extenso não são detectados; é um limite conhecido. |
| Como sabem que o −28% não é acaso? | Teste de duas proporções: p ≈ 3·10⁻⁷, com intervalo de confiança de 95%. E amostra pequena vira "insuficiente", não conclusão. |
| Por que o kit não funcionou? | Os dados não mostram efeito. Hipótese: boa parte do vazamento é bico entupido. Para confirmar, falta um campo estruturado de peça trocada. |
| Quem usa e para quê? | Marina (P&D) prova o impacto; Carlos (técnico) consulta a máquina antes de ir; Rafael (CS) vê, na ligação, se já teve o mesmo problema. |
| O que falta para virar POC? | Conector Salesforce → S3; base instalada por série; campo de peça trocada; o conector "DNA da Máquina" na Cora corporativa (login Entra ID, só o grupo do P&D, `/mcp` protegido); deploy privado na AWS. |
| E se a série vier errada? | 3,1% dos chamados têm série ilegível; ficam marcados e não entram no DNA. Por isso a primeira melhoria é **validar a série na abertura do chamado**. |
| Como liga o boletim aos chamados? | O P&D registra o boletim e o sistema gera um código. Um campo de lista com esse código no chamado é um **ponto de melhoria que identificamos** (aparece em "Pontos de melhoria", na Visão geral); hoje o vínculo é inferido por palavras e a tela diz isso. |
| É difícil de integrar? | O backend é uma API; o Salesforce e o app do técnico consomem as mesmas rotas que a tela usa. E a integração com a IA da empresa já está feita: a Cora usa as análises por **MCP**, com o controle de acesso e a auditoria dela. |
| Por que a Cora e não um chat próprio? | A empresa já tem a plataforma, com login, permissões, auditoria e o modelo. Nós entregamos o que falta: **evidência de campo como ferramenta**. Um chat a mais seria outra credencial e outro lugar para a engenharia olhar. |
| E se a Cora inventar um número? | Ela não calcula: chama `dna_*` e recebe o JSON. A resposta mostra a ferramenta usada, e a mesma análise está na tela Melhorias para conferir. |
| O ML presta? | Risco de retorno: AUC 0,70 contra 0,64 da regra simples; nos 10% de maior risco, 65,5% voltam (média: 24,9%). É modesto e dito como modesto. |

## Plano B (se algo falhar no palco)

| Problema | O que fazer |
|---|---|
| A página não carrega | `make up`; espere 15 s; recarregue. Se persistir, plano B abaixo. |
| Porta 8080 ocupada | Pare o que a usa, ou mude `8080:8080` no `compose.yaml`. |
| Container caiu | `make logs` mostra o motivo; `make up` sobe de novo, sem perder a base. |
| Sem internet | As análises seguem (tudo é local). A Cora não responde: role a página Assistente até **Respostas prontas (sem IA)**. |
| A Cora responde sem o selo de ferramenta | Não insista no palco: mostre o mesmo número na tela **Melhorias**. Depois, ver `docs/CORA.md` (patch e seed). |
| Tudo falhou | Abra as 9 imagens de `demo-offline/` na ordem (01 a 09) e conte a mesma história; avise que é a captura de tela. |

`demo-offline/` tem **dados reais** (trechos de chamados). Use só no evento e
**não a inclua no pacote de entrega** (o `dna-maquina-mvp.zip` já a exclui).

## Antes de entregar

- Abrir `#/pd/boletins` com o boletim de teste (PDF interno: **só para teste local**).
- Pacote **sem** `data/raw`, **sem** `demo-offline/` e **sem** o boletim interno.
- Avisar a organização sobre o telefone real na linha 16165 da planilha.
- Confirmar com o P&D a decodificação da série (premissa P1) e se o diretório
  oficial de melhorias tem mais itens que os 3 cadastrados.
