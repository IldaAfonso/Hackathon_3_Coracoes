# Checklist do dia do evento (14/10/2026)

Manhã no notebook da demo, no Kiro; apresentação às 16h.
A única credencial é a **AWS do kit da Cora** (modelo dela). O MVP não
precisa de nenhuma. Não publicar na internet: o MVP e o `/mcp` não têm
login, a Cora do kit roda com usuário de teste e os dados são reais.

## Manhã (notebook da demo, no Kiro)

- [ ] Perguntar aos organizadores: o kit da Cora roda **local**? Qual a
      porta? A credencial AWS do kit já vem pronta?
- [ ] Avisar os organizadores do bug de conectores do kit (patch em
      `integracoes/cora/cora-fix-uuid-conectores.patch`).
- [ ] Descompactar `dna-maquina-mvp-cora.zip` e colocar a planilha em
      `data/raw/` (ela não vai no zip de propósito).
- [ ] Colar `docs/PROMPT_KIRO.md` no Kiro (patch, Cora, MVP, seed).
- [ ] `make demo-ready` e `make demo-check` até **PRONTO PARA O PALCO**
      (inclui as 11 ferramentas em `/mcp`).
- [ ] Na página Assistente, 3 perguntas de ensaio; cada resposta com o
      selo de ferramenta:
      "O kit de adaptação hidráulica reduziu os retornos?" ·
      "A bandeja de cápsulas funcionou? Monte o parecer técnico." ·
      "O que está crescendo no Luna nos últimos 3 meses?"
- [ ] (Opcional) Resumo da página DNA por IA: `DNA_USE_BEDROCK=1` +
      credencial no terminal do MVP e `make bedrock-check`. Se falhar,
      **não insistir**: o resumo por regras basta.

## Início da tarde

- [ ] Abrir `#/pd/boletins` e passar o fluxo uma vez (PDF de teste, interno).
- [ ] Colocar as **fotos oficiais** dos dois modelos em `frontend/public/assets/modelos/`
      (`passione.webp` e `luna.webp`; ver o `LEIA-ME.md` da pasta) e conferir no DNA.
- [ ] Estoque: se a empresa der a posição real, importar em `#/pd/estoque`; senão,
      dizer que é a base de exemplo fictícia.
- [ ] Abrir a Visão geral (`#/visao-geral`) e conferir "Pontos de melhoria que identificamos".
- [ ] Ensaiar com cronômetro: `docs/ROTEIRO_DEMO.md` (5 min + 3 de perguntas).
      Boletins é opcional: cortar primeiro se estourar o tempo. A pergunta
      à Cora entra no fim; se estourar, corte os Boletins, não a Cora.
- [ ] Logo antes de subir: 1 pergunta de aquecimento à Cora.
- [ ] Deixar as abas na ordem do roteiro; `demo-offline/` aberta à parte.
- [ ] Avisar a organização sobre o telefone real na linha 16165.

## Regras

- Demonstrar na pilha **local** da máquina (sem depender da rede do evento).
- Dizer "inferido" sobre o vínculo do boletim; o exato depende do campo de
  lista no chamado (recomendação, fora do protótipo).
- Dizer "a Cora pergunta, o nosso código responde": os números vêm das
  ferramentas `dna_*`, não do modelo.
- Não dizer que a Cora com o DNA está em produção: é o kit local do
  hackathon, com usuário de teste.
- Se a Cora falhar no palco: mostrar o mesmo número na tela Melhorias ou
  nas respostas prontas por regras.
- `demo-offline/`, a planilha e o boletim interno **não** vão na entrega.
