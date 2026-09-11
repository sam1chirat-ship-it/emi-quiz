# Les 12 coups de l'EMI

Jeu mobile de révision d'Économie Monétaire Internationale (L3 Paris 1).
Un seul fichier livré : `index.html`, **généré** par `tools/build.py`.

- **En ligne** : https://sam1chirat-ship-it.github.io/emi-quiz/
- **Repo** : https://github.com/sam1chirat-ship-it/emi-quiz

## Structure

```
emi-quiz/
  index.html            ← GÉNÉRÉ, committé (déploiement statique)
  src/template.html     ← code source (HTML + CSS + JS) avec marqueur /*__DATA__*/
  data/data.json        ← CATS, BOTS, QCM, VF, SENS, ORDRE, OUVERTE, ETOILE
  tools/
    build.py            ← data.json + template → index.html (atomique)
    verify.py           ← contrôles bloquants avant écriture
  .claude/skills/       ← garde-fous éditoriaux (emi-patch, à venir)
  sources/              ← cours, fiches, TD, sujets — SEULE source autorisée
  SPEC.md               ← contrat fonctionnel (§1 à §10)
  ARCHITECTURE.md       ← doc du prédécesseur Bamboozled (référence)
  NOTES.md              ← hypothèses de session
```

## Édition

- Une question → `data/data.json`.
- Une règle, un style, un rendu → `src/template.html`.
- Ne **jamais** éditer `index.html` à la main. `build.py` le régénère
  et `verify.py` refuse toute écriture invalide (script cassé, DATA non
  parsable, squelette DOM incomplet, taille suspecte).

## Build

```
python3 tools/build.py
```

Écrit `index.html.tmp`, valide, puis renomme atomiquement.

## Lancement local

```
python3 -m http.server 8000 --bind 127.0.0.1
# puis ouvrir http://127.0.0.1:8000/
```

Ajouter `?seed=42` pour figer le PRNG (déterministe, utile pour reproduire un bug).
`?bots=weak` (acc 0.1) ou `?bots=strong` (acc 0.9) surcharge les bots pour tests / réglage.

## Playtest (Playwright)

Une seule fois pour installer les navigateurs headless :

```
npm install
npx playwright install chromium
```

Puis les 3 modes de test (SPEC §8.4) :

```
npm run playtest:scenario     # parcours joueur juste + joueur faux
npm run playtest:srs          # boîte 0 après mauvaise réponse
npm run playtest:layout       # safe-area et bouton Suivant iPhone SE
npm run playtest:all          # les trois
npm run playtest:update       # fige captures/baseline.json (git-ignoré)
```

## Déploiement GitHub Pages

`index.html` est déjà à la racine, committé sur `main`. Sur GitHub :

1. Push le repo : `git remote add origin git@github.com:<user>/emi-quiz.git && git push -u origin main`
2. Réglages → Pages → Source `Deploy from a branch`, branche `main`, dossier `/ (root)`, Save.
3. L'URL de production `https://<user>.github.io/emi-quiz/` apparaît en quelques minutes.

Aucun build côté GitHub : ils servent le `index.html` tel qu'il est.

## Cibles

- Safari iOS (iPhone), Chromium desktop.
- Français seul. `T` = objet plat de chaînes (pas d'i18n multi-langue).
- Aucune dépendance runtime hors Google Fonts (Bebas Neue, Lora).
- localStorage : `emi.srs.v1`, `emi.regne.v1`, `emi.settings.v1`.

Voir `SPEC.md` pour le déroulé d'une émission, les 12 catégories et les
formats de question.
