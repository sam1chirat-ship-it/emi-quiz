#!/usr/bin/env python3
"""add.py — ajout contrôlé d'items dans data/data.json.

Le fichier d'entrée est un JSON de la forme :

    { "QCM": [...], "QCMM": [...], "VF": [...], "SENS": [...], "ORDRE": [...],
      "OUVERTE": [...], "ETOILE": [...], "CATS": {...}, "LESSONS": {...} }

CATS : seules des catégories NOUVELLES sont acceptées (id ∈ verify.CATS_ORDER).
LESSONS : ajoute ou remplace le cours d'une catégorie.

Chaque item peut porter un `id` explicite ; si absent, add.py attribue le
prochain identifiant libre `<cat>-NNN` pour la catégorie.

Étapes (dry-run par défaut) :
  1. Charge data.json et le lot d'entrée.
  2. Attribue les ids manquants.
  3. Fusionne (data + lot) en mémoire.
  4. Passe le résultat à audit.audit_data.
  5. Si aucun bloquant ne concerne un item du lot, et (--write) donné :
     réécrit data.json, puis appelle build.py ; si le build échoue,
     data.json est restauré. Les bloquants préexistants (hors lot) sont
     affichés mais ne bloquent pas l'ajout.

Sans --write : impression du résumé et code de sortie 0/1 selon audit.

Usage :
    python3 tools/add.py path/to/items.json
    python3 tools/add.py path/to/items.json --write
    python3 tools/add.py path/to/items.json --warnings-fatal
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from audit import audit_data  # noqa: E402
from verify import CATS_ORDER  # noqa: E402

DATA_JSON = REPO / "data" / "data.json"
ITEM_BANKS = ("QCM", "QCMM", "VF", "SENS", "ORDRE", "OUVERTE")
BUILD_PY = REPO / "tools" / "build.py"


def _load_data() -> dict:
    return json.loads(DATA_JSON.read_text(encoding="utf-8"))


def _used_ids_by_cat(data: dict) -> dict[str, set[int]]:
    used: dict[str, set[int]] = defaultdict(set)
    for key in ITEM_BANKS + ("ETOILE",):
        for it in data.get(key) or []:
            iid = it.get("id", "")
            m = re.match(r"^([a-z0-9]+)-(\d{3})$", iid)
            if m:
                used[m.group(1)].add(int(m.group(2)))
    return used


def _assign_ids(lot: dict, used: dict[str, set[int]]) -> list[str]:
    assigned: list[str] = []
    for key in ITEM_BANKS:
        for it in lot.get(key) or []:
            if "id" in it and it["id"]:
                continue
            cat = it.get("cat")
            if cat not in CATS_ORDER:
                raise SystemExit(f"add: cat inconnue « {cat} » pour item {it!r}")
            n = 1
            while n in used[cat]:
                n += 1
            used[cat].add(n)
            it["id"] = f"{cat}-{n:03d}"
            assigned.append(it["id"])
    return assigned


def _merge(data: dict, lot: dict) -> dict:
    merged = json.loads(json.dumps(data, ensure_ascii=False))  # deep copy
    for cid, entry in (lot.get("CATS") or {}).items():
        if cid in merged["CATS"] and merged["CATS"][cid] != entry:
            raise SystemExit(f"add: CATS[{cid}] existe déjà (modification refusée)")
        if cid not in CATS_ORDER:
            raise SystemExit(f"add: CATS[{cid}] absent de verify.CATS_ORDER")
        merged["CATS"][cid] = entry
    for cid, lesson in (lot.get("LESSONS") or {}).items():
        merged.setdefault("LESSONS", {})[cid] = lesson
    for key in ITEM_BANKS + ("ETOILE",):
        if key not in merged:
            merged[key] = []
        for it in lot.get(key) or []:
            merged[key].append(it)
    return merged


def _write_data(data: dict) -> None:
    # Même sérialisation que le fichier existant (indent 2, sans \n final)
    # pour que les diffs git ne montrent que les items ajoutés.
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    tmp = DATA_JSON.with_suffix(".json.tmp")
    tmp.write_text(txt, encoding="utf-8")
    tmp.replace(DATA_JSON)


def _run_build() -> int:
    r = subprocess.run([sys.executable, str(BUILD_PY)], cwd=REPO)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lot", help="fichier JSON du lot à ajouter")
    ap.add_argument("--write", action="store_true", help="applique l'écriture (défaut : dry-run)")
    ap.add_argument("--warnings-fatal", action="store_true", help="signalements bloquent aussi")
    args = ap.parse_args()

    lot_path = Path(args.lot)
    try:
        lot = json.loads(lot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"lot {lot_path}: {exc}", file=sys.stderr)
        return 2

    if not isinstance(lot, dict):
        print("lot: la racine doit être un objet {QCM,VF,SENS,...}", file=sys.stderr)
        return 2

    data = _load_data()
    for cid in (lot.get("CATS") or {}):
        if cid not in CATS_ORDER:
            print(f"add: CATS[{cid}] absent de verify.CATS_ORDER", file=sys.stderr)
            return 2
    known = set(data["CATS"]) | set(lot.get("CATS") or {})
    for key in ITEM_BANKS:
        for it in lot.get(key) or []:
            if it.get("cat") not in known:
                print(f"add: cat inconnue « {it.get('cat')} »", file=sys.stderr)
                return 2
    used = _used_ids_by_cat(data)
    try:
        assigned = _assign_ids(lot, used)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if assigned:
        print(f"add: ids attribués = {assigned}")

    try:
        merged = _merge(data, lot)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    new_ids = {it["id"] for k in ITEM_BANKS + ("ETOILE",) for it in lot.get(k) or []}
    id_re = re.compile(r"[a-z0-9]+-\d{2,3}")

    def _in_lot(msg: str) -> bool:
        return any(m in new_ids for m in id_re.findall(msg))

    all_blocking, all_warnings = audit_data(merged)
    blocking = [b for b in all_blocking if _in_lot(b)]
    warnings = [w for w in all_warnings if _in_lot(w) or "cat=" in w]
    for w in warnings:
        print(f"WARN {w}")
    for b in all_blocking:
        print(("BLOCK " if b in blocking else "PRE   ") + b, file=sys.stderr)

    total_new = sum(len(lot.get(k) or []) for k in ITEM_BANKS + ("ETOILE",))
    print(f"add: {total_new} items proposés · {len(blocking)} bloquants · {len(warnings)} signalements",
          file=sys.stderr)

    if blocking:
        print("add: écriture refusée (audit bloquant).", file=sys.stderr)
        return 1
    if args.warnings_fatal and warnings:
        print("add: écriture refusée (--warnings-fatal).", file=sys.stderr)
        return 1

    if not args.write:
        print("add: dry-run, rien écrit. Utilise --write pour appliquer.", file=sys.stderr)
        return 0

    backup = DATA_JSON.read_text(encoding="utf-8")
    _write_data(merged)
    print(f"add: data.json mis à jour ({total_new} items ajoutés). Lancement du build…", file=sys.stderr)
    rc = _run_build()
    if rc != 0:
        DATA_JSON.write_text(backup, encoding="utf-8")
        print("add: build en échec, data.json restauré.", file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
