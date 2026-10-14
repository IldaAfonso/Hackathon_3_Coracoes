"""Estoque × melhoria: o que atualizar antes de vender.

Fonte de dados nova: a posição de estoque por número de série (exportada
do ERP/WMS em .xlsx ou .csv). Enquanto ninguém importar o arquivo real,
a tela usa a base de EXEMPLO fictícia e avisa isso.

Rotas (prefixo /api/estoque):

* ``GET  /``                     retrato da fonte (o que há e onde)
* ``GET  /melhoria/{id}``        levantamento de uma melhoria
* ``POST /importar``             troca a posição de estoque (arquivo)
* ``POST /aplicacoes``           marca/desmarca "aplicada" numa máquina
* ``GET  /modelo.csv``           modelo do arquivo para o ERP/WMS

Regras e premissas: ``src/dna_maquina/stock.py``.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.common import improvements
from app.serializers import df_json
from app.settings import MAX_UPLOAD_BYTES
from dna_maquina import config
from dna_maquina import stock as stock_core

router = APIRouter(prefix="/estoque", tags=["estoque"])

EXAMPLE_FILE = config.PROJECT_ROOT / "data" / "synthetic" / \
    "estoque_exemplo.csv"
"""Base de exemplo, fictícia (``scripts/make_stock_example.py``)."""

STOCK_FILE = Path(os.getenv(
    "DNA_STOCK_FILE",
    str(config.PROJECT_ROOT / "data" / "estoque" / "estoque.csv")))
"""Última posição importada (no container: volume ``/app/state``)."""

MARKS_FILE = Path(os.getenv(
    "DNA_STOCK_MARKS",
    str(config.PROJECT_ROOT / "data" / "estoque" / "aplicacoes.json")))
"""Marcações "aplicada" feitas na tela (série + código do projeto)."""

MACHINE_COLUMNS = [
    "serie", "local", "data_entrada", "dias_em_estoque", "ano_fab",
    "semana_fab", "situacao", "status", "situacao_label",
]


class _StockCache:
    """Posição de estoque limpa; recarrega quando o arquivo muda."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._key: tuple | None = None
        self._frame: pd.DataFrame | None = None

    def source(self) -> tuple[Path, str]:
        """Arquivo em uso e de onde veio (importada ou exemplo)."""
        if STOCK_FILE.exists():
            return STOCK_FILE, "importada"
        return EXAMPLE_FILE, "exemplo"

    def frame(self) -> pd.DataFrame:
        """A posição limpa (``stock.clean_stock``), em cache."""
        path, _ = self.source()
        key = (str(path), path.stat().st_mtime_ns)
        with self._lock:
            if key != self._key:
                raw = stock_core.read_stock_file(path.read_bytes(),
                                                 path.name)
                self._frame = stock_core.clean_stock(raw)
                self._key = key
            return self._frame

    def updated_at(self) -> str:
        """Data da última atualização do arquivo em uso."""
        path, _ = self.source()
        moment = datetime.fromtimestamp(path.stat().st_mtime)
        return moment.isoformat(timespec="minutes")


cache = _StockCache()
_marks_lock = threading.Lock()


def _read_marks() -> list[dict]:
    """Marcações feitas na tela (lista de {serie, codigo, em})."""
    if not MARKS_FILE.exists():
        return []
    return json.loads(MARKS_FILE.read_text(encoding="utf-8"))


def _mark_pairs() -> set[tuple[str, str]]:
    return {(m["serie"], m["codigo"].upper()) for m in _read_marks()}


def _find(improvement_id: str):
    item = next((i for i in improvements() if i.id == improvement_id), None)
    if item is None:
        raise HTTPException(404, "Melhoria não encontrada.")
    return item


