"""Conteúdo editorial da narrativa: o que falta hoje e o que implantar.

Fica separado das rotas porque é texto de produto, não lógica: quem
revisa o discurso (P&D, pitch) edita aqui sem tocar na API.
"""

from __future__ import annotations

IMPROVEMENTS_TO_DEPLOY: tuple[dict, ...] = (
    {
        "prioridade": 1,
        "titulo": "Validar o número de série na abertura do chamado",
        "porque": "A série é a chave que liga os três times. Hoje parte "
        "dela chega ilegível.",
        "dono": "Customer Success",
        "tipo": "processo + sistema",
        "evidencia": "serie_invalida",
        "no_prototipo": "Série ilegível fica marcada e fora do DNA; a "
        "tela Dados mostra quantos chamados são afetados.",
    },
    {
        "prioridade": 2,
        "titulo": "Campo de lista com o código da melhoria (e a peça "
        "trocada) no chamado",
        "porque": "O kit só aparece no texto livre e o código de peça do "
        "boletim quase nunca é citado: sem um campo estruturado o efeito "
        "de um boletim só pode ser inferido por palavras.",
        "dono": "Pós-vendas + TI",
        "tipo": "sistema",
        "evidencia": "pecas_citadas",
        "no_prototipo": "A tela Boletins gera o código da melhoria e a "
        "importação já aceita a coluna; sem ela o vínculo é marcado "
        "como inferido.",
    },
    {
        "prioridade": 3,
        "titulo": "Ligar o chamado ao registro técnico do mesmo caso",
        "porque": "CS e técnico descrevem o mesmo chamado de jeitos "
        "diferentes e a ligação não é obrigatória.",
        "dono": "CS + Pós-vendas",
        "tipo": "processo",
        "evidencia": "sem_conclusao",
        "no_prototipo": "A tela Duas vozes põe sintoma e causa lado a "
        "lado e mostra quando divergem.",
    },
    {
        "prioridade": 4,
        "titulo": "Cadastrar cada melhoria com a série a partir da qual vale",
        "porque": "Permite comparar antes e depois por coorte de "
        "fabricação, sem adivinhar.",
        "dono": "P&D",
        "tipo": "processo",
        "evidencia": "boletins",
        "no_prototipo": "As telas Boletins e Melhorias cadastram a "
        "melhoria e já medem o antes × depois com intervalo de confiança.",
    },
    {
        "prioridade": 5,
        "titulo": "DNA da máquina no atendimento e no app do técnico",
        "porque": "Quem atende precisa ver o histórico da série antes "
        "de agir.",
        "dono": "TI",
        "tipo": "sistema",
        "evidencia": "reincidencia",
        "no_prototipo": "A tela DNA da máquina reúne a história inteira "
        "de uma série; a API pode ser consumida pelo Salesforce.",
    },
)
