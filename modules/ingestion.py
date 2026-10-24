"""PDF text extraction with section-focused cleaning."""

from __future__ import annotations

import re
from pathlib import Path

REFERENCE_HEADINGS = re.compile(
    r"^\s*(references|bibliography|works cited|literature cited)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
SUPPLEMENT_HEADINGS = re.compile(
    r"^\s*(supplementary materials|appendix|acknowledgments|acknowledgements)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
PAGE_NUMBER_LINE = re.compile(
    r"^\s*(?:page\s*)?\d+\s*(?:of\s*\d+)?\s*$|^\s*\d+\s*$",
    re.IGNORECASE,
)
DOI_LINE = re.compile(r"^\s*https?://doi\.org/\S+\s*$", re.IGNORECASE)


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_references_and_back_matter(text: str) -> str:
    for pattern in (REFERENCE_HEADINGS, SUPPLEMENT_HEADINGS):
        match = pattern.search(text)
        if match:
            text = text[: match.start()]
    return text


def _drop_likely_headers_footers(page_lines: list[str]) -> list[str]:
    """Remove lines that look like running headers, footers, or page numbers."""
    cleaned: list[str] = []
    for line in page_lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if PAGE_NUMBER_LINE.match(stripped):
            continue
        if DOI_LINE.match(stripped):
            continue
        if len(stripped) < 80 and stripped.isupper() and " " in stripped:
            continue
        cleaned.append(stripped)
    return cleaned


def _extract_with_pymupdf(file_path: str) -> str:
    import fitz  # PyMuPDF

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    doc = fitz.open(file_path)
    try:
        parts: list[str] = []
        for page in doc:
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))
            page_lines = [b[4].strip() for b in blocks if b[4].strip()]
            page_lines = _drop_likely_headers_footers(page_lines)
            if page_lines:
                parts.append("\n".join(page_lines))
        return "\n\n".join(parts)
    finally:
        doc.close()


def _extract_with_pdfplumber(file_path: str) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            raw = page.extract_text() or ""
            lines = _drop_likely_headers_footers(raw.splitlines())
            if lines:
                parts.append("\n".join(lines))
    return "\n\n".join(parts)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract raw text from a research PDF, focusing on abstract through discussion.

    Strips reference sections and common header/footer noise. Raises ValueError
    for likely scanned/image-only PDFs with insufficient extractable text.
    """
    text = ""
    errors: list[str] = []

    try:
        text = _extract_with_pymupdf(file_path)
    except Exception as exc:
        errors.append(f"PyMuPDF: {exc}")

    if len(text.strip()) < 200:
        try:
            text = _extract_with_pdfplumber(file_path)
        except Exception as exc:
            errors.append(f"pdfplumber: {exc}")

    text = _normalize_whitespace(text)
    text = _strip_references_and_back_matter(text)
    text = _normalize_whitespace(text)

    if len(text) < 200:
        detail = "; ".join(errors) if errors else "minimal text extracted"
        raise ValueError(
            "This PDF appears scanned or image-only. "
            f"Could not extract enough text for analysis ({detail})."
        )

    return text


def chunk_text(text: str, *, max_chars: int = 12_000, overlap: int = 800) -> list[str]:
    """Split long papers into overlapping chunks for LLM context limits."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            break_at = text.rfind("\n\n", start, end)
            if break_at > start + max_chars // 2:
                end = break_at
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]
