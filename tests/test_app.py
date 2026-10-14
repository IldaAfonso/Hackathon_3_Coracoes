"""
Teste de fumaça do app — abre o Streamlit e navega pelas 9 telas.

É lento (1–3 min: monta cache e treina o modelo se preciso), por isso só
roda quando pedido::

    RUN_APP_TESTS=1 pytest tests/test_app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
PAGES = ["Visão geral", "DNA da máquina", "Melhoria × impacto",
         "Duas vozes", "Radar", "Risco de retorno",
         "Padrões no texto (IA)", "Assistente (IA)", "Importar base"]

pytestmark = pytest.mark.skipif(os.getenv("RUN_APP_TESTS") != "1",
                                reason="lento; use RUN_APP_TESTS=1")


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(page):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(APP), default_timeout=300)
    app.run()
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, [e.value for e in app.exception]
