#!/usr/bin/env python3
"""build.py — génère index.html à partir de src/template.html + data/data.json.

Contrat (SPEC §8.1) :
  - Remplace le marqueur `/*__DATA__*/` dans le template par
    `const DATA = <json>;`, où <json> est produit par
    `json.dumps(data, ensure_ascii=False, separators=(', ', ': '))`.
  - Écriture atomique : `.tmp` puis `os.rename` uniquement si
    `verify_all` retourne ok=True.
  - Refuse d'écrire si verify échoue. Exit non-zéro.

Usage :
  python3 tools/build.py                 # ./index.html
  python3 tools/build.py --check-only    # dry-run : sort le rapport
  python3 tools/build.py --strict-volumes # les volumes cat/format
                                         # deviennent bloquants
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from verify import verify_all  # noqa: E402

TEMPLATE = REPO / "src" / "template.html"
DATA_JSON = REPO / "data" / "data.json"
OUTPUT = REPO / "index.html"

VENDOR = REPO / "vendor"
KATEX_CSS = VENDOR / "katex.min.css"
KATEX_JS = VENDOR / "katex.min.js"
KATEX_FONTS = VENDOR / "fonts"

MARKER = "/*__DATA__*/"
MARKER_KATEX_CSS = "/*__KATEX_CSS__*/"
MARKER_KATEX_JS = "/*__KATEX_JS__*/"


def _inline_katex_css() -> str:
    """Charge katex.min.css et remplace chaque url(fonts/NAME.woff2) par un
    data URI base64. Supprime les fallbacks woff/ttf pour économiser des octets
    (Safari iOS et Chromium supportent woff2 partout où on cible)."""
    css = KATEX_CSS.read_text(encoding="utf-8")

    def repl_src(m: re.Match) -> str:
        # m.group(0) est un `src:` complet (url(...) format(...), url(...) format(...), ...)
        # On garde uniquement la première url(...woff2)
        m2 = re.search(r'url\(fonts/([A-Za-z0-9_-]+)\.woff2\)', m.group(0))
        if not m2:
            return m.group(0)
        name = m2.group(1)
        font_path = KATEX_FONTS / f"{name}.woff2"
        if not font_path.exists():
            raise SystemExit(f"vendor: {font_path} manquant")
        b64 = base64.b64encode(font_path.read_bytes()).decode("ascii")
        return f'src:url(data:font/woff2;base64,{b64}) format("woff2")'

    css = re.sub(r'src:\s*url\(fonts/[^)]+\)[^;}]*', repl_src, css)
    return css


def _inline_katex_js() -> str:
    js = KATEX_JS.read_text(encoding="utf-8")
    return js


def load_data() -> dict:
    with DATA_JSON.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def render(template: str, data: dict) -> bytes:
    for m in (MARKER, MARKER_KATEX_CSS, MARKER_KATEX_JS):
        if template.count(m) != 1:
            raise SystemExit(
                f"template: {template.count(m)} occurrence(s) de {m} "
                f"(exigé : exactement 1)"
            )
    payload = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))
    injected = f"const DATA = {payload};"
    html = template.replace(MARKER, injected)
    html = html.replace(MARKER_KATEX_CSS, _inline_katex_css())
    html = html.replace(MARKER_KATEX_JS, _inline_katex_js())
    return html.encode("utf-8")


def atomic_write(path: Path, candidate: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(candidate)
    os.rename(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser(description="build index.html")
    ap.add_argument("--check-only", action="store_true",
                    help="ne rien écrire, juste lancer verify")
    ap.add_argument("--strict-volumes", action="store_true",
                    help="volumes cat/format bloquants (au lieu de warnings)")
    args = ap.parse_args()

    try:
        data = load_data()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"data.json: {exc}", file=sys.stderr)
        return 2
    try:
        template = load_template()
    except OSError as exc:
        print(f"template.html: {exc}", file=sys.stderr)
        return 2

    candidate = render(template, data)

    prev_size = OUTPUT.stat().st_size if OUTPUT.exists() else None
    ok, report = verify_all(
        candidate, data,
        prev_size=prev_size,
        strict_volumes=args.strict_volumes,
    )

    for w in report["warnings"]:
        print(f"WARN {w}")
    for e in report["errors"]:
        print(f"ERR  {e}", file=sys.stderr)

    print(f"size={report['size']} bytes, ok={ok}", file=sys.stderr)

    if not ok:
        print("build refusé (verify a échoué).", file=sys.stderr)
        return 1
    if args.check_only:
        print("check-only : rien écrit.", file=sys.stderr)
        return 0

    atomic_write(OUTPUT, candidate)
    print(f"OK: {OUTPUT} ({report['size']} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
