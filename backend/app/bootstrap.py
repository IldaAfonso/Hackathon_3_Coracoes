"""Ajuste de caminhos que precisa rodar antes dos módulos de análise.

``impact.load_improvements(path=config.IMPROVEMENTS_FILE)`` guarda o
caminho padrão no momento do import. Para o catálogo de melhorias viver
num volume gravável (e sobreviver a reinícios), o caminho é trocado
aqui, antes de ``dna_maquina.impact`` ser importado.
"""

import os
from pathlib import Path

from dna_maquina import config

IMPROVEMENTS_PATH = Path(
    os.getenv("DNA_IMPROVEMENTS_FILE", str(config.IMPROVEMENTS_FILE))
)
config.IMPROVEMENTS_FILE = IMPROVEMENTS_PATH
