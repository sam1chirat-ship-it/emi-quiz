#!/usr/bin/env python3
"""verify.py — contrôles bloquants (SPEC §8.2).

Utilisé par build.py avant le rename atomique. Lit un candidat
`index.html` en mémoire (bytes) et une valeur `data_expected` (dict
attendu tel qu'il apparaît dans le fichier source `data/data.json`).

Règles :
  1. Le HTML contient exactement un <script>.
  2. `node --check` passe sur le contenu du script.
  3. `const DATA = {…};` re-parsé en JSON strict == data_expected.
  4. Tous les ids du squelette DOM (§7.1) sont présents.
  5. Schéma des items (§3) respecté.
  6. Volumes minimaux par catégorie — warning en v1 (non bloquant).
  7. Taille du fichier ≥ 95 % de la taille du précédent build.

Sortie :
  - `verify_all(candidate_bytes, data_expected, prev_size=None, strict_volumes=False)`
    renvoie `(ok:bool, report:dict)`. `report['errors']` liste les
    règles bloquantes, `report['warnings']` les non bloquantes.
  - En CLI (`python3 tools/verify.py index.html`), vérifie le fichier
    donné en argument par rapport à `data/data.json`. Exit 0 / 1.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Ids du squelette DOM (SPEC §7.1)
REQUIRED_IDS = [
    "pupitres",
    "banner",
    "stage",
    "overlay",
    "modal",
    "etoile",
    "boot",
]

# Catégories autorisées (SPEC §2)
CATS_ORDER = [
    "bdp", "pen", "si", "forex", "cot", "tcr",
    "smi", "parite", "monet", "depr", "equil", "mf",
]

# `trap` autorisés (SPEC §10)
TRAPS = {
    "signe-bdp", "stock-flux", "bc-bcour", "certain-incertain",
    "niveau-log", "horizon", "sens-parite", "fixe-flexible",
    "mf-regime", "bs-etapes", "ml-symetrie", "endo-exo",
    "statique-dyn", "sterilise",
}

SENS_ANSWERS = {"up", "down", "same", "ambig"}

# Volumes minimaux par catégorie (SPEC §3, ligne 196)
MIN_PER_CAT = {"qcm": 6, "vf": 4, "sens": 4, "ordre": 1, "ouverte": 2}


def _extract_script(html: str) -> tuple[list[str], str]:
    """Retourne (scripts, script_extrait_pour_node_check)."""
    scripts = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
        html,
        flags=re.DOTALL,
    )
    return scripts, (scripts[0] if scripts else "")


def _extract_data_const(script: str) -> str | None:
    """Retourne la chaîne JSON entre `const DATA=` et le `;` qui termine.

    Contrat : DATA est un objet littéral JSON strict inlined, terminé par
    `};` suivi d'un saut de ligne ou d'un espace. build.py garantit ce
    format.
    """
    marker = "const DATA="
    i = script.find(marker)
    if i < 0:
        return None
    start = i + len(marker)
    # `};` — le premier tel motif après start.
    j = script.find("};", start)
    if j < 0:
        return None
    return script[start:j + 1]  # inclut le `}` fermant


def _node_check(script: str) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile(
        suffix=".js", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(script)
        path = tmp.name
    try:
        r = subprocess.run(
            ["node", "--check", path],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            return True, ""
        return False, r.stderr.strip() or r.stdout.strip() or "node --check a échoué"
    except FileNotFoundError:
        return False, "node introuvable dans le PATH"
    except subprocess.TimeoutExpired:
        return False, "node --check timeout"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _check_ids(html: str) -> list[str]:
    missing = []
    for i in REQUIRED_IDS:
        # id="stage" — quote simple ou double
        pat = re.compile(r"""id\s*=\s*["']""" + re.escape(i) + r"""["']""")
        if not pat.search(html):
            missing.append(i)
    return missing


