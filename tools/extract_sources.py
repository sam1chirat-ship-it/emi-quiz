#!/usr/bin/env python3
"""extract_sources.py — extrait le texte des sources dans text/.

PDFs via pymupdf (mode 'text' + 'blocks' séparés), docx via python-docx.
Sortie : un .txt par source + un INDEX.md listant les chemins et
volumes. text/ est git-ignoré (voir .gitignore).
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf
from docx import Document

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "sources"
OUT = REPO / "text"


def slug(path: Path) -> str:
    rel = path.relative_to(SRC).as_posix()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", rel).strip("-").lower()
    return s + ".txt"


def extract_pdf(path: Path) -> tuple[str, int]:
    doc = pymupdf.open(path)
    parts: list[str] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        parts.append(f"===== page {i + 1} =====")
        parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(parts), sum(len(p) for p in parts)


def extract_docx(path: Path) -> tuple[str, int]:
    d = Document(path)
    parts: list[str] = []
    for para in d.paragraphs:
        t = para.text
        if t.strip():
            parts.append(t)
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    txt = "\n".join(parts)
    return txt, len(txt)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    index_lines: list[str] = ["# Extractions sources → text/", ""]

    files = sorted(SRC.rglob("*"))
    ok = 0
    for f in files:
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext == ".pdf":
            txt, n = extract_pdf(f)
        elif ext == ".docx":
            txt, n = extract_docx(f)
        else:
            continue
        target = OUT / slug(f)
        target.write_text(txt, encoding="utf-8")
        rel = f.relative_to(SRC).as_posix()
        index_lines.append(f"- `{target.name}` ← `{rel}` ({n} chars)")
        ok += 1
    (OUT / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"extrait {ok} fichiers dans {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
