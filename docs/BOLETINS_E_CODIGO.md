# Boletins e código de melhoria

## Quem insere o quê

| Dado | Quem | Observação |
|---|---|---|
| Boletim (assunto, modelo, data, revisão, peças, série) | **P&D**, uma vez | Pela tela **P&D → Boletins**: sobe o PDF, revisa, registra |
| **Código do projeto da melhoria** (`MEL-G5-RF-0002-R`) | **Gerado pelo sistema** ao registrar | Sai no boletim e na etiqueta do kit; aparece em destaque na lista de boletins cadastrados (P&D e Pós-venda) |
| Consulta dos boletins cadastrados | **Pós-venda** | **Pós-venda → Boletins**: só a lista (sem inserir), com código, peças e série de corte |
| Melhoria aplicada em máquina **em estoque** | **Pós-venda** | **Estoque**: "Marcar aplicada", ou coluna "Melhorias aplicadas" no arquivo do ERP/WMS |
| Código aplicado no chamado | **Técnico (Pós-vendas)**, em lista | Evidência **registrada** (exata) |
| Palavras no texto livre | Técnico, sem querer | Evidência **inferida** (rotulada assim) |

O tipo vem do campo "Número de Série" do boletim: **Indiferente** = kit de
campo (`retrofit_campo`); **uma série** = mudança de fábrica (`corte_serie`).

## Formato do código
`MEL-<G5|G4>-<RF|CS>-<sequência de 4 dígitos>-<letra verificadora>`.
Legível, único e com verificação contra erro de digitação.

## Como o vínculo funciona hoje
1. Se a base tiver a coluna `codigo_melhoria` (futuro campo do Salesforce),
   o chamado conta como "com a melhoria" quando o código é igual: **registrado**.
2. Sem a coluna, vale a busca dos termos no texto livre: **inferido**.

Os termos são sugeridos do assunto e o P&D os ajusta vendo a contagem.

## Limites (ditos com franqueza)
- **A extração atual não traz a coluna** "Código da melhoria": hoje tudo é
  inferido. A importação `.xlsx` já a aceita (opcional) e a tela Dados mostra
  quantos chamados trazem código e quantos são inválidos. Isso é um
  **ponto de melhoria que identificamos** (recomendação para a empresa, fora do
  protótipo): campo de lista no chamado com os códigos do modelo.
- Os códigos de peça do boletim aparecem em poucos chamados; por isso o
  código de melhoria é melhor do que o código de peça.
- Boletim com intervalo de séries: o sistema usa a primeira e avisa.
- O PDF é lido em memória e descartado (limite 5 MB, 20 páginas).
- Premissa a confirmar com o P&D: o código nasce neste sistema ou no
  cadastro oficial de melhorias? Evitar dois cadastros paralelos.
