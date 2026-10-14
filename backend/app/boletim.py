"""Leitura de boletins técnicos em PDF e geração do código de melhoria.

O PDF é lido em memória e descartado: nada dele é gravado. A leitura só
*sugere* campos; quem confirma é o P&D, na tela.
"""

from __future__ import annotations

import io
import re
from datetime import datetime

from dna_maquina.serial import parse_serial
from dna_maquina.taxonomy import strip_accents

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGES = 20
MODELS = {"passione": "Passione", "luna": "Luna"}
TYPE_CODE = {"retrofit_campo": "RF", "corte_serie": "CS"}
MODEL_CODE = {"Passione": "G5", "Luna": "G4"}
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"

_DATE = r"(\d{2}/\d{2}/\d{4})"
_UPPER = r"(?!\d{7,}\b)[A-ZÀ-Ý0-9“”\"'/.,+-]+(?=\s|$)"
_PART = re.compile(
    r"\b(\d{7})\s*-\s*(" + _UPPER + r"(?:\s" + _UPPER + r")*)"
)
_STOPWORDS = {"de", "da", "do", "para", "com", "uma", "das", "dos", "na",
              "no", "em", "por", "que"}


class PdfError(ValueError):
    """PDF inválido, grande demais ou ilegível."""


def extract_text(content: bytes) -> str:
    """Texto do PDF numa linha só (espaços normalizados)."""
    if len(content) > MAX_BYTES:
        raise PdfError("Arquivo acima de 5 MB.")
    if not content.startswith(b"%PDF"):
        raise PdfError("O arquivo não é um PDF.")
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
        if len(reader.pages) > MAX_PAGES:
            raise PdfError(f"PDF com mais de {MAX_PAGES} páginas.")
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfError:
        raise
    except Exception as error:  # noqa: BLE001 — PDF malformado
        raise PdfError("Não foi possível ler o PDF.") from error
    return re.sub(r"\s+", " ", " ".join(pages)).strip()


def _iso(date_br: str | None) -> str | None:
    if not date_br:
        return None
    try:
        return datetime.strptime(date_br, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def parse_bulletin(text: str) -> dict:
    """Extrai modelo, série, data, assunto, revisão e peças do texto.

    O tipo vem do campo "Número de Série": "Indiferente" é kit de campo
    (``retrofit_campo``); uma série é mudança de fábrica
    (``corte_serie``). Intervalos de série pedem revisão manual.
    """
    flat = re.sub(r"\s+", " ", text)
    folded = strip_accents(flat).lower()
    model = next((name for key, name in MODELS.items() if key in folded),
                 None)
    warnings: list[str] = []

    serial_raw = None
    found = re.search(r"N[uú]mero de S[eé]rie:?\s*(.+?)\s+Data\b", flat, re.I)
    if found:
        serial_raw = found.group(1).strip()
    if serial_raw is None or serial_raw.lower().startswith("indiferente"):
        kind, serial = "retrofit_campo", None
        if serial_raw is None:
            warnings.append("Campo 'Número de Série' não encontrado; "
                            "assumi kit de campo. Confira.")
    else:
        candidates = re.findall(r"[A-Z0-9]{12,}", serial_raw.upper())
        parsed = parse_serial(candidates[0]) if candidates else None
        kind = "corte_serie"
        serial = parsed.serie if parsed and parsed.valida else None
        if serial is None:
            warnings.append(f"Série '{serial_raw}' não reconhecida: "
                            "informe a série inicial à mão.")
        if len(candidates) > 1:
            warnings.append("O boletim indica um intervalo de séries; "
                            "usei a primeira. Revise.")

    date = re.search(r"Data:?\s*" + _DATE, flat)
    revision = re.search(r"Revis[aã]o:?\s*" + _DATE, flat)
    subject = re.search(r"Assunto:?\s*(.+?)\s+Revis", flat)
    if subject is None:
        subject = re.search(r"Assunto:?\s*(.{3,80}?)(?:\s{2,}|$)", flat)
    parts, seen = [], set()
    for code, desc in _PART.findall(flat):
        label = f"{code} - {desc.strip()}"
        if label not in seen:
            seen.add(label)
            parts.append(label)

    title = subject.group(1).strip() if subject else ""
    return {
        "modelo": model,
        "tipo": kind,
        "serie_inicial": serial,
        "data_documento": _iso(date.group(1) if date else None),
        "revisao": _iso(revision.group(1) if revision else None),
        "titulo": title[:120],
        "pecas": parts,
        "termos_sugeridos": suggest_terms(title),
        "avisos": warnings,
    }


def suggest_terms(title: str) -> list[str]:
    """Raízes (6 letras) do assunto, para buscar no texto livre."""
    words = re.findall(r"[a-z]{4,}", strip_accents(title).lower())
    terms = []
    for word in words:
        root = word[:6]
        if word not in _STOPWORDS and root not in terms:
            terms.append(root)
    return terms[:3]


def _check_letter(body: str) -> str:
    total = sum((i + 1) * ord(ch) for i, ch in enumerate(body))
    return _ALPHABET[total % len(_ALPHABET)]


def make_code(model: str, kind: str, existing: list[str | None]) -> str:
    """Código único: ``MEL-G5-RF-0003-K`` (K = letra verificadora)."""
    prefix = f"MEL-{MODEL_CODE[model]}-{TYPE_CODE[kind]}-"
    used = [int(c[len(prefix):len(prefix) + 4]) for c in existing
            if c and c.startswith(prefix)]
    body = f"{prefix}{max(used, default=0) + 1:04d}"
    return f"{body}-{_check_letter(body)}"


def valid_code(code: str) -> bool:
    """Confere o formato e a letra verificadora de um código."""
    found = re.fullmatch(r"(MEL-[A-Z0-9]{2}-[A-Z]{2}-\d{4})-([A-Z])", code)
    return bool(found) and _check_letter(found.group(1)) == found.group(2)
