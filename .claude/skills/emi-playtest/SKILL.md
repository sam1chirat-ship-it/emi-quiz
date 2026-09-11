---
name: emi-playtest
description: >
  Validation runtime avant commit dans `emi-quiz` : Playwright sur
  Chromium, serveur `python3 -m http.server` local, trois modes
  (`scenario`, `srs`, `layout`) ou `all`. Captures d'écran hashées
  SHA-256 comparées à `captures/baseline.json` (git-ignoré).
  S'active dès qu'on prépare un commit qui touche `src/template.html`
  ou une catégorie complète de `data/data.json`.
---

# emi-playtest — filet runtime avant commit

## Prérequis

- `npm install` (Playwright core, ~2 packages)
- `npx playwright install chromium` (télécharge Chromium headless
  shell, ~95 Mo, stocké dans `~/Library/Caches/ms-playwright/`)
- Aucun accès réseau externe pendant le test (le jeu n'a pas de
  worker Cloudflare).

## Commandes

```
npm run playtest:all                    # scenario + srs + layout
npm run playtest:scenario               # seul le parcours joueur
npm run playtest:srs                    # seul le test SRS
npm run playtest:layout                 # seul le test mobile
npm run playtest:update                 # all + fige captures/baseline.json
node tools/playtest.mjs all --headed    # non-headless (debug visuel)
node tools/playtest.mjs all --keep-server  # laisse http.server en vie
```

Exit code : `0` si tout passe, `1` si au moins une erreur, `2` si
échec d'infrastructure (Chromium plante, http.server ne démarre pas).

## Ce que teste chaque mode

### `scenario`

Deux parties enchaînées :

1. **`?seed=42&bots=weak`** (bots à 0.1 sur tous les formats) — le
   joueur répond juste à tout. Doit atteindre `screen=bilan` avec
   `phase="victory"` (Maître de midi) ou `phase="over"`. Zéro
   `pageerror`.
2. **`?seed=43&bots=strong`** (bots à 0.9 partout) — le joueur
   répond faux à tout. Doit se faire éliminer (`players[0].out=true`)
   et arriver au bilan `phase="over"`. Zéro `pageerror`.

Captures : `scenario-1-envoi-q1`, `scenario-1-bilan`,
`scenario-2-envoi-q1`, `scenario-2-bilan`.

### `srs`

Sur `?seed=99&bots=strong` : après une mauvaise réponse au premier
qcm, on lit `localStorage.emi.srs.v1` et on vérifie que l'item est
en boîte `0` avec `due <= now`. Aucune interaction plus loin.

### `layout`

Viewport iPhone SE (375×667), safe-area émulée `--sat: 59px`,
`--sab: 34px` injectés en `addStyleTag`.

- Vérifie `padding-top` de `.topbar` ≥ 30 px (SPEC §7.4).
- Vérifie `h1.top` ≥ 20 px (safe-area haute).
- Vérifie que le bouton `Suivant` en phase why est accessible via
  `scrollIntoViewIfNeeded` et complètement dans le viewport après
  scroll, hauteur ≥ 30 px (tactile), visible.

Captures : `layout-topbar`, `layout-why`.

## Captures SHA-256

- Chaque `capture(name)` fait un screenshot, calcule le SHA-256
  (16 hex de tête) et compare à `captures/baseline.json`.
- Trois issues possibles :
  - `NEW` : première fois qu'on rencontre ce nom → ajout à la
    baseline si `--update-baseline` (ou si la baseline n'existe pas
    encore).
  - `match` : identique à la baseline.
  - `CHANGED` : le hash a changé → warning (n'échoue pas le test) ;
    `--update-baseline` fige la nouvelle version.
- `captures/` est **git-ignoré** : chaque contributeur a sa baseline
  locale. Aucune CI multi-machine ne peut comparer sans convention
  supplémentaire.

## Serveur local

`playtest.mjs` lance `python3 -m http.server <port> --bind 127.0.0.1`
sur un port haut choisi via `net.createServer().listen(0)`. Le
serveur est tué en `SIGTERM` à la sortie, sauf `--keep-server`.

## Ce qui n'est PAS testé

- **iPhone réel** — Playwright emule iPhone SE mais ne remplace pas
  un test physique. Toujours vérifier une fois sur Safari mobile
  avant de mettre en prod.
- **Persistance entre sessions** — le test SRS vérifie l'écriture,
  pas la propagation sur une émission ultérieure. À ajouter si
  besoin.
- **Cadence de jeu** — les délais Playwright (`sleep`) sont plus
  courts qu'en usage réel ; ils masquent des glitches temporels
  potentiels (débounce, doubles taps).

## Intégration au flow de commit

Ordre recommandé avant tout `git commit` qui touche `src/template.html`
ou une catégorie complète de `data/data.json` :

```
python3 tools/build.py        # produit index.html + verify
node tools/playtest.mjs all   # non-régression runtime
git add -A && git commit ...
```

Le workflow est le même à chaque étape. La CI peut appeler
`playtest:all` avec des captures baseline stockées ailleurs qu'en
local (ou en désactivant les warnings `CHANGED`).