def _validate_schema(data: dict) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    def dup_id(item_id: str, where: str) -> None:
        if item_id in seen_ids:
            errors.append(f"{where}: id dupliqué « {item_id} »")
        seen_ids.add(item_id)

    cats = data.get("CATS")
    if not isinstance(cats, dict):
        errors.append("CATS absent ou non-objet")
        return errors
    cat_ids = set(cats.keys())
    unknown = cat_ids - set(CATS_ORDER)
    if unknown:
        errors.append(f"CATS: identifiants inconnus {sorted(unknown)}")

    bots = data.get("BOTS")
    if not isinstance(bots, list) or not bots:
        errors.append("BOTS absent ou vide")

    def _base(item: dict, fmt: str, i: int) -> None:
        where = f"{fmt}[{i}]"
        iid = item.get("id")
        if not isinstance(iid, str) or not iid:
            errors.append(f"{where}: id manquant"); return
        dup_id(iid, where)
        if item.get("cat") not in cat_ids:
            errors.append(f"{where} ({iid}): cat inconnue « {item.get('cat')} »")
        if not isinstance(item.get("ch"), int):
            errors.append(f"{where} ({iid}): ch manquant ou non entier")
        d = item.get("diff")
        if not isinstance(d, int) or not 1 <= d <= 3:
            errors.append(f"{where} ({iid}): diff doit être 1..3")
        why = item.get("why")
        if not isinstance(why, str) or not why.strip():
            errors.append(f"{where} ({iid}): why manquant")
        trap = item.get("trap")
        if trap is not None and trap not in TRAPS:
            errors.append(f"{where} ({iid}): trap inconnu « {trap} »")

    for i, it in enumerate(data.get("QCM") or []):
        _base(it, "QCM", i)
        ch = it.get("choices")
        if not isinstance(ch, list) or len(ch) != 4:
            errors.append(f"QCM[{i}] ({it.get('id')}): 4 choices exigées")
        elif not all(isinstance(c, str) and c.strip() for c in ch):
            errors.append(f"QCM[{i}] ({it.get('id')}): choices doivent être des chaînes")
        a = it.get("a")
        if not isinstance(a, int) or not 0 <= a < 4:
            errors.append(f"QCM[{i}] ({it.get('id')}): a doit être 0..3")

    for i, it in enumerate(data.get("VF") or []):
        _base(it, "VF", i)
        if not isinstance(it.get("a"), bool):
            errors.append(f"VF[{i}] ({it.get('id')}): a doit être booléen")

    for i, it in enumerate(data.get("SENS") or []):
        _base(it, "SENS", i)
        if it.get("a") not in SENS_ANSWERS:
            errors.append(f"SENS[{i}] ({it.get('id')}): a ∈ up/down/same/ambig")
        if not isinstance(it.get("ctx"), str) or not it.get("ctx", "").strip():
            errors.append(f"SENS[{i}] ({it.get('id')}): ctx manquant (audit bloquant)")
        if not isinstance(it.get("shock"), str) or not it.get("shock", "").strip():
            errors.append(f"SENS[{i}] ({it.get('id')}): shock manquant")
        if not isinstance(it.get("var"), str) or not it.get("var", "").strip():
            errors.append(f"SENS[{i}] ({it.get('id')}): var manquant")

    for i, it in enumerate(data.get("ORDRE") or []):
        _base(it, "ORDRE", i)
        st = it.get("steps")
        if not isinstance(st, list) or not 3 <= len(st) <= 6:
            errors.append(f"ORDRE[{i}] ({it.get('id')}): steps 3..6")
        elif not all(isinstance(s, str) and s.strip() for s in st):
            errors.append(f"ORDRE[{i}] ({it.get('id')}): steps chaînes non vides")

    for i, it in enumerate(data.get("OUVERTE") or []):
        _base(it, "OUVERTE", i)
        if not isinstance(it.get("model"), str) or not it["model"].strip():
            errors.append(f"OUVERTE[{i}] ({it.get('id')}): model manquant")
        pts = it.get("points")
        if not isinstance(pts, list) or not pts:
            errors.append(f"OUVERTE[{i}] ({it.get('id')}): points liste non vide")

    for i, it in enumerate(data.get("ETOILE") or []):
        iid = it.get("id")
        if not isinstance(iid, str) or not iid:
            errors.append(f"ETOILE[{i}]: id manquant"); continue
        dup_id(iid, f"ETOILE[{i}]")
        if not isinstance(it.get("name"), str) or not it["name"].strip():
            errors.append(f"ETOILE[{i}] ({iid}): name manquant")
        clues = it.get("clues")
        if not isinstance(clues, list) or len(clues) != 5:
            errors.append(f"ETOILE[{i}] ({iid}): 5 indices exigés")

    return errors


