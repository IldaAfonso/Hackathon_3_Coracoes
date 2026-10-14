# Validação do protótipo com a base sintética

Uma base **sintética** (sem dado real nem pessoal) tem o mesmo layout da
extração do Salesforce, o catálogo de melhorias e dois boletins em PDF.
Nela, os efeitos são **plantados**; se o protótipo os recupera, o pipeline,
a estatística e a API estão corretos. A base real continua sendo a da
demonstração; esta serve para validar e para quem não pode ter a planilha.

| Arquivo (`data/synthetic/`) | Conteúdo |
|---|---|
| `base_sintetica.xlsx` | Base completa: 9.940 chamados, 6.938 máquinas, com a coluna "Código da melhoria" |
| `inicial/base_inicial.xlsx` | Início da pilha sintética (4.673 chamados) |
| `complemento/base_complemento.xlsx` | O que se importa na tela (repete 3 meses de propósito) |
| `melhorias_sintetica.json` | 2 melhorias, usadas pelos testes |
| `melhorias_vazia.json` | Catálogo vazio: a pilha sintética começa sem melhorias |
| `boletim_sintetico_kit.pdf` | Série "Indiferente" (kit de campo) |
| `boletim_sintetico_serie.pdf` | Com série (mudança de fábrica) |
| `ground_truth.json` | A verdade plantada |

Gerada por `scripts/make_synthetic_base.py` (semente fixa: sempre igual).

## O que foi plantado e o que o protótipo deve achar

| Plantado | Esperado | Resultado medido |
|---|---|---|
| Bandeja: vazamento de 32% para 16% dos chamados | "Funcionou" | **Funcionou**, p ≈ 2·10⁻⁵⁹, queda relativa de 51% |
| Kit: retorno em 90 dias igual com e sem o kit | "Sem efeito mensurável" | **Sem efeito mensurável**, p = 0,76 |
| Código no atendimento com kit | vínculo "registrado" | **registrado**, 387 chamados com código |
| Sem a coluna de código | cai nas palavras ("inferido") | coberto por teste |
| 5% de séries ilegíveis | marcadas na qualidade | entre 3% e 7% |
| 25 máquinas crônicas (6 chamados) | achar ao menos 80% | coberto por teste |
| 1 telefone falso no texto | contado e mascarado | exatamente 1 |
| Boletim "Indiferente" / com série | `retrofit_campo` / `corte_serie` | coberto por teste |

## Demonstração ponta a ponta, passo a passo, na tela

```bash
make sintetico       # http://localhost:8090 (isolada da base real)
```

A pilha sintética começa com **a base inicial (4.673 chamados) e nenhuma
melhoria**. Faça na tela, nesta ordem:

1. **Visão geral** (`#/visao-geral`): veja o diagnóstico da base parcial.
   **P&D → Melhorias** diz que ainda não há nenhuma.
2. **Importar base de chamados** (link na entrada, `#/dados`): envie `data/synthetic/complemento/base_complemento.xlsx`.
   A base passa a 9.940 chamados; os 3 meses repetidos são atualizados, não
   duplicados.
3. **P&D → Boletins:** envie `boletim_sintetico_kit.pdf` (série "Indiferente").
   Sai **kit de campo**. Clique em "Ver dados relacionados" (387 chamados,
   *inferido*) e **Registrar**. O código gerado é `MEL-G5-RF-0001-B`.
4. **P&D → Boletins:** envie `boletim_sintetico_serie.pdf` (com série). Sai
   **mudança de fábrica**, série `G5PS000210224033`. Registrar gera
   `MEL-G5-CS-0001-Y`.
5. **P&D → Melhorias:** a bandeja dá **Funcionou** e o kit, **Sem efeito
   mensurável**, com o selo **registrado** (os chamados da base já trazem o
   código gerado no passo 3).
6. **Dados:** a qualidade mostra os chamados com código de melhoria.
7. **Pós-venda → Boletins:** os dois boletins aparecem só como lista, cada um
   com o código do projeto da melhoria.
8. **P&D → Estoque:** o levantamento usa a base de estoque de exemplo
   (fictícia, independente da base sintética de chamados) e mostra as
   máquinas a atualizar para cada melhoria registrada.

A mesma sequência roda sozinha com `make sintetico-e2e` (mostra `TUDO OK`).

## Como rodar

```bash
make test        # inclui tests/test_synthetic_validation.py
make sintetico   # sobe a pilha isolada em http://localhost:8090
make sintetico-e2e   # a demonstração acima, automática
make sintetico-down
```

`make sintetico` usa projeto e volumes próprios: **não mistura** com a base
real (`make up`, porta 8080). 

## Limites

- Sintético prova que o **método** acerta o que foi plantado. Não prova que
  o efeito exista nos dados reais.
- Os efeitos plantados são fortes de propósito; na base real a bandeja dá
  −28%, não −51%.
- Nunca importar `base_sintetica.xlsx` na pilha real (Dados > Importar):
  misturaria dado de teste com dado real. Use `make sintetico`.
