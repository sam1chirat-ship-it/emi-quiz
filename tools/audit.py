#!/usr/bin/env python3
"""audit.py — qualité éditoriale des banques QCM/VF/SENS/ORDRE/OUVERTE.

Sortie deux niveaux (SPEC §8.3) :
  - BLOQUANT (exit 1)  : strict_dup, fuzzy_dup, answer_in_question,
    multi_question, answer_too_long, duplicate_in_lot, qcm_choice_dup,
    sens_no_ctx.
  - SIGNALEMENT (exit 0) : perishable, qcm_correct_longest,
    convention (regex compte financier positif sans sortie).

Usage :
  python3 tools/audit.py               # audit data/data.json
  python3 tools/audit.py --json path   # audit un fichier de lot (voir add.py)
  python3 tools/audit.py --warnings-fatal  # signalements → bloquants

Aucune écriture. Peut être lu par add.py qui délègue l'écriture au build.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify import TRAPS as VERIFY_TRAPS  # noqa: E402  (source unique des traps)
DATA_JSON = REPO / "data" / "data.json"

FUZZY_THRESHOLD = 0.72
ANSWER_TOO_LONG_CHARS = 75
QCM_CORRECT_LONGEST_PCT = 0.40
QCMM_OK_LONGER_RATIO = 1.25   # longueur moyenne des « ok » / « ko » par catégorie
BANKS = ("QCM", "QCMM", "VF", "SENS", "ORDRE", "OUVERTE")


def variants(v) -> list[str]:
    """Un champ texte peut être une chaîne ou une liste de formulations."""
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v or "")]

PERISHABLE_PATTERNS = [
    r"\bactuel(le|s|les)?\b", r"\baujourd'hui\b", r"\brecord\b",
    r"\bdepuis\b", r"\bmondial(ement)?\b", r"\bactuellement\b",
]
YEAR_RE = re.compile(r"\b(20[2-9]\d)\b")  # années >= 2020 traitées comme périssables


def normalize(s: str) -> str:
    # Normalisation forte : diacritiques enlevés, garde uniquement alphanumérique.
    # Utilisée pour tests de similitude narrative (fuzzy_dup, answer_in_question).
    s = unicodedata.normalize("NFD", s).lower()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def normalize_math(s: str) -> str:
    # Normalisation faible : minuscules + espaces compactés, garde tous les
    # symboles (+, −, ×, ÷, ε, /, =). Utilisée pour qcm_choice_dup où les
    # formules identiques à un signe près doivent rester distinctes.
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_data(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_answers(item: dict) -> list[str]:
    """Retourne les textes de réponse d'un item (par format)."""
    fmt = _detect_fmt(item)
    if fmt == "qcmm":
        return [str(x) for x in item.get("ok") or []]
    if fmt == "qcm":
        return [str(item["choices"][item["a"]])]
    if fmt == "vf":
        return ["vrai" if item["a"] else "faux"]
    if fmt == "sens":
        return [str(item["a"])]
    if fmt == "ordre":
        return [" | ".join(item["steps"])]
    if fmt == "ouverte":
        return [str(item.get("model", ""))]
    return []


def _detect_fmt(it: dict) -> str:
    if "ok" in it and "ko" in it:
        return "qcmm"
    if "choices" in it and "a" in it and isinstance(it["a"], int):
        return "qcm"
    if isinstance(it.get("a"), bool):
        return "vf"
    if "shock" in it and "var" in it:
        return "sens"
    if "steps" in it:
        return "ordre"
    if "model" in it:
        return "ouverte"
    return "?"


def _item_source(it: dict) -> str:
    fmt = _detect_fmt(it)
    if fmt in ("qcm", "vf", "qcmm"):
        return " / ".join(variants(it.get("q", "")))
    if fmt == "sens":
        return (it.get("ctx", "") + " | " + it.get("shock", "") + " → " + it.get("var", "")).strip(" |→ ")
    if fmt == "ordre":
        return it.get("title", "") or ""
    if fmt == "ouverte":
        return " / ".join(variants(it.get("q", "")))
    return ""


