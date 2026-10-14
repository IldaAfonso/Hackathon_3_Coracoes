# Roteiro do pitch: 5 minutos

**Quem fala:** Cristiano conduz (engenharia e evidências). Ilza faz a demo ao vivo (slide 6). Karen cuida do passador de slides e do vídeo de backup.

| # | Slide | Tempo | Fala (Cristiano, salvo indicação) |
|---|---|---|---|
| 1 | **"Já consertaram uma vez. Por que vazou de novo?"** | 0:00–0:30 | "Esta é a máquina G5PS000220465809. Entre fevereiro e agosto de 2025 ela abriu **10 chamados**, 6 por vazamento. Os técnicos registraram quatro causas diferentes, e em 6 dos 10 chamados nem há registro do que foi feito. A história dela existe, só que espalhada." |
| 2 | **A engenharia trabalha no escuro** | 0:30–1:00 | "O consumidor fala com o CS, o técnico registra outra coisa e o P&D lança a melhoria. A resposta que mais importa nunca volta para a engenharia: **funcionou?** Hoje, para responder, a Marina extrai, limpa e monta gráfico à mão a cada pergunta." |
| 3 | **DNA da Máquina** | 1:00–1:30 | "Nossa solução junta, por número de série, as duas vozes do chamado e o diretório de melhorias. Descobrimos que a série carrega **ano e semana de fabricação**, então dá para saber de qual versão de engenharia cada máquina é. Com isso temos 20 mil DNAs e 30 mil chamados, e uma nova extração em .xlsx atualiza tudo." |
| 4 | **Caso: bandeja de cápsulas (2022)** | 1:30–2:30 | "O Informativo Técnico de abril de 2022 mudou a bandeja a partir da série G5PS000210224033 para eliminar vazamentos. Comparamos máquinas fabricadas antes e depois, observadas no mesmo período. Antes do corte, **19,6%** dos chamados eram vazamento; depois, **14,2%**. São **‑28%**, com p menor que 0,001. Olhem o degrau na semana do corte e depois um platô estável até 2024, o que mostra que não é efeito da idade. **Funcionou.**" |
| 5 | **E o que não funcionou** | 2:30–3:15 | "Fizemos a mesma pergunta para o kit de adaptação hidráulica. Reparos de vazamento com o kit voltam em 90 dias **na mesma taxa** que sem o kit, 15%. Como engenheiro de confiabilidade, fui ver o modo de falha: **38% dos 'Máquina vazando' são, para o técnico, bico entupido**. É transbordo, não vedação, e o kit ataca a falha errada. Esse é o tipo de evidência que muda a próxima melhoria." |
| 6 | **Demo ao vivo** (Ilza) | 3:15–4:15 | Ilza: abre **DNA da máquina** (a máquina do slide 1, com os selos de melhoria) → **Melhorias** (troca bandeja ↔ adaptação e mostra os vereditos) → **Radar**: "o Luna 'Não extrai' saiu de 7 para mais de 100 chamados por mês em 2026, e ninguém precisou perguntar" → **Assistente (Cora)**: pergunta "o kit de adaptação hidráulica reduziu os retornos?" e mostra o selo da ferramenta: "a Cora, a IA da própria 3corações, pergunta; o nosso código responde". |
| 7 | **Do protótipo à POC** | 4:15–4:45 | "Para virar POC na 3corações: conector Salesforce para a AWS, rodando este mesmo código; **base instalada por série**, para passar de mix para falhas por mil máquinas; a **posição de estoque do ERP**, para atualizar as máquinas paradas antes de vender; **campo estruturado de peça trocada** no formulário do técnico; e o DNA aparecendo para o CS durante a ligação. E o assistente já é a **Cora**: o conector 'DNA da Máquina' entra na Cora corporativa, com login e acesso só do P&D. Construímos tudo no Kiro, com spec, README e premissas documentadas." |
| 8 | **"Funcionou?" Agora a engenharia sabe.** | 4:45–5:00 | "Cada reclamação é uma pista. O DNA da Máquina transforma as pistas em prova. Obrigado." |

## Perguntas prováveis da banca (respostas curtas)
- **"Como sabem que a série tem ano/semana?"** 99,95% dos campos de "semana" ficam entre 01 e 53, e a data de instalação cresce com o "ano". Tratamos como premissa a confirmar com o P&D, e ela está documentada no README.
- **"Sem base instalada, como afirmam redução?"** Medimos o *mix* (a fração dos chamados que são vazamento), que não depende do tamanho da coorte. Com a base instalada, o mesmo código calcula a taxa absoluta. Esse é o passo 1 da POC.
- **"A coorte antiga não falha mais por ser velha?"** Se fosse idade, as coortes de 2021 a 2024 estariam em escada. Elas ficam entre 13% e 16%, sem tendência. O degrau está no corte.
- **"E os dados sujos?"** Nada é apagado. 942 séries ilegíveis (3%), 21% sem conclusão técnica e 164 chamados abertos antes da instalação aparecem no relatório de qualidade.
- **"Por que regras e não IA no texto?"** Para ser auditável pela engenharia. A IA entra onde dá para medir (ML com validação temporal, modos de falha no texto) e a conversa fica com a Cora, que só lê os nossos números.
- **"Por que a Cora e não um chat próprio?"** A empresa já tem a plataforma, com login, permissões, auditoria e o modelo. Entregamos a evidência de campo como ferramenta (MCP), sem outra credencial nem outro lugar para olhar.
- **"E se a Cora inventar?"** Ela não calcula: chama a ferramenta e mostra qual usou; o mesmo número está na tela Melhorias.

## Checklist do dia
- [ ] App aberto na máquina de demo, já na página DNA
- [ ] Kit da Cora no ar (com o patch) e 1 pergunta de aquecimento feita na página Assistente
- [ ] Vídeo de backup da demo no desktop
- [ ] Cronometrar 2 ensaios completos (meta: 4:50)


## Complemento: boletim e código de melhoria (se couber nos 5 minutos)
"O P&D insere o boletim em PDF; o sistema lê, mostra os dados relacionados e
gera o **código da melhoria**. Para o técnico registrar esse código no chamado,
o campo de lista no chamado é um **ponto de melhoria que identificamos**, recomendado à empresa e fora do protótipo. Hoje o
vínculo é inferido por palavras, e dizemos isso na tela."
