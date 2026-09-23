# NOTES J1 — hypothèses et décisions

Ce fichier ne remplace pas SPEC.md. Il consigne les points où SPEC laisse
un choix ouvert, ou une décision technique de J1 à valider plus tard.

## Décisions J1

### 1. Seed par défaut du PRNG
- `?seed=NNN` → mulberry32(NNN).
- Sans `?seed=`, on ne peut pas appeler `Math.random` (interdit par le
  cadrage). Seed initial construit **une seule fois au boot** par :
  `Date.now() ^ ((performance.now()*1000)|0) ^ (crypto.getRandomValues(new Uint32Array(1))[0])`.
  Journalisé au démarrage dans `console.log` (pas `console.error`). Une fois
  le PRNG semé, aucun appel à `Math.random` nulle part.

### 2. Bots pendant le coup d'envoi en J1 (sans duels)
- Bots « répondent » (tirage PRNG vs `bot.acc[format]`) après chaque
  question du joueur. Leur feu avance sur les mauvaises réponses,
  purement visuel — le rouge ne déclenche rien tant que la logique de
  duel n'est pas là (J2). Cela permet de tester la table de rendu des
  pupitres dès J1 et évite un refactor de `resolve()` à J2.

### 3. Fin de manche « Fin J1 »
- Après 8 questions du coup d'envoi (ou banque épuisée), l'écran passe
  à `screen: "bilan"` version dégradée : titre « Fin de la manche
  (coup d'envoi) », score du joueur, bouton « Rejouer » qui remet à
  `screen: "setup"`. Pas de duel de fin de manche, pas de liste
  d'erreurs détaillée — ça arrive J2 avec le vrai bilan.

### 4. Répartition des 40 items sur 12 catégories
- 20 qcm + 20 vf = 40. Cible « ≥ 3 par catégorie ».
- Répartition : 4 catégories à 4 items (2 qcm + 2 vf) et 8 catégories
  à 3 items (répartis 1-2 ou 2-1 selon la pertinence pédagogique).
- Priorité aux catégories qu'on peut tomber dans les 8 premières
  questions du coup d'envoi : `bdp`, `pen`, `si`, `forex`, `cot`,
  `tcr`, `smi`, `parite` (les 8 premiers chapitres) reçoivent au moins
  3 items chacun ; `monet`, `depr`, `equil`, `mf` complètent.

### 5. SRS J1 — version minimale
- `pickDue(fmt, cats)` : filtre par format ET par catégories cochées,
  échus (`due ≤ now`) triés par `box` croissant, puis jamais vus, puis
  les autres par `due` croissant. **Pas de pondération par faiblesse
  de catégorie en J1** (SPEC §5.2 step 3, à J2).
- Boîtes 0-4, intervalles `[0, 1, 2, 4, 7]` jours (§5.1 SPEC).
- Réponse correcte : `box+1` (max 4), `due = now + interval[box]`.
- Réponse fausse : `box = 0`, `due = now`.
- « Coup bas » : pas en J1 (Coup par coup = J3).

### 6. Absence de duels en J1
- `S.duel = null` en permanence, `S.after = null`, table `CONT` définie
  mais vide (juste `nextQ` et `endManche`). Structure prête sans code
  actif. Aucun test de feu rouge en J1 : les bots peuvent passer au
  rouge visuellement, ça ne casse rien.

### 7. Fond de scène et pupitres
- 4 pupitres visibles dès le coup d'envoi (joueur + 3 bots), pas de
  `.out` en J1.
- Feux : 3 pastilles rendues par pupitre, colorisées selon `p.feu ∈
  {0,1,2}`. Passage au rouge : bordure du pupitre, pas plus.
- Animation score (`animScore`, `PREV`) portée depuis Bamboozled J2 —
  en J1 le score est mis à jour sans animation particulière (setter
  simple), mais les hooks (`PREV`, `.pod.win/lose`) sont préparés.

### 8. Extraction des sources
- Faite après le squelette et avant l'écriture de `data/data.json`
  (méthode du cadrage). Sortie `text/` (git-ignoré), un fichier `.txt`
  par source, index dans `text/INDEX.md`.
- Aucun contenu de source n'est encodé dans le code ; seule
  `data/data.json` porte le contenu utilisateur.

### 9. Validation runtime en J1
- `python3 tools/build.py` refuse d'écrire si `verify.py` échoue.
- `node --check` sur le script extrait fait partie de verify.
- Pas de Playwright en J1 (ce sera J6). Smoke manuel via
  `python3 -m http.server` + Chrome. Absence d'erreur console
  vérifiée à l'œil sur `Coup d'envoi` complet en J1.

### 10. Convention `--pile-bas` en J1
- Pas de bloc fixe en bas d'écran en J1. `--pile-bas` initialisée à
  `0px`, un `ResizeObserver` prêt à observer un élément `#pilebas` si
  ajouté plus tard. Le padding-bottom de `#stage` reste
  `calc(var(--pile-bas) + 24px)` — 24 px minimum sans bloc du bas.

## Points en attente (à trancher lors de leurs livrables)

- J2 : format exact du bilan complet (§1.9), animation entrée/sortie
  des pupitres éliminés.
- J3 : UX du « coup bas » (bouton dédié ou geste ?).
- J4 : distance visuelle entre les deux horloges du coup fatal.
- J5 : mise en page de l'étoile (5 secteurs animés → révélation
  progressive).