def audit_data(data: dict) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    warnings: list[str] = []

    all_items: list[tuple[str, dict]] = []
    for key in BANKS:
        for it in data.get(key) or []:
            all_items.append((key, it))

    # Index par (fmt, énoncé normalisé) et par (fmt, réponse normalisée) pour
    # les tests de doublons.
    by_signature: dict[tuple[str, str], list[str]] = defaultdict(list)
    by_answer: dict[tuple[str, str], list[tuple[str, str, dict]]] = defaultdict(list)

    for key, it in all_items:
        fmt = _detect_fmt(it)
        src = _item_source(it)
        ans_list = collect_answers(it)
        sig = (fmt, normalize(src) + " || " + normalize(" ".join(ans_list)))
        by_signature[sig].append(it["id"])
        for ans in ans_list:
            by_answer[(fmt, normalize(ans))].append((it["id"], src, it))

    # 1. strict_dup : deux items ont la même clef (fmt, source normalisée +
    #    réponse). C'est plus strict que "même question" seul, moins qu'un
    #    match parfait de texte.
    for sig, ids in by_signature.items():
        if len(ids) > 1:
            blocking.append(f"strict_dup fmt={sig[0]} ids={ids}")

    # 2. fuzzy_dup : mêmes format+réponse et énoncés proches (ratio > 0.72).
    # Ne s'applique pas au format `sens` : deux sens avec même réponse mais
    # cadres différents (fixe vs flexible, choc Ms vs choc G) partagent
    # beaucoup de vocabulaire canonique du cours (« Mundell-Fleming »,
    # « mobilité parfaite »…) et déclencheraient trop de faux positifs.
    # Les vrais doublons sens sont couverts par strict_dup (ctx+shock+var+a
    # identiques → même signature).
    for (fmt, ans), triples in by_answer.items():
        if fmt == "sens":
            continue
        if len(triples) < 2:
            continue
        for i in range(len(triples)):
            for j in range(i + 1, len(triples)):
                id_a, src_a, it_a = triples[i]
                id_b, src_b, it_b = triples[j]
                if id_a == id_b:
                    continue
                r = difflib.SequenceMatcher(None, normalize(src_a), normalize(src_b)).ratio()
                if r > FUZZY_THRESHOLD:
                    blocking.append(f"fuzzy_dup fmt={fmt} ratio={r:.2f} ids=[{id_a},{id_b}]")

    # Traps autorisés (SPEC §10) — miroir de verify.py.
    TRAPS_OK = VERIFY_TRAPS

    # 3-8 : contrôles item par item.
    for key, it in all_items:
        iid = it.get("id", "?")
        fmt = _detect_fmt(it)
        src = _item_source(it)

        # 3.a. mat : obligatoire (aligné sur verify.py — évite qu'un lot passe
        #      l'audit mais casse le build).
        mat = it.get("mat")
        if not isinstance(mat, str) or not mat.strip():
            blocking.append(f"mat_missing id={iid}")

        # 3.b. why : obligatoire pour TOUS les formats, y compris OUVERTE
        #      (verify.py le vérifie systématiquement).
        why = it.get("why")
        if not isinstance(why, str) or not why.strip():
            blocking.append(f"why_missing id={iid}")

        # 3.c. trap : si présent, doit être dans la liste §10 (verify.py
        #      refuse « - » ou un tag inventé).
        trap = it.get("trap")
        if trap is not None:
            if trap not in TRAPS_OK:
                blocking.append(f"trap_invalid id={iid} trap={trap!r}")

        # 3. answer_in_question : la bonne réponse (>=3 chars significatifs)
        #    apparaît dans l'énoncé.
        for ans in collect_answers(it):
            nans = normalize(ans)
            if len(nans) < 4:
                continue
            if fmt == "vf":
                continue  # "vrai" / "faux" ne comptent pas.
            if any(nans in normalize(v) for v in variants(it.get("q", "")) if fmt in ("qcm", "qcmm", "ouverte")) \
                    or (fmt not in ("qcm", "qcmm", "ouverte") and nans in normalize(src)):
                blocking.append(f"answer_in_question id={iid} ans in question")

        # 4. multi_question : plusieurs '?' dans l'énoncé.
        texts = variants(it.get("q", "")) if fmt in ("qcm", "qcmm", "vf", "ouverte") else [src]
        for text in texts:
            if text.count("?") > 1:
                blocking.append(f"multi_question id={iid} count={text.count('?')}")

        # 5. answer_too_long : réponse > 75 caractères. S'applique à `vf`
        #    (jamais > 4 chars en pratique). Les `ouverte` ont des
        #    réponses-modèles longues par nature (essais d'examen) —
        #    seuil relevé à 500 en bloquant + warning au-delà de 350.
        #    Les `choices` de qcm sont éditoriaux : warning si > 120.
        if fmt == "vf":
            for ans in collect_answers(it):
                if len(ans) > ANSWER_TOO_LONG_CHARS:
                    blocking.append(f"answer_too_long id={iid} len={len(ans)}")
        elif fmt == "ouverte":
            model_len = len(it.get("model") or "")
            if model_len > 500:
                blocking.append(f"answer_too_long id={iid} model_len={model_len}")
            elif model_len > 350:
                warnings.append(f"ouverte_model_long id={iid} len={model_len}")
        elif fmt == "qcm":
            longest = max(len(c) for c in it["choices"])
            if longest > 120:
                warnings.append(f"qcm_choice_long id={iid} len={longest}")

        # 6. qcm_choice_dup : deux choix identiques après normalisation FAIBLE
        #    (préserve les opérateurs mathématiques + / − / × / ε).
        if fmt == "qcm":
            seen = set()
            for c in it["choices"]:
                n = normalize_math(c)
                if n in seen:
                    blocking.append(f"qcm_choice_dup id={iid} choix « {c[:40]} »")
                seen.add(n)

        # 6 bis. qcmm : pas de proposition en double (ok ∪ ko), aucune
        #        proposition à la fois juste et fausse ; longueur signalée.
        if fmt == "qcmm":
            seen = {}
            for side in ("ok", "ko"):
                for c in it.get(side) or []:
                    n = normalize_math(c)
                    if n in seen:
                        blocking.append(f"qcmm_choice_dup id={iid} « {c[:40]} » ({seen[n]}/{side})")
                    seen[n] = side
                    if len(c) > 160:
                        warnings.append(f"qcmm_choice_long id={iid} len={len(c)}")

        # 7. sens_no_ctx : un sens sans ctx est ambigu (bloquant).
        if fmt == "sens":
            if not (it.get("ctx") or "").strip():
                blocking.append(f"sens_no_ctx id={iid}")

        # 8. duplicate_in_lot est géré si l'audit tourne sur un lot ; ici
        #    on l'assimile à strict_dup au niveau du fichier entier.

    # Signalements non bloquants.

    # qcm_correct_longest : par catégorie, > 40 % des qcm ont la bonne
    # réponse la plus longue.
    per_cat: dict[str, list[dict]] = defaultdict(list)
    for it in data.get("QCM") or []:
        per_cat[it["cat"]].append(it)
    for cat, items in per_cat.items():
        if len(items) < 3:
            continue
        cnt = 0
        for it in items:
            lens = [len(c) for c in it["choices"]]
            if len(set(lens)) == 1:
                continue
            if lens[it["a"]] == max(lens):
                cnt += 1
        if cnt / len(items) > QCM_CORRECT_LONGEST_PCT:
            warnings.append(
                f"qcm_correct_longest cat={cat} {cnt}/{len(items)} ({100*cnt/len(items):.0f}%)"
            )

    # qcmm_ok_longer : par catégorie, les propositions justes sont en
    # moyenne nettement plus longues que les fausses (indice de longueur).
    qcmm_cat: dict[str, list[dict]] = defaultdict(list)
    for it in data.get("QCMM") or []:
        qcmm_cat[it["cat"]].append(it)
    for cat, items in qcmm_cat.items():
        oks = [len(c) for it in items for c in it.get("ok") or []]
        kos = [len(c) for it in items for c in it.get("ko") or []]
        if oks and kos:
            r = (sum(oks) / len(oks)) / (sum(kos) / len(kos))
            if r > QCMM_OK_LONGER_RATIO:
                warnings.append(f"qcmm_ok_longer cat={cat} ratio={r:.2f}")

    # perishable : mots-clefs ou années récentes dans l'énoncé.
    perish_re = re.compile("|".join(PERISHABLE_PATTERNS), re.IGNORECASE)
    for _, it in all_items:
        text = _item_source(it) + " " + " ".join(collect_answers(it))
        if perish_re.search(text) or YEAR_RE.search(text):
            iid = it.get("id", "?")
            match = perish_re.search(text) or YEAR_RE.search(text)
            warnings.append(f"perishable id={iid} motif={match.group(0)!r}")

    # convention : « compte financier positif » sans « sortie » à proximité.
    cf_re = re.compile(r"compte\s+financier\s+positif", re.IGNORECASE)
    for _, it in all_items:
        text = _item_source(it) + " " + it.get("why", "")
        if cf_re.search(text) and "sortie" not in normalize(text):
            warnings.append(f"convention id={it.get('id')} « compte financier positif » sans « sortie »")

    return blocking, warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(DATA_JSON), help="fichier data.json à auditer")
    ap.add_argument("--warnings-fatal", action="store_true", help="signalements → bloquants")
    args = ap.parse_args()

    path = Path(args.json)
    try:
        data = load_data(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"lecture {path}: {exc}", file=sys.stderr)
        return 2

    blocking, warnings = audit_data(data)
    for w in warnings:
        print(f"WARN {w}")
    for b in blocking:
        print(f"BLOCK {b}", file=sys.stderr)

    n_items = sum(len(data.get(k) or []) for k in BANKS)
    print(f"audit : {n_items} items, {len(blocking)} bloquants, {len(warnings)} signalements", file=sys.stderr)

    if blocking:
        return 1
    if args.warnings_fatal and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
