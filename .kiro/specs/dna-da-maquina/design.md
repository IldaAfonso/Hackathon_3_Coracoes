# Design técnico: DNA da Máquina

## Visão geral
```
 Salesforce (.xlsx)          Diretório de melhorias (melhorias.json)
        │                                  │
        ▼                                  │
 ingest.clean_complaints  ── flags dq_*    │
        ▼                                  │
 serial.decode_serial_column (ano/semana/chave)
        ▼                                  │
 taxonomy.classify_repairs (componentes, causa, kits)
        ▼                                  │
 analytics.add_voice_agreement             │
        ▼                                  │
 history.add_machine_sequence (DNA)        │
        ▼                                  ▼
 data/processed/chamados.parquet ──► impact.evaluate / analytics.radar / history.*
        ▼
 backend FastAPI (rotas por domínio, cache em memória, máscara de privacidade)
        ▼
 frontend estático (nginx): telas que só conversam com /api
        │                                        ▲
        └─ página Assistente: iframe <Cora>/embed │ /mcp (ferramentas dna_*)
                      Cora (chat + modelo) ───────┘
```

## Modelo de dados (base enriquecida, 1 linha por chamado)
| Coluna | Origem | Uso |
|---|---|---|
| case_id | Número do caso | Chave de deduplicação |
| sintoma_cs | Detalhamento CS | Voz do consumidor |
| laudo, motivo, conclusao | Pós-vendas | Voz do técnico |
| serie, valida, formato | serial.py | Chave do DNA |
| ano_fab, semana_fab, chave_ordem | serial.py | Coortes e corte de melhoria |
| componentes, causa_principal, causa_label, familia_tecnica | taxonomy.py | Leitura da causa |
| fez_adaptacao_hidraulica, trocou_oring_anel, mexeu_bandeja | taxonomy.py | Evidência dos kits |
| vozes_concordam | analytics.py | Duas vozes |
| ordem_na_maquina, dias_desde_anterior, reincidente, problema_voltou | history.py | DNA e efetividade do reparo |
| dq_* | ingest.py | Qualidade de dados |

## Decisões de projeto
1. **Coorte de fabricação em vez de calendário.** As melhorias são de 2022 e os chamados de 2025–26, então comparar datas de abertura não isola o efeito. Coortes observadas na mesma janela de calendário controlam sazonalidade e mudanças de processo.
2. **Indicador de mix na ausência de denominador.** Sem base instalada, a taxa absoluta é desconhecida. A participação do sintoma nos chamados da coorte é robusta a coortes de tamanhos diferentes. Viés conhecido: a coorte "Antes" é mais velha, o que tende a subestimar o ganho; a faixa estável de 13–16% nas coortes de 2021 a 2024 mostra que a idade não explica a queda.
3. **Kit de campo = retorno em 90 dias.** Como o kit vale para qualquer série, a pergunta certa é se o reparo com kit "segura" a máquina. Censura à direita: os últimos 90 dias da base ficam fora.
4. **Regras antes de LLM.** Auditáveis e explicáveis para a engenharia. O Bedrock entra na POC com as regras como baseline.
5. **Estatística sem SciPy.** Wilson e teste z implementados em `impact.py`, com menos dependências e fórmulas visíveis.
6. **Backend e frontend separados.** A análise vira uma API que o Salesforce ou o app do técnico podem consumir; a interface troca sem tocar nas análises. O Streamlit original ficou como alternativa (`make legacy`).
7. **Frontend sem build.** HTML, CSS e módulos ES servidos por nginx: menos peças para quebrar no evento, proxy `/api` na mesma origem (sem CORS), CSP restrita a recursos próprios.
8. **Privacidade na saída.** A base real tem um telefone digitado à mão; toda string livre passa pela máscara antes de sair. Regex não pega nomes nem endereços: limite documentado.
9. **Dados do desafio fora de imagem e repositório.** A planilha é montada somente leitura em execução.
10. **Grupo vazio não é erro.** Comparação antes × depois sem um dos grupos devolve p-valor ausente e o veredito "Amostra insuficiente" (bug achado na revisão e corrigido em `impact._compare_groups`).
11. **Assistente pela Cora, via MCP.** A empresa já tem a plataforma de IA (login, RBAC, auditoria, modelo). O MVP publica as análises como ferramentas (`backend/app/mcp_server.py`, transporte streamable HTTP sem estado, gerenciador de sessões recriado a cada partida) e incorpora a Cora no iframe com o contexto da tela. Não há segundo chat nem segunda credencial; sem a Cora, o plano B é por regras.
12. **Áreas na URL.** A entrada separa P&D e Pós-venda; a área vai no hash (`#/pd/...`) e define o menu (`areas.js`, puro e testado). A mesma página serve às duas áreas e muda só o que cada time pode fazer (ex.: Boletins só lista no Pós-venda).
13. **Estoque como fonte própria.** A posição de estoque por série é importada à parte (não mistura com a base de chamados) e cruzada com o catálogo de melhorias pela chave `AAAASSNNNNN` da série (P10/P11). Marcações "aplicada" ficam num JSON no volume de estado. Até a posição real chegar, uma base de exemplo fictícia, avisada na tela.

## Tratamento de erros
- `SchemaError` na importação: mensagem com as colunas faltantes; a base atual não muda.
- Datas ilegíveis viram NaT e chamados sem data de abertura são descartados (contados no log).
- Série inválida: o chamado entra nas contagens gerais, mas não no DNA nem nas coortes.

## Estratégia de testes
- Unitários por premissa: decodificação de série, normalização, prioridade da taxonomia, regras de concordância, Wilson e teste z, merge sem duplicar, reincidência de 90 dias.
- Smoke test da interface antiga: `streamlit.testing.v1.AppTest` (opcional, `RUN_APP_TESTS=1`).
- API: `tests/test_api.py` e `tests/test_privacy.py` sobre uma amostra isolada do disco (modelos, cache e catálogo vão para pasta temporária).
- `make smoke`: todas as rotas na base real, incluindo a conferência de que o telefone real não vaza.
- Frontend: `node --test` nas funções puras (inclui a ponte com a Cora); ESLint.
- MCP: `tests/test_mcp.py` (catálogo, protocolo HTTP, privacidade, erros, host recusado) e `make mcp-check` no ambiente; integração testada com o kit real da Cora (docs/CORA.md).