- J6 : baseline captures Playwright, seed retenu pour le scenario.

## Contradictions ou ambiguïtés relevées

Aucune à ce jour entre SPEC.md et les sources.

## Faits périssables détectés

Aucun — le cours d'EMI est théorique, pas de références datées à
« actuellement » ou de records mondiaux dans le programme.

## Idées à programmer (J7+)

### Cheat sheet (J10 pressenti)

Page « glossaire » accessible depuis la topbar (à côté de PALMARÈS ?)
pour dépanner le jargon EMI. Contenu à assembler à partir des
`notations` déjà présentes dans les items `ouverte` (déjà 30 items
qui portent leurs propres notations, source gratuite).

- Sigles : PPA, PNCTI, PCTI, TCR, TCEN, TCER, TCEF, FEER, PEN, CC,
  CF, TC, EO, IDE, IS, LM, BC, PTM, ML, BS…
- Notations : `e` (log au certain), `E` (niveau), `eᵃ` (anticipation),
  `S_C` / `S_I` (certain / incertain), `i`, `i*`, `π`, `π*`, `Ms`,
  `f` (taux à terme), `q` (log TCER), `ω_i` (poids), `ρ` (prime de
  risque), `ε_X`, `ε_M`.
- Conventions du cours (à surligner) : CF > 0 = sortie ; e au certain ;
  ΔPEN = CC hors valorisation ; ML : ε_X + ε_M > 1 ; PNCTI :
  e = eᵃ + (i − i*).

UX possible : modal plein écran (comme #etoile) déclenché par
`data-act="cheatsheet"`, structure en 3 blocs (sigles / notations /
conventions), champ recherche en haut (filtrage par `norm()` sur la
liste).

Source de données : nouveau champ `CHEATSHEET` dans `data.json`
(ajouté au verify), ou construction automatique par un
`tools/build_cheatsheet.py` qui parcourt les `notations` de OUVERTE
+ dictionnaire fixe pour les sigles.

## Banque et marché (mbf) — contradictions entre sources (J42)

Relevées sans être tranchées par ma mémoire ; les items suivent la source indiquée.

1. **Seuil d'Arcand, Berkes & Panizza.** 110 % du crédit privé / PIB dans les
   diapos (chap. 2), la note VoxEU (2011) et Boucher et al. (chap. 5).
   Carré & L'Oeillet (2017) écrivent « autour d'un ratio crédit/PIB de
   80 %-100 % » ; Cournède & Denk (OCDE) ≈ 100 %. Items : 110 %, avec le
   piège signalé dans le cours `arcand`.
2. **Date de Bâle 2.** Diapos chap. 4 : « Bâle 2 signés en 2003 » puis
   « accords signés en 2004 ». Le partiel de janvier 2026 (Q57) écrit 2004 :
   retenu 2004.
3. **Bhattacharya & Jacklin.** Diapos chap. 1 : « Battacharya et Jackling
   (1986) » puis « Battacharya et Jacklin (1988) ». Retenu 1988 (graphie
   Bhattacharya & Jacklin).
4. **Modèles internes.** Diapos : Bâle 2 (accords de 2004) autorise les
   modèles internes ; Boucher et al. : « dès 1996 » (amendement risques de
   marché). Items : modèles internes = Bâle 2, la date 1996 citée en
   explication seulement.

## Banque et marché — faits datés conservés

Le partiel interroge des rapports datés (FSB déc. 2025, Banking on Climate
Chaos 2022, Banking on Business as Usual 2025, prix de la Banque de Suède
2022). Ces items sont ancrés sur leur source et leur date (« d'après le
rapport X de … ») : ils restent vrais pour cette source, mais audit.py les
signale en « perishable » (avertissement non bloquant).