@router.get("")
def overview() -> dict:
    """Retrato da fonte de estoque e as melhorias a levantar."""
    _, origin = cache.source()
    return {
        "fonte": origin,
        "aviso": None if origin == "importada" else (
            "Base de EXEMPLO, fictícia: importe a posição de estoque real "
            "(.xlsx ou .csv) para o levantamento valer."),
        "atualizado_em": cache.updated_at(),
        **stock_core.stock_overview(cache.frame()),
        "melhorias": [
            {"id": i.id, "codigo": i.codigo, "titulo": i.titulo,
             "modelo": i.modelo, "tipo": i.tipo,
             "data_documento": i.data_documento}
            for i in sorted(improvements(), key=lambda i: i.data_documento,
                            reverse=True)
        ],
    }


@router.get("/melhoria/{improvement_id}")
def survey(improvement_id: str) -> dict:
    """Máquinas em estoque que precisam da melhoria antes da venda."""
    item = _find(improvement_id)
    result = stock_core.survey(cache.frame(), item, _mark_pairs())
    machines = result.maquinas.copy()
    machines["data_entrada"] = machines["data_entrada"].dt.strftime(
        "%Y-%m-%d")
    _, origin = cache.source()
    return {
        "fonte": origin,
        "melhoria": {"id": item.id, "codigo": item.codigo,
                     "titulo": item.titulo, "modelo": item.modelo,
                     "tipo": item.tipo, "data_documento": item.data_documento,
                     "pecas": list(item.pecas)},
        "regra": result.regra,
        **stock_core.summarize(result, item),
        "maquinas": df_json(machines[MACHINE_COLUMNS]),
    }


@router.post("/importar")
async def import_stock(
    file: Annotated[UploadFile, File(description=".xlsx ou .csv")],
) -> dict:
    """Troca a posição de estoque pela do arquivo (não mistura)."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Arquivo grande demais.")
    try:
        raw = stock_core.read_stock_file(content, file.filename or "")
        clean = stock_core.clean_stock(raw)
    except stock_core.StockSchemaError as error:
        raise HTTPException(422, str(error)) from error
    except (ValueError, OSError) as error:
        raise HTTPException(422, "Não consegui ler o arquivo de estoque."
                            ) from error
    if clean.empty:
        raise HTTPException(422, "O arquivo não tem nenhuma máquina.")
    STOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    STOCK_FILE.write_text(stock_core.to_csv_text(clean), encoding="utf-8")
    return {"fonte": "importada",
            **stock_core.stock_overview(cache.frame())}


class MarkIn(BaseModel):
    """Máquina que recebeu (ou não) a melhoria no estoque."""

    serie: str = Field(min_length=6, max_length=40)
    codigo: str = Field(pattern=r"^MEL-[A-Z0-9]+-[A-Z]{2}-\d{4}-[A-Z]$")
    aplicada: bool = True


@router.post("/aplicacoes")
def mark_applied(body: MarkIn) -> dict:
    """Marca a melhoria como aplicada (ou desfaz) numa máquina.

    Grava série, código do projeto e o momento; a próxima consulta já
    tira a máquina da lista de pendentes.
    """
    serial = body.serie.strip().upper()
    code = body.codigo.upper()
    if serial not in set(cache.frame()["serie"]):
        raise HTTPException(404, "Série não está na posição de estoque.")
    with _marks_lock:
        marks = [m for m in _read_marks()
                 if (m["serie"], m["codigo"]) != (serial, code)]
        if body.aplicada:
            marks.append({"serie": serial, "codigo": code,
                          "em": datetime.now().isoformat(
                              timespec="seconds")})
        MARKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        MARKS_FILE.write_text(json.dumps(marks, ensure_ascii=False,
                                         indent=1), encoding="utf-8")
    return {"serie": serial, "codigo": code, "aplicada": body.aplicada}


@router.get("/modelo.csv")
def template() -> Response:
    """Modelo do arquivo de estoque, para exportar do ERP/WMS."""
    return Response(
        stock_core.TEMPLATE_CSV, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":
                 'attachment; filename="modelo_estoque.csv"'})
