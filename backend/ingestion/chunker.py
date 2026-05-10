"""Découpage des PDF juridiques marocains en articles (chunks)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pdfplumber

CODE_MAPPING = {
    "code_commerce": "Code de Commerce",
    "code_famille": "Code de la Famille",
    "code_obligations_contrats": "Code des Obligations et des Contrats",
    "code_penal": "Code Pénal",
    "code_procedure_civile": "Code de Procédure Civile",
    "code_travail": "Code du Travail",
}

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_ARTICLE_HEADER = re.compile(
    r"^(?:Article|ARTICLE|Art\.)\s+(\d+(?:\s*[\d\w]*)?)",
    re.IGNORECASE | re.MULTILINE,
)
_FALLBACK_CHUNK_SIZE = 500


def _clean_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = _CONTROL_CHARS.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_full_text(pdf_path: Path) -> str:
    parts: list[str] = []
    path_arg = pdf_path if pdf_path.exists() else str(pdf_path)
    with pdfplumber.open(path_arg) as pdf:
        for page in pdf.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if not t.strip():
                try:
                    t = page.extract_text(layout=True) or ""
                except Exception:
                    t = ""
            parts.append(t)
    return "\n\n".join(parts)


def _article_number_from_chunk(chunk: str) -> str:
    m = _ARTICLE_HEADER.search(chunk.strip())
    if m:
        return m.group(1).strip()
    return "?"


def _fallback_chunks(text: str, source_file: str, code_name: str) -> list[dict]:
    out: list[dict] = []
    clean = text.strip()
    if not clean:
        return out
    for i, start in enumerate(range(0, len(clean), _FALLBACK_CHUNK_SIZE)):
        piece = clean[start : start + _FALLBACK_CHUNK_SIZE]
        aid = f"{Path(source_file).stem.lower()}_fb_{i}"
        out.append(
            {
                "article_id": aid,
                "code": code_name,
                "article_number": f"segment_{i}",
                "content": piece,
                "source_file": source_file,
            }
        )
    return out


def chunk_pdf(pdf_path: Path) -> list[dict]:
    """
    Extrait et découpe un PDF en articles.
    Retourne une liste de dicts avec article_id, code, article_number, content, source_file.
    """
    pdf_path = Path(pdf_path)
    stem_key = pdf_path.stem.lower()
    code_name = CODE_MAPPING.get(stem_key, pdf_path.stem)
    source_file = pdf_path.name

    text = _extract_full_text(pdf_path)
    text = _clean_text(text)
    if not text:
        return []

    split_pattern = r"(?=\b(?:Article|ARTICLE|Art\.)\s+\d+)"
    parts = re.split(split_pattern, text)
    parts = [p.strip() for p in parts if p and p.strip()]

    if len(parts) <= 1 and not re.search(
        r"\b(?:Article|ARTICLE|Art\.)\s+\d+", text, re.IGNORECASE
    ):
        return _fallback_chunks(text, source_file, code_name)

    rows: list[dict] = []
    idx = 0
    for part in parts:
        if not re.match(r"^(?:Article|ARTICLE|Art\.)\s+\d+", part, re.IGNORECASE):
            if not rows and part:
                aid = f"{stem_key}_preamble_{idx}"
                rows.append(
                    {
                        "article_id": aid,
                        "code": code_name,
                        "article_number": "preamble",
                        "content": part,
                        "source_file": source_file,
                    }
                )
                idx += 1
            continue
        num = _article_number_from_chunk(part)
        aid = f"{stem_key}_art_{num}_{idx}"
        rows.append(
            {
                "article_id": aid,
                "code": code_name,
                "article_number": num,
                "content": part,
                "source_file": source_file,
            }
        )
        idx += 1

    if not rows:
        return _fallback_chunks(text, source_file, code_name)

    return rows
