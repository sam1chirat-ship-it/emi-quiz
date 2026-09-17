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
    # 6) exposants/indices entre parens (avec parens imbriquées OK) :
    #    `x^(1/(1-\alpha))` → `x^{1/(1-\alpha)}`
    def _wrap_paren_after(s: str, op: str) -> str:
        out = []
        i = 0
        while i < len(s):
            c = s[i]
            if c == op and i + 1 < len(s) and s[i + 1] == "(":
                # trouve la parens fermante balancée
                depth = 1
                j = i + 2
                while j < len(s) and depth > 0:
                    if s[j] == "(":
                        depth += 1
                    elif s[j] == ")":
                        depth -= 1
                    j += 1
                if depth == 0 and (j - (i + 2)) <= 60:
                    out.append(op + "{" + s[i + 2:j - 1] + "}")
                    i = j
                    continue
            out.append(c)
            i += 1
        return "".join(out)

    s = _wrap_paren_after(s, "^")
    s = _wrap_paren_after(s, "_")
    # 7) INDICES LETTRES → droit (\mathrm{}) pour matcher la
    #    convention des manuels : `x^n` reste puissance italique,
    #    `x_A` devient label droit lisible.
    #    Règles :
    #    - `_X` (une majuscule seule) : wrap → label typique (g_A, s_H, L_A)
    #    - `_{ABC}` ou `_{Ab}` (mot commençant par majuscule) : wrap
    #    - `_i`, `_j`, `_k`, `_n`, `_t` (minuscule seule) : LAISSE italique
    #      (indices de sommation / itération, convention math standard)
    #    - `_0`..`_9`, `_{...}` avec macro (\alpha...) : LAISSE tel quel
    def _wrap_sub_content(m: re.Match) -> str:
        content = m.group(1)
        # Skip si contient déjà une macro (\alpha, \mathrm, etc.)
        if "\\" in content:
            return m.group(0)
        # Skip si commence par un chiffre (indice numérique italique)
        if re.match(r"^\d", content):
            return m.group(0)
        # Skip si contient uniquement des opérateurs / expression
        # arithmétique (i+1, t-1, i,j, n-1) : garde italique
        if re.match(r"^[a-z]([\+\-,][a-z0-9]+)+$", content):
            return m.group(0)
        # Toute lettre / label passe en \mathrm
        if re.match(r"^[A-Za-z][A-Za-z0-9]*$", content):
            return "_{\\mathrm{" + content + "}}"
        return m.group(0)

    # cas `_X` (une lettre seule non suivie de lettre) : wrap direct
    s = re.sub(r"_([A-Za-z])(?![A-Za-z{])",
               lambda m: "_{\\mathrm{" + m.group(1) + "}}", s)
    # cas `_{...}` : appliquer la logique
    s = re.sub(r"_\{([^{}]{1,20})\}", _wrap_sub_content, s)
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


MATH_BLOCK_RE = re.compile(r"\\\[([^\[\]]{1,200})\\\]|\\\(([^()]{1,200})\\\)")


def reprocess_math_blocks(text: str) -> str:
    """Applique to_latex à l'intérieur des blocs \[...\] et \(...\) déjà
    présents dans le texte (utile pour ré-appliquer to_latex après une
    évolution du convertisseur, ex. ajout du mathrm sur les indices).
    """
    def _repl(m):
        if m.group(1) is not None:
            return r"\[" + to_latex(m.group(1)) + r"\]"
        return r"\(" + to_latex(m.group(2)) + r"\)"
    return MATH_BLOCK_RE.sub(_repl, text)


# Regex pour repérer des variables inline dans la prose :
#   x_A, g_w, g_n, s_R, \pi_T, k^*, x^2, y*, π* (Unicode)
# On ne match PAS les mots contenant un `_` (file_name, snake_case) :
#   on exige une lettre unique avant le `_` (au sens Unicode BMP),
#   pas précédée d'une autre lettre.
INLINE_MATH_RE = re.compile(
    r"(?<![A-Za-zÀ-ÿ0-9\\])"
    r"([A-Za-zΔΠΣαβγδεηθλμπρστφϕω])"
    r"(?:_(?:[A-Za-z0-9]|\{[^{}]{1,15}\}))+"
    r"(?:\^[*A-Za-z0-9]|\^\{[^{}]{1,15}\})?"
    r"(?![A-Za-zÀ-ÿ])"
)

# Variables Unicode nues qui méritent un rendu math si isolées :
#   `π*`, `i*`, `e^a` en prose.
INLINE_STAR_RE = re.compile(
    r"(?<![A-Za-zÀ-ÿ0-9\\])"
    r"([A-Za-zΔΠΣαβγδεηθλμπρστφϕω])\*"
    r"(?![A-Za-zÀ-ÿ])"
)


def wrap_inline_math(text: str) -> str:
    """Enveloppe les micro-formules inline dans la prose : `g_A` → `\(g_A\)`.

    Applique to_latex à chaque match pour la mise en \mathrm des indices.
    Idempotent : ignore les matches déjà à l'intérieur d'un `\(…\)` ou `\[…\]`.
    """
    # Découpage : on skip les blocs déjà math
    parts = []
    i = 0
    n = len(text)
    while i < n:
        # cherche prochain \[ ou \(
        p_bracket = text.find(r"\[", i)
        p_paren = text.find(r"\(", i)
        candidates = [x for x in (p_bracket, p_paren) if x >= 0]
        nx = min(candidates) if candidates else -1
        if nx < 0:
            parts.append(_wrap_prose(text[i:]))
            break
        parts.append(_wrap_prose(text[i:nx]))
        # trouve fin de bloc
        close = r"\]" if nx == p_bracket else r"\)"
        end = text.find(close, nx + 2)
        if end < 0:
            parts.append(text[i:])
            break
        parts.append(text[nx:end + 2])
        i = end + 2
    return "".join(parts)


def _wrap_prose(prose: str) -> str:
    def _inline_repl(m: re.Match) -> str:
        return "\\(" + to_latex(m.group(0)) + "\\)"

    def _star_repl(m: re.Match) -> str:
        return "\\(" + to_latex(m.group(1) + "*") + "\\)"

    prose = INLINE_MATH_RE.sub(_inline_repl, prose)
    prose = INLINE_STAR_RE.sub(_star_repl, prose)
    return prose


def latexify_text(text: str) -> str:
    # 1) ré-applique to_latex sur les blocs existants (idempotent)
    text = reprocess_math_blocks(text)
    # 2) enveloppe les micro-formules inline
    text = wrap_inline_math(text)
    # 3) puis passe ligne-formule complète
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
