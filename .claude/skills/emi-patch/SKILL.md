---
name: emi-patch
description: >
  Modifier de façon vérifiée le projet `emi-quiz`. `index.html` est
  GÉNÉRÉ par `tools/build.py` — toute édition passe soit par
  `data/data.json` (une question, une catégorie, un bot), soit par
  `src/template.html` (une règle, un style, un rendu), puis par
  `python3 tools/build.py` qui refuse d'écrire si `tools/verify.py`
  échoue. S'active dès qu'un fichier de ce projet est modifié.
---

# emi-patch — la seule voie d'écriture de « Les 12 coups de l'EMI »

`index.html` est un artefact de build. **Ne jamais l'éditer à la
main.** À chaque écriture, `verify.py` vérifie que le fichier est
récupérable, que la banque DATA round-trip contre `data/data.json`,
que le squelette DOM est complet, et que le script passe
`node --check`. Les règles sont dans SPEC §8.2.

## Fichiers concernés

Aucune édition directe autorisée sur :

| Fichier | Qui l'écrit |
|---|---|
| `index.html` | uniquement `tools/build.py` |

Éditables, chacun avec ses garde-fous :

| Fichier | Objet | Contrôle |
|---|---|---|
| `data/data.json` | Contenu (questions, catégories, bots, étoiles) | `verify.py` règle 5 (schéma) + volumes minimums par catégorie (règle 6, warning en v1). Interdit d'utiliser un `trap` hors §10 SPEC. Ids `cat-nnn` uniques. |
| `src/template.html` | Code (HTML/CSS/JS) et marqueur `/*__DATA__*/` | `verify.py` règles 1 (un seul `<script>`), 2 (`node --check`), 4 (ids DOM §7.1 présents), 7 (plancher 95 % de la taille précédente). |
| `tools/*` | Outillage Python | Rien de spécifique — les tests d'usage passent par un build après édition. |

## Procédure d'édition

1. **Lecture avant écriture.** Toujours `Read` le fichier avant `Edit`
   (Claude Code applique déjà ce garde-fou).
2. **Éditer via `Edit`** en fournissant un `old_string` suffisamment
   long pour être **unique** dans le fichier. Ne jamais `Write` un
   fichier entier existant sauf refonte totale.
3. **Build immédiat après édition :**
   ```
   python3 tools/build.py
   ```
   - Sortie stderr : `WARN` (volumes v1) et `ERR` (bloquants).
   - `ok=True` → écriture atomique `index.html.tmp` → `os.rename`.
   - `ok=False` → **aucune** écriture. Corriger, puis rebuild.
4. **Smoke local** avant commit :
   ```
   python3 -m http.server 8000 --bind 127.0.0.1
   # ouvrir http://127.0.0.1:8000/ dans Chrome (Safari iOS pour mobile).
   ```
   Pas d'erreur console attendue. En J6+, `tools/playtest.mjs`
   (Playwright) automatise ce contrôle avec un seed fixé
   (`?seed=42`).
5. **Commit** — un objet par commit : une fonctionnalité, une
   catégorie enrichie, un fix. Le message décrit le **pourquoi**.

## Interdits en dur (les compter fait exit 1 verify)

- Toucher `index.html` à la main.
- Ajouter un `console.error(...)` (SPEC : les erreurs sont des
  exceptions, `pageerror` est l'oracle du playtest J6).
- Utiliser `Math.random()` dans `src/template.html` (SPEC §0 : PRNG
  mulberry32 seedable uniquement). Une occurrence unique en
  commentaire est tolérée.
- Ajouter un `onclick=` inline (SPEC §7.2 : délégation via `data-act`
  et table `ACT`).
- Introduire un `import` ES modules, une dépendance runtime autre que
  Google Fonts, un worker, une clé API.
- Créer une clef `localStorage` en dehors de `emi.srs.v1`,
  `emi.regne.v1`, `emi.settings.v1` (SPEC §5.4).
- Utiliser un `trap` non listé en SPEC §10 (verify règle 5 bloquant).
- Réutiliser un `id` d'item (verify règle 5 bloquant).

## Contrats sur `data/data.json`

- `CATS` : 12 catégories fixes (voir §2 SPEC). On peut renommer un
  libellé, jamais un id (les items pointent dessus).
- `BOTS` : 3 bots exactement en v1 (`newShow` en attend trois).
- Champs communs des items : `id`, `cat`, `ch`, `diff` (1..3), `why`.
- Format qcm : `choices` de longueur 4, `a` ∈ 0..3.
- Format vf : `a` booléen (true / false).
- Format sens : `a` ∈ `up`, `down`, `same`, `ambig` et `ctx`
  non vide.
- Format ordre : `steps` de longueur 3..6.
- Format ouverte : `model` non vide + `points` liste non vide.
- Format etoile : 5 `clues` exactement.

Toute violation → `verify.py` règle 5 → build refusé.

## Contrats sur `src/template.html`

- Un seul `<script>` (verify règle 1). Le marqueur `/*__DATA__*/` est
  remplacé par `const DATA = <json>;`. Ne pas ajouter d'autres
  `<script>` : `verify` refuse.
- `#pupitres`, `#banner`, `#stage`, `#overlay`, `#modal`, `#etoile`,
  `#boot` obligatoires (verify règle 4).
- CSS : ne pas retirer les règles safe-area (`max(20px,var(--sat))`,
  `max(30px,calc(10px + var(--sat)))`), `--pile-bas`, `#banner
  position:relative`, `.btnrow` (premier enfant 100 %),
  `input,textarea` user-select. Voir ARCHITECTURE §2.4 + §10 #B1
  à #B7.
- Aucune fonction dans `S`. Continuations = **chaînes** résolues par
  la table `CONT`. Toute mutation de `S.manche` passe par `endQ()`.
- Un seul goulot de réponse : `answer(payload)`. Toute réponse
  passe par `answer → resolve → render(phase='why') → endQ`.
- Table `ACT` : ajouter une action = ajouter une entrée dans `ACT`
  et un `data-act="xxx"` sur l'élément. Pas de `onclick=`.
- Quand tu supprimes ou renommes une fonction JS, `grep` global
  obligatoire sur `src/template.html` (ARCHITECTURE §10 #B7 :
  `updAIBadge` fantôme).

## Skills à venir

- `emi-questions` (J3) : audit éditorial des banques
  (`strict_dup`, `fuzzy_dup`, `answer_in_question`, `multi_question`,
  `answer_too_long`, `qcm_choice_dup`, `qcm_correct_longest`,
  `sens_no_ctx`, `convention` — cf. SPEC §8.3).
- `emi-playtest` (J6) : Playwright, scenarios `scenario` + `srs` +
  `layout`, captures SHA-256 comparées à `captures/baseline.json`,
  proxy Cloudflare irrelevant (pas d'IA v1).

## Rappel des chemins

```
data/data.json                    ← contenu
src/template.html                 ← code + marqueur /*__DATA__*/
tools/build.py                    ← data + template → index.html (atomique)
tools/verify.py                   ← contrôles bloquants
tools/extract_sources.py          ← pymupdf/python-docx → text/ (git-ignoré)
```

Ce SKILL est vivant : chaque fois qu'un contrat structurel évolue
(nouveau format, nouvelle clef `localStorage`, nouveau `trap`),
**mettre à jour ce fichier dans la même PR**.
