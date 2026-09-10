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
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from verify import verify_all  # noqa: E402

TEMPLATE = REPO / "src" / "template.html"
DATA_JSON = REPO / "data" / "data.json"
OUTPUT = REPO / "index.html"

MARKER = "/*__DATA__*/"


def load_data() -> dict:
    with DATA_JSON.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def render(template: str, data: dict) -> bytes:
    if template.count(MARKER) != 1:
        raise SystemExit(
            f"template: {template.count(MARKER)} occurrence(s) de {MARKER} "
            f"(exigé : exactement 1)"
        )
    payload = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))
    injected = f"const DATA = {payload};"
    html = template.replace(MARKER, injected)
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
