"""Document ingestion utilities."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf(pdf_path: Path) -> str:
    """Extract text from a text-based PDF while preserving page boundaries."""
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"\n\n--- Page {page_number} ---\n\n{text.strip()}")
    return "".join(pages).strip()


def load_document(path: Path) -> str:
    """Load UTF-8 text/Markdown or extract text from a PDF."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    raise ValueError(f"Unsupported input format: {suffix or '<none>'}")
