# Les 12 coups de l'EMI

Jeu mobile de révision d'Économie Monétaire Internationale (L3 Paris 1).
Un seul fichier livré : `index.html`, **généré** par `tools/build.py`.

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

## Cibles

- Safari iOS (iPhone), Chromium desktop.
- Français seul. `T` = objet plat de chaînes (pas d'i18n multi-langue).
- Aucune dépendance runtime hors Google Fonts (Bebas Neue, Lora).
- localStorage : `emi.srs.v1`, `emi.regne.v1`, `emi.settings.v1`.

Voir `SPEC.md` pour le déroulé d'une émission, les 12 catégories et les
formats de question.
