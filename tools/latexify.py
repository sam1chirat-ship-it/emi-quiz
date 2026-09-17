#!/usr/bin/env python3
"""latexify.py — passe conservatrice de conversion LaTeX pour LESSONS.

Ne touche QUE les *lignes-formule* pures (essentiellement une équation,
< 120 chars, contient `=` ou `≈`, moins de 3 mots FR ≥ 4 lettres) →
enveloppées en \[...\] et Unicode traduit en macros LaTeX.

Le reste (prose contenant des symboles Grecs) est laissé intact —
KaTeX ne le rendra pas mais le contenu Unicode reste lisible. La
conversion inline plus fine sera faite item par item plus tard.

Idempotent : détecte \[ / \( déjà présents et skip.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "data.json"

UNI2TEX = {
    "Δ": r"\Delta ", "Π": r"\Pi ", "Σ": r"\Sigma ",
    "α": r"\alpha ", "β": r"\beta ", "γ": r"\gamma ", "δ": r"\delta ",
    "ε": r"\varepsilon ", "η": r"\eta ", "θ": r"\theta ", "λ": r"\lambda ",
    "μ": r"\mu ", "π": r"\pi ", "ρ": r"\rho ", "σ": r"\sigma ",
    "τ": r"\tau ", "φ": r"\varphi ", "ϕ": r"\phi ", "ω": r"\omega ",
    "↑": r"\uparrow ", "→": r"\to ", "↓": r"\downarrow ",
    "⇔": r"\Leftrightarrow ", "∈": r"\in ", "∝": r"\propto ",
    "∞": r"\infty ", "∫": r"\int ", "∼": r"\sim ",
    "≈": r"\approx ", "≠": r"\ne ", "≤": r"\le ", "≥": r"\ge ",
    "·": r"\cdot ", "×": r"\times ", "±": r"\pm ", "−": "-",
    "≷": r"\gtrless ", "√": r"\sqrt",
    # Modifier lettres superscript/subscript courantes en éco
    "ᵃ": r"^a", "ᵇ": r"^b", "ⁿ": r"^n", "ᵗ": r"^t",
    "ᵢ": r"_i", "ⱼ": r"_j", "ₖ": r"_k", "ₙ": r"_n",
    # Lettres précomposées avec dot above (dérivées temporelles)
    "Ȧ": r"\dot A ", "ȧ": r"\dot a ",
    "Ḃ": r"\dot B ", "ḃ": r"\dot b ",
    "Ḣ": r"\dot H ", "ḣ": r"\dot h ",
    "Ġ": r"\dot G ", "ġ": r"\dot g ",
    "Ẋ": r"\dot X ", "ẋ": r"\dot x ",
    "Ẏ": r"\dot Y ", "ẏ": r"\dot y ",
    "Ż": r"\dot Z ", "ż": r"\dot z ",
    # Lettres précomposées avec macron (moyennes)
    "Ā": r"\bar A ", "ā": r"\bar a ", "Ē": r"\bar E ", "ē": r"\bar e ",
    "Ī": r"\bar I ", "ī": r"\bar i ", "Ō": r"\bar O ", "ō": r"\bar o ",
    "Ū": r"\bar U ", "ū": r"\bar u ", "Ȳ": r"\bar Y ", "ȳ": r"\bar y ",
    # Chapeau (steady state)
    "Â": r"\hat A ", "â": r"\hat a ",
    "Ê": r"\hat E ", "ê": r"\hat e ",
    "Ĥ": r"\hat H ", "ĥ": r"\hat h ",
    "Ŷ": r"\hat Y ", "ŷ": r"\hat y ",
    # Chiffres exposant/indice
    "⁰": r"^0", "¹": r"^1", "²": r"^2", "³": r"^3",
    "⁴": r"^4", "⁵": r"^5", "⁶": r"^6", "⁷": r"^7",
    "⁸": r"^8", "⁹": r"^9",
    "₀": r"_0", "₁": r"_1", "₂": r"_2", "₃": r"_3",
    "₄": r"_4", "₅": r"_5", "₆": r"_6", "₇": r"_7",
    "₈": r"_8", "₉": r"_9",
    # Note : les combining marks (̇ dot, ̄ bar, ̂ hat) sont
    # traités par to_latex avant cette table (pour capital+combining).
}

MATH_SIGNATURE = set("ΔΠΣαβγδεηθλμπρστφϕω↑↓→⇔∈∝∞∫∼≈≠≤≥·×±−≷√=_^")


def to_latex(run: str) -> str:
    """Traduit une chaîne pure math en LaTeX."""
    # 0) combining marks : <lettre>+diacritique → macro LaTeX
    #    U+0307 = dot above → \dot ; U+0304 = macron → \bar ;
    #    U+0302 = circumflex → \hat
    diacritic = {"̇": "dot", "̄": "bar", "̂": "hat"}
    out = []
    i = 0
    n = len(run)
    while i < n:
        c = run[i]
        if i + 1 < n and run[i + 1] in diacritic:
            out.append("\\" + diacritic[run[i + 1]] + "{" + c + "}")
            i += 2
            continue
        out.append(c)
        i += 1
    run = "".join(out)
    # 1) pré-transforme les patterns `<var>*` en `<var>^*` (avant
    #    conversion Unicode, sinon les macros \pi trailent un espace)
    s = re.sub(
        r"([A-Za-z_}\]ΔΠΣαβγδεηθλμπρστφϕω])\*",
        r"\1^*",
        run,
    )
    # 2) traduit char par char
    out = []
    for ch in s:
        out.append(UNI2TEX.get(ch, ch))
    s = "".join(out)
    # 3) échappe `%` (LaTeX : commentaire)
    s = s.replace("%", r"\%")
    # 4) supprime les espaces parasites autour de _, ^, {, }
    s = re.sub(r"\s+([_^])", r"\1", s)
    s = re.sub(r"([_^])\s+", r"\1", s)
    # 5) `k̇` → `\dot k` (le combining dot a été absorbé au-dessus,
    #    donc on capture "\dot" via une passe : lettre isolée suivie
    #    de rien de spécifique ne peut pas être détectée fiablement.
    #    On accepte de perdre le point.
    # 6) exposants entre parens : `x^(a+b)` → `x^{a+b}`
    s = re.sub(r"\^\(([^()]{1,40})\)", r"^{\1}", s)
    s = re.sub(r"_\(([^()]{1,20})\)", r"_{\1}", s)
    # 7) préfixe modifieur devant un opérateur : `2/3\cdot ` -> `\tfrac{2}{3}`
    #    trop risqué en regex ; on laisse.
    # 8) compacte
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


FR_PROSE = {
    "absolue", "relative", "condition", "revenus", "transferts",
    "excédent", "courant", "exporte", "importe", "pays", "hausse",
    "baisse", "monnaie", "traduit", "signifie", "convention",
    "internationale", "cours", "avec", "sans", "reste", "fidèle",
    "avant", "après", "aussi", "faible", "forte", "capital",
    "capitaux", "actifs", "biens", "services",
}


def is_formula_line(L: str) -> bool:
    """Ligne = ÉQUATION PURE, sans prose. Très conservateur.

    Règles :
      - longueur ≤ 70
      - pas d'item de liste, pas de markdown, pas de `:`
      - contient `=` ou `≈`
      - AUCUN mot de 5+ lettres (donc pas de mot FR courant)
      - au moins 1 char de MATH_SIGNATURE
    """
    if not L or len(L) > 70:
        return False
    if r"\(" in L or r"\[" in L:
        return False
    if re.match(r"^\s*([-*]\s|\d+\.\s)", L):
        return False
    if "**" in L or ":" in L:
        return False
    # `$` = symbole USD dans le contenu, incompatible avec le mode math
    if "$" in L:
        return False
    if not any(c in L for c in "=≈"):
        return False
    # AUCUN mot ≥ 5 lettres
    if re.search(r"[A-Za-zÀ-ÿ]{5,}", L):
        return False
    if not any(c in MATH_SIGNATURE for c in L):
        return False
    return True


def latexify_line(line: str) -> str:
    stripped = line.strip()
    if not is_formula_line(stripped):
        return line
    indent = line[: len(line) - len(line.lstrip())]
    trailing = line[len(line.rstrip()):]
    # retire une éventuelle ponctuation finale hors math
    body = stripped
    tail_punct = ""
    while body and body[-1] in ".;":
        tail_punct = body[-1] + tail_punct
        body = body[:-1]
    return indent + r"\[" + to_latex(body) + r"\]" + tail_punct + trailing


def latexify_text(text: str) -> str:
    return "\n".join(latexify_line(l) for l in text.split("\n"))


ITEM_FIELDS = ("q", "why", "ctx", "shock", "var", "title", "model")


def _latexify_item(it: dict) -> int:
    n = 0
    for k in ITEM_FIELDS:
        v = it.get(k)
        if isinstance(v, str):
            new = latexify_text(v)
            if new != v:
                it[k] = new
                n += 1
    # choices : liste de strings
    if isinstance(it.get("choices"), list):
        new = [latexify_text(c) if isinstance(c, str) else c for c in it["choices"]]
        if new != it["choices"]:
            it["choices"] = new
            n += 1
    # steps : liste de strings
    if isinstance(it.get("steps"), list):
        new = [latexify_text(s) if isinstance(s, str) else s for s in it["steps"]]
        if new != it["steps"]:
            it["steps"] = new
            n += 1
    return n


def main() -> int:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    changed = 0
    # 1) LESSONS
    for cid, lesson in data.get("LESSONS", {}).items():
        for b in lesson.get("blocks", []):
            for k in ("text", "title"):
                v = b.get(k)
                if isinstance(v, str):
                    new = latexify_text(v) if k == "text" else latexify_line(v)
                    if new != v:
                        b[k] = new
                        changed += 1

    # 2) Items par format
    for group in ("QCM", "VF", "SENS", "ORDRE", "OUVERTE"):
        for it in data.get(group, []):
            changed += _latexify_item(it)

    # 3) CHEATSHEET : notations mathématiques (dt/dd)
    cs = data.get("CHEATSHEET", {})
    for section in ("notations", "sigles", "conventions"):
        for e in cs.get(section, []) or []:
            if isinstance(e, dict):
                for k in ("t", "d"):
                    v = e.get(k)
                    if isinstance(v, str):
                        new = latexify_line(v)
                        if new != v:
                            e[k] = new
                            changed += 1

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"latexify: {changed} champ(s) modifié(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