def _volumes_warnings(data: dict) -> list[str]:
    """Règle 6 : volumes minimaux par catégorie — warnings en v1."""
    warnings: list[str] = []
    per_cat: dict[str, dict[str, int]] = {c: {} for c in CATS_ORDER}
    fmt_map = [("QCM", "qcm"), ("VF", "vf"), ("SENS", "sens"),
               ("ORDRE", "ordre"), ("OUVERTE", "ouverte")]
    for key, fmt in fmt_map:
        for it in data.get(key) or []:
            c = it.get("cat")
            if c in per_cat:
                per_cat[c][fmt] = per_cat[c].get(fmt, 0) + 1
    for c in CATS_ORDER:
        for fmt, n_min in MIN_PER_CAT.items():
            n = per_cat[c].get(fmt, 0)
            if n < n_min:
                warnings.append(f"cat={c} fmt={fmt}: {n}/{n_min} (cible v1)")
    return warnings


def verify_all(
    candidate: bytes,
    data_expected: dict,
    prev_size: int | None = None,
    strict_volumes: bool = False,
) -> tuple[bool, dict]:
    errors: list[str] = []
    warnings: list[str] = []
    html = candidate.decode("utf-8", errors="replace")

    # 1. Un seul <script>.
    scripts, script = _extract_script(html)
    if len(scripts) != 1:
        errors.append(f"règle 1: {len(scripts)} <script> détectés (1 exigé)")

    # 2. node --check.
    if script:
        ok, msg = _node_check(script)
        if not ok:
            errors.append(f"règle 2 (node --check): {msg}")

    # 3. DATA re-parsée en JSON strict == data_expected.
    if script:
        data_str = _extract_data_const(script)
        if data_str is None:
            errors.append("règle 3: const DATA=… introuvable")
        else:
            try:
                data_got = json.loads(data_str)
            except json.JSONDecodeError as exc:
                errors.append(f"règle 3: DATA n'est pas du JSON strict ({exc})")
            else:
                if data_got != data_expected:
                    errors.append("règle 3: DATA ne round-trip pas avec data.json")

    # 4. Ids du squelette DOM.
    missing = _check_ids(html)
    if missing:
        errors.append(f"règle 4: ids DOM manquants {missing}")

    # 5. Schéma des items.
    for e in _validate_schema(data_expected):
        errors.append(f"règle 5: {e}")

    # 6. Volumes minimaux — warning en v1.
    for w in _volumes_warnings(data_expected):
        (errors if strict_volumes else warnings).append(f"règle 6: {w}")

    # 7. Taille ≥ 95 % du précédent build.
    if prev_size is not None:
        cur = len(candidate)
        if cur < int(prev_size * 0.95):
            errors.append(
                f"règle 7: taille {cur} < 95% du précédent ({prev_size})"
            )

    ok = not errors
    return ok, {"errors": errors, "warnings": warnings, "size": len(candidate)}


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: verify.py <index.html> [data.json]", file=sys.stderr)
        return 2
    idx = Path(argv[1])
    data_path = Path(argv[2]) if len(argv) == 3 else REPO / "data" / "data.json"
    try:
        candidate = idx.read_bytes()
    except OSError as exc:
        print(f"lecture {idx}: {exc}", file=sys.stderr)
        return 2
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"lecture {data_path}: {exc}", file=sys.stderr)
        return 2
    ok, report = verify_all(candidate, data)
    for w in report["warnings"]:
        print(f"WARN {w}")
    for e in report["errors"]:
        print(f"ERR  {e}", file=sys.stderr)
    print(f"size={report['size']} bytes, ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
