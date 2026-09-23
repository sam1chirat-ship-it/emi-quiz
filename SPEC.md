# « Les 12 coups de l'EMI » — Spécification v1

Titre provisoire. Jeu mobile de révision d'Économie Monétaire Internationale (L3 Paris 1),
solo, calqué sur le déroulé des *12 coups de midi*, construit sur la structure technique de
Bamboozled (`ARCHITECTURE.md`) avec les corrections listées en §8.

---

## 0. Décisions

| Sujet | Décision |
|---|---|
| Concept | Une **émission** = une partie de ~12 min : le joueur affronte 3 candidats simulés (bots) sur 5 manches, puis revient le lendemain défendre son titre de Maître. |
| Contenu | 6 chapitres du cours, découpés en **12 catégories** (§2). Chaque question annonce sa catégorie ; le setup permet de cocher/décocher les catégories. |
| Formats | Les 6 formats : `qcm`, `vf`, `sens`, `ordre`, `calc` (généré), `ouverte` (auto-évaluée) + `etoile`. Chaque manche a ses formats (§1.4). |
| Échéance | Examen dans < 3 semaines → v1 jouable en 6-7 jours (§9), banque enrichie ensuite. |
| Langue | Français seul. `T` reste un objet unique de chaînes (pas d'`I18N` multi-langue). |
| IA | **Aucune en v1.** Conventions propres au cours (compte financier > 0 = sortie nette de capitaux ; `e` = taux au certain en log ; `i = i* − (eᵃ − e)`) trop faciles à contredire. Pas de worker, pas de clé API. |
| Distribution | `index.html` unique déployé sur GitHub Pages, **généré** par `tools/build.py` depuis `src/template.html` + `data/data.json` (§8.1). |

**Repris de Bamboozled tel quel** : couche mobile (§2.4 de `ARCHITECTURE.md` intégral), état global `S` + `render()` unique + goulot `endQ()`, export/import JSON, `norm()` et le portail de saisie libre (pour l'étoile), boot IIFE, `springTo`, bandeau dans le flux, son WebAudio + haptique.

**Abandonné** : `DATA` mono-ligne éditée en place (remplacée par `data.json`), `SEEN` « jamais deux fois » (remplacé par la répétition espacée), le plancher 300 Ko, les scènes de jeu, `#logwrap` fixe, la clé API, les alias CSS rétro-compat, `--banner-max-h`.

---

## 1. Déroulé d'une émission

### 1.1 Candidats

Quatre pupitres : le joueur + trois bots (`DATA.BOTS`, Annexe A). Chaque pupitre porte un
**feu** : vert → orange (1re erreur) → rouge (2e erreur). Passer au rouge déclenche un duel.

### 1.2 Règle commune à chaque question

1. La question annonce sa catégorie et son format, puis s'affiche.
2. Le joueur répond. Chaque bot « répond » par tirage PRNG contre `bot.acc[format]`.
3. Bonne réponse : `+pts(format) × combo` (combo = 1, 1.5 à partir de 3 bonnes d'affilée). Mauvaise : le feu avance, combo = 1, la question retombe en boîte 0 (§5).
4. Après chaque réponse, l'explication (`why`) s'affiche, même en cas de bonne réponse — c'est là qu'on révise.

### 1.3 Duels et éliminations

- **Rouge** → duel immédiat contre le candidat au score le plus bas (hors le rouge). Duel = 3 questions `sens`, premier à 2 bonnes ; égalité 1-1 après 3 → mort subite. Le perdant est éliminé ; les feux des survivants repassent au vert.
- **Fin de manche sans rouge** : le dernier au score est en danger. Si c'est un bot → éliminé directement. Si c'est le joueur → duel contre l'avant-dernier. **Le joueur n'est jamais éliminé sans duel.**
- **Joueur éliminé** → l'émission s'arrête, écran **Bilan** (§1.9). Le règne, s'il y en avait un, prend fin.

### 1.4 Les manches

| Manche | Candidats | Longueur | Formats | Points |
|---|---|---|---|---|
| **Coup d'envoi** | 4 | 8 questions max | `qcm`, `vf` | 100 |
| **Coup par coup** | 3 | 6 questions max | `sens`, `ordre` | 150 / 200 |
| **Coup fatal** | 2 | chrono 90 s chacun | `calc`, `qcm` à 3 choix | pas de points : on joue le titre |
| **Coup de maître** | 1 | 5 questions | `ouverte` | paliers 1 → 10 → 100 → 1 000 → 10 000 |
| **Étoile mystérieuse** | 1 | 1 proposition | `etoile` | palmarès |

**Coup par coup — le coup bas.** Une fois par manche, le joueur peut passer une question à un bot. La question est **marquée « à revoir »** (boîte 0, échue) : éviter a un coût pédagogique, pas seulement stratégique.

### 1.5 Coup fatal (chrono)

Deux horloges de 90 s. La question s'affiche pour le candidat dont c'est le tour, son horloge tourne.

- Bonne réponse → son horloge se fige, au tour de l'adversaire.
- Mauvaise réponse → il garde la main, nouvelle question, l'horloge continue.
- Le bot « réfléchit » `rand(4, 12)` s puis répond selon `acc`.
- Horloge à 0 → perdu. Le vainqueur est **Maître de midi**.

Formats : `calc` généré (§4) et `qcm` réduit à 3 propositions (on retire un distracteur au hasard, jamais le `trap`).

### 1.6 Coup de maître

Cinq questions `ouverte` (type examen). Pour chacune :

1. Énoncé + chrono 45 s **indicatif** (pas bloquant — l'examen est chronométré, la révision non).
2. Bouton « Voir la réponse » → réponse-modèle + liste des éléments attendus (`points`) + notations à préciser (`notations`).
3. Auto-évaluation : **Su** (palier +1) / **À moitié** (on continue, pas de palier) / **Pas su** (fin du coup de maître, cagnotte figée au palier atteint).

5 « Su » = coup de maître réussi → accès à l'étoile. La cagnotte de l'émission s'ajoute à celle du règne.

### 1.7 Étoile mystérieuse

Un concept du cours à deviner (Feldstein-Horioka, surajustement de Dornbusch, paradoxe de Triffin, TCEF…). Cinq indices, du plus vague au plus précis.

- Chaque coup de maître réussi révèle **un indice de plus** et donne **une seule proposition** (saisie libre, `norm()` + `aliases`).
- Trouvée → gravée au palmarès du règne, nouvelle étoile tirée. Ratée → même étoile à la prochaine émission, indices conservés.

### 1.8 Le règne (persistant)

`emi.regne.v1` : `{ maitre:Boolean, jours:Number, cagnotte:Number, etoile:{id, indices:Number}, palmares:[{jours, cagnotte, etoiles}] }`.

- Vainqueur du coup fatal → `maitre=true`, `jours+1`. Au setup suivant : « Jour N du règne, cagnotte X ».
- Joueur éliminé → le règne est archivé dans `palmares` (5 meilleurs), `maitre=false`, `jours=0`, `cagnotte=0`. L'étoile en cours est conservée.

### 1.9 Bilan (fin d'émission ou élimination)

- Chaque erreur de l'émission : question, ta réponse, la bonne, `why`.
- Jauges par catégorie (§5.3), liste « à revoir ».
- Boutons : Rejouer / Exporter.

### 1.10 Émission express (v1.1)

Même déroulé, 4 / 3 / 60 s / 3 questions. Pas dans la v1.

---

## 2. Catégories

Chaque entrée de `CATS` porte un champ `mat` (chaîne, `"emi"`, `"croissance"` ou `"mbf"` — Banque et marché, libellé affiché via `T.mats`). Le setup filtre par **matière** avant de filtrer par **catégorie** (si une seule matière est présente dans la banque, l'étape est transparente ; la structure est prête pour les deux matières simultanément).

| id | Catégorie | ch | Contenu |
|---|---|---|---|
| `bdp` | Balance des paiements | 1 | Comptes, signes, identité TC + CC − CF + EO = 0, capacité/besoin de financement, lecture d'un tableau |
| `pen` | Position extérieure nette | 1 | Stock vs flux, équation d'accumulation, effets de valorisation |
| `si` | Épargne-investissement & paradoxes | 1 | (S−I)+(T−G)=(X−M), Feldstein-Horioka, Lucas, zone euro, de jure / de facto |
| `forex` | Marché des changes | 2 | OTC, monnaie véhiculaire, spot / terme / swap / option, couverture exportateur vs importateur |
| `cot` | Cotation & taux croisés | 2 | Certain / incertain, `S_I = 1/S_C`, arbitrage triangulaire |
| `tcr` | Taux effectifs & taux de change réel | 2 | TCEN, TCER = TCEN × P/P*, variation log-linéarisée, lecture compétitivité / pouvoir d'achat |
| `smi` | SMI & régimes de change | 2 | Étalon-or, Bretton Woods, Triffin, monnaie internationale, typologie fixe → flottant |
| `parite` | Parités de taux d'intérêt | 3 | PCTI, PNCTI, PNCTIR, horizon, niveau vs log, sens du signe |
| `monet` | Modèles monétaires | 3 | Prix flexibles (Frenkel), Dornbusch, Meese-Rogoff, guerre des monnaies |
| `depr` | Dépréciation & balance commerciale | 4 | Effets volume / valeur, Marshall-Lerner, courbe en J, pricing to market, AS-AD, échangeables / non échangeables, allocation intertemporelle |
| `equil` | Change d'équilibre | 5 | PPA absolue / relative, Balassa-Samuelson (toutes les étapes), TCEF, TCEC |
| `mf` | Mundell-Fleming & politiques de change | 6 | Triangle d'incompatibilité, fixe / flexible × mobilité, interventions stérilisées, statique comparative |

---

## 3. Formats et schémas (`data/data.json`)

Champs communs à tout item : `id` (stable, ex. `bdp-012` — **jamais un hash du texte**, pour que la SRS survive aux corrections de formulation), `mat` (chaîne — matière ; `"emi"`, `"croissance"` ou `"mbf"`, présent sur chaque item), `cat`, `ch`, `diff` (1-3), `why` (explication courte, obligatoire), `trap` (optionnel : quelle confusion classique la question teste, cf. §10).

### `qcm`
```json
{"id":"parite-003","cat":"parite","ch":3,"diff":2,
 "q":"Sous la PNCTI (e = taux au certain en log), une hausse surprise de i, à eᵃ donné, provoque :",
 "choices":["une appréciation immédiate de e","une dépréciation immédiate de e","aucun effet sur e, seulement sur f","une hausse de i*"],
 "a":0,"trap":"sens-parite",
 "why":"i = i* − (eᵃ − e) ⇒ e = eᵃ + (i − i*). À anticipation donnée, i↑ ⇒ e↑ : appréciation immédiate."}
```
Toujours 4 `choices`, `a` = indice de la bonne. Les distracteurs viennent des confusions du prof (§10), pas du hasard.

### `qcmm` — QCM à réponses multiples, à réservoirs (Banque et marché)
Format du partiel de Banque et marché : plusieurs propositions justes, notation tout ou rien. Pour que la même notion revienne formulée autrement à chaque passage, l'item stocke des **réservoirs** :
```json
{"id":"diamond84-001","mat":"mbf","cat":"diamond84","ch":1,"diff":2,
 "q":["Dans Diamond (1984), la banque est :","Selon Diamond (1984), l'intermédiaire bancaire se justifie comme :"],
 "ok":["un contrôleur délégué","une réponse à l'aléa moral ex post", "…"],
 "ko":["un assureur de liquidité","une réponse à la sélection adverse ex ante", "…"],
 "koWhy":["C'est Diamond-Dybvig (1983).","C'est Leland-Pyle (1977).", "…"],
 "trap":"auteur-role","why":"…"}
```
`q` : une formulation ou une liste ; `ok` ≥ 2 propositions justes ; `ko` ≥ 3 distracteurs ; `koWhy` optionnel, aligné sur `ko`. À l'affichage (`materializeQcmm`) : 1 à 3 justes + distracteurs, 4 ou 5 choix, mélangés au PRNG ; `S.q` reçoit la version figée (`choices`, `good`), l'id ne change pas (SRS). Au coup fatal, un qcmm se réduit à 1 juste + 2 fausses (`qcmmToQcm3`). En coup d'envoi, `qcmm` remplace `qcm` quand la matière en possède.

**Variantes de formulation (tous formats texte)** : `q` d'un `qcm`, `vf`, `ouverte` peut aussi être une liste de formulations équivalentes ; une est tirée à l'affichage. Un item sans liste ne consomme pas le PRNG (rendus EMI/croissance inchangés).

### `vf`
```json
{"id":"bdp-004","cat":"bdp","ch":1,"diff":1,
 "q":"Une hausse des réserves officielles apparaît avec un signe positif dans le compte financier.",
 "a":true,"trap":"signe-bdp",
 "why":"Hausse des réserves ⇔ sortie nette de capitaux ⇔ solde financier positif (convention du cours)."}
```

### `sens`
```json
{"id":"mf-007","cat":"mf","ch":6,"diff":2,
 "ctx":"Mundell-Fleming, change flexible, mobilité parfaite des capitaux",
 "shock":"Hausse des dépenses publiques",
 "var":"Production Y",
 "a":"same","trap":"mf-regime",
 "why":"G↑ ⇒ i↑ ⇒ entrées de capitaux ⇒ appréciation ⇒ X−M↓ : éviction totale, Y inchangé."}
```
`a` ∈ `up` | `down` | `same` | `ambig`. Quatre boutons fixes ↑ ↓ = ?

### `ordre`
```json
{"id":"equil-002","cat":"equil","ch":5,"diff":2,
 "title":"Effet Balassa-Samuelson : remettre les étapes dans l'ordre",
 "steps":["Gains de productivité dans le secteur échangeable","Hausse des salaires dans l'échangeable","Contagion des salaires au secteur abrité (marché du travail unique)","Hausse des prix des non-échangeables","Hausse du niveau général des prix ⇒ appréciation réelle"],
 "why":"Le prof exige toutes les étapes : la contagion salariale est celle qu'on oublie."}
```
`steps` dans le bon ordre (3 à 6) ; l'UI les mélange (PRNG) et le joueur tapote dans l'ordre. Bon = ordre exact.

### `calc` — voir §4 (généré, pas stocké).

### `ouverte`
```json
{"id":"tcr-010","cat":"tcr","ch":2,"diff":2,
 "q":"Qu'appelle-t-on taux de change effectif nominal ? Écrire la formule en précisant soigneusement les notations.",
 "model":"Moyenne pondérée des taux de change bilatéraux au certain, les poids étant les parts des partenaires dans le commerce extérieur. En log : e_eff = Σᵢ ωᵢ eᵢ, Σ ωᵢ = 1. En niveau : moyenne géométrique.",
 "points":["moyenne pondérée","poids = parts commerciales","bilatéraux au certain","log = arithmétique / niveau = géométrique"],
 "notations":["e ou E (log ou niveau)","certain ou incertain","ωᵢ"]}
```

### `etoile`
```json
{"id":"et-03","name":"Paradoxe de Feldstein-Horioka","aliases":["feldstein horioka","feldstein-horioka","fh"],
 "clues":["Je date de 1980.","Je contredis la mobilité parfaite des capitaux.","Je porte deux noms.","Je compare épargne et investissement nationaux.","Je constate qu'ils restent fortement corrélés."]}
```

### Volumes cibles

| Format | v1 (J6) | Cible |
|---|---|---|
| `qcm` | 90 | 150 |
| `vf` | 60 | 100 |
| `sens` | 60 | 100 |
| `ordre` | 15 | 25 |
| `ouverte` | 30 | 50 |
| `etoile` | 12 | 25 |
| `calc` | 6 générateurs | 8 |

Répartition minimale par catégorie : 6 `qcm`, 4 `vf`, 4 `sens`, 1 `ordre`, 2 `ouverte`. Sources : fiches chap. 1-5, récap (chap. 6), sujet 2023-24 + corrigé, CC1, TD1, TD7, diapos « erreurs fréquentes ».

---

## 4. Générateurs `calc`

Fonctions JS `GEN[name](rng) → {q, choices, a, why}`. Contrainte : **faisable de tête** (l'examen interdit la calculatrice) — chiffres ronds, une seule opération non triviale.

| name | Ce qu'on calcule | Distracteurs |
|---|---|---|
| `cross` | Taux croisé au certain à partir de deux cotations à l'incertain (ex. 1 USD = 100 JPY, 1 USD = 0,8 EUR ⇒ 1 EUR = 125 JPY) | inverse (0,008), produit (80), mauvais sens (1,25) |
| `varTCR` | Variation du TCR : ΔE + (π − π*) | oubli de l'inflation, signe inversé, π* − π |
| `neer` | Variation du TCEN : Σ ωᵢ Δeᵢ (2 partenaires) | moyenne non pondérée, somme brute, un seul partenaire |
| `bdp` | Solde d'un compte à partir de crédits/débits (biens + services) | oubli des services, signe, inversion crédit/débit |
| `capfin` | Capacité (besoin) de financement = TC + CC, et sens des flux de capitaux | TC seul, TC − CC, signe du CF |
| `uip` | e = eᵃ + (i − i*) sur un horizon (annualisé → trimestriel) | oubli de l'horizon, signe, ratio au lieu de différence |

`why` est construit avec les chiffres tirés (pas de texte fixe). Le PRNG est seedable (`?seed=`) — mulberry32, remplace `Math.random` partout dans le jeu.

---

## 5. Répétition espacée et persistance

### 5.1 `emi.srs.v1` — SM-2 ou FSRS-4.5 (J38, choix au setup)
Deux algorithmes, au choix du joueur (`settings.srsAlgo`, SM-2 par défaut). Chaque carte porte son `algo` ; changer de réglage migre la carte à la volée au prochain passage (les anciennes cartes à boîtes `{box, ok, ko}` sont migrées aussi).
```
SM-2 : { "<id>": { "algo":"sm2",  "due":<ms>, "last":<ms>, "reps":N, "lapses":N, "ef":≥1.3, "interval":jours } }
FSRS : { "<id>": { "algo":"fsrs", "due":<ms>, "last":<ms>, "reps":N, "lapses":N, "S":stabilité, "D":1..10, "state":"new|learning|review|relearning" } }
```
Note sur l'échelle SM-2 (0-5) : bonne réponse → 4, mauvaise → 1 ; coup de maître : Su → 4, À moitié → 3, Pas su → 1. FSRS reçoit la note convertie ({0,1} → Again, 2 → Hard, 3-4 → Good, 5 → Easy), rétention cible 90 %, 17 poids par défaut de FSRS-4.5.
- **SM-2** : échec → `reps = 0`, intervalle 1 jour ; succès → 1, puis 6 jours, puis `intervalle × ef` ; `ef` ajusté à chaque note (plancher 1,3).
- **FSRS** : stabilité S et difficulté D mises à jour selon la rétention estimée ; intervalle ≈ S jours.

**Maîtrisé** (`isMastered`) : SM-2 `reps ≥ 2` et intervalle ≥ 4 jours ; FSRS `state = review` et S ≥ 4.

### 5.2 Tirage — `pickDue(format, cats)`
1. Candidats = items du format, de la matière courante, dans les catégories cochées, non encore posés dans l'émission. Si tous ont été posés : on ignore le filtre « non posés » (log une seule fois, `S.warned[format]`). `null` seulement si le format n'a aucun item dans ces catégories (l'appelant bascule alors sur un autre format).
2. Paliers : échus (`due ≤ now`) → jamais vus → autres. On prend le premier palier non vide.
3. Dans ce palier, seuls les ex æquo restent en lice : échus → clé de maîtrise minimale (`reps` en SM-2, ⌊S⌋ en FSRS) ; autres → même jour d'échéance le plus proche ; jamais vus → tous.
4. Tirage PRNG pondéré par la faiblesse de la catégorie : poids = 1 + part des items de la catégorie (tous formats) non maîtrisés, jamais vus compris (∈ [1, 2]).

### 5.3 Jauge de catégorie
Part des items de la catégorie **maîtrisés** (`isMastered`). Affichée au setup et au bilan.

### 5.4 Autres clefs
- `emi.regne.v1` (§1.8).
- `emi.settings.v1` : `{ mat, cats:[ids], sfx:Boolean, express:Boolean, srsAlgo:"sm2"|"fsrs" }`.
- Rien d'autre. L'émission en cours n'est pas sauvegardée : `exportGame()` / `importGame()` (format `{version:1, ts, S, SRS, REGNE}`) sont le seul moyen d'y revenir.

### 5.5 Export / import
Identique à Bamboozled. `S` ne contient **aucune fonction** (§6.1) : l'export est fidèle à tout moment, duel compris.

---

## 6. État et machine à états

### 6.1 `S` (construit par `newShow(settings)`)
```
S = {
  screen: "setup" | "show" | "bilan" | "palmares",
  manche: "envoi" | "cpc" | "fatal" | "maitre" | "etoile",
  phase:  "intro" | "q" | "why" | "duel" | "elim" | "clock" | "reveal" | "guess",
  players: [ {name, bot:false, score, feu:0..2, combo, out:false},
             {name, bot:true, acc:{…}, score, feu, out}, … ],   // index 0 = joueur
  cur:    Number,          // qui a la main (coup fatal) — toujours 0 ailleurs
  q:      Item | null,     // question courante (objet DATA ou sortie de GEN)
  qFmt:   String,
  qIdx:   Number,          // n° de question dans la manche
  asked:  [ids],           // posés dans l'émission
  answered: { choice, ok } | null,
  duel:   { a, b, wins:[0,0], n } | null,        // pas de closure : "after" = "endManche"|"nextQ"
  after:  "nextQ" | "endManche" | null,          // continuation du duel, résolue par table
  clocks: [ms, ms] | null, // coup fatal
  coupBas: Boolean,        // disponible cette manche
  maitre: { n, su, palier } | null,
  cagnotte: Number,
  errors: [ {id, fmt, given, ok:false} ],       // pour le bilan
  log:    [String],        // 30 dernières entrées
  warned: {},
  timer, timerMax,
  seed:   Number,
}
```
Toutes les valeurs sont initialisées dans `newShow` (aucun champ optionnel). Les continuations sont des **chaînes** résolues par `CONT = { nextQ, endManche }`.

### 6.2 `screen`
```
setup ──newShow()──▶ show ──joueur éliminé / étoile jouée / coup de maître fini──▶ bilan ──▶ setup
                                                                                     └──▶ palmares ──▶ setup
```

### 6.3 `manche` × `phase` (dans `screen==="show"`)
```
envoi:  intro → (q → why)×≤8 → [duel*] → elim → endManche
cpc:    intro → (q → why)×≤6 → [duel*] → elim → endManche
fatal:  intro → clock (q/why enchaînés sous chrono) → elim → endManche
maitre: intro → (q → reveal)×≤5 → endManche
etoile: intro → guess → endManche → bilan
```
`duel` peut s'intercaler après n'importe quel `why` d'`envoi`/`cpc` (feu rouge). C'est la **seule** exception au flux linéaire, comme `handleStation` dans Bamboozled.

### 6.4 Le goulot
Toute réponse passe par `answer(payload)` → `resolve()` (score, feux, SRS, bots) → `render()` en `phase:"why"` → bouton « Suivant » → `endQ()` → décide : duel / fin de manche / `nextQ()`. **Aucune autre fonction ne change `S.manche`.**

---

## 7. Rendu et interface

### 7.1 Squelette DOM (statique, dans l'ordre)
```html
<div class="topbar">  <!-- son, export/import, réglages, palmarès --> </div>
<header><h1>…</h1><div class="sub">Jour N · cagnotte</div></header>
<div id="pupitres"></div>      <!-- 4 pupitres : nom, feu, score, .active, .out -->
<div id="banner"></div>        <!-- position:relative, déplacé par banner() -->
<main id="stage"></main>       <!-- tout le contenu de phase, innerHTML par render() -->
<div id="overlay"></div>       <!-- intro de manche, verdict de duel, élimination (z 50) -->
<div id="modal"><div class="sheet"></div></div>   <!-- confirmations (z 60) -->
<div id="etoile"></div>        <!-- plein écran : étoile + indices + saisie (z 85) -->
<div id="boot"></div>          <!-- démarrage (z 95) -->
```
Pas d'élément fixe en bas d'écran en v1. Si un jour on en ajoute un, appliquer le contrat `--pile-bas` (ResizeObserver → `#stage{padding-bottom}`), jamais un padding sur `body`.

### 7.2 Câblage des boutons
Délégation : un seul listener `pointerup` sur `#stage`, `data-act="answer" data-v="2"`. Table `ACT = { answer, next, coupBas, reveal, grade, order, guess, … }`. Ajouter une action = une entrée dans `ACT`, greppable. Aucun `onclick=` en chaîne.

### 7.3 Composants
- **Pupitre** : nom, feu (3 pastilles), score animé (`animScore` repris), `.active` (anneau or), `.out` (grisé, barré).
- **Carte question** : eyebrow = catégorie · format, énoncé, zone de réponse (4 boutons / ↑↓=? / liste à ordonner / saisie). Après réponse : la bonne en vert, la tienne en rouge si différente, `why` en dessous, bouton « Suivant » pleine largeur (`.btnrow` : 1er enfant `flex:1 1 100%`).
- **Horloges** (coup fatal) : deux barres qui se vident, la barre active pulse.
- **Bandeau** (`#banner`) : « Bonne réponse », « Piège ! » (quand `given === trap`), « Feu orange », etc. Dans le flux entre `#pupitres` et `#stage`.
- **Overlay de manche** : titre, règles en 2 lignes, bouton « C'est parti ».
- **Étoile** : disque doré masqué par 5 secteurs, un secteur retiré par indice ; indices en liste ; saisie + bouton unique « Proposer ».

### 7.4 CSS
- `:root` : `--ink:#0B1230` (nuit bleue), `--ink2:#14204A`, `--ink3:#1E2E63`, `--gold:#FFC93C`, `--vert:#4DE6A8`, `--orange:#FF9F43`, `--rouge:#FF4D5A`, `--bleu:#4FC3F7`, `--cream:#FFF4E0`, `--muted:#8E9BC7`, `--line:rgba(79,195,247,.3)`, `--sat/--sab/--sal/--sar` = `env(safe-area-inset-*, 0px)`, `--sans:'Bebas Neue','Arial Narrow',Arial,sans-serif`, `--serif:'Lora',Georgia,serif`.
- Pas d'alias, pas de variable orpheline.
- Z-index : `body::before/::after` 2 · flux 3 · `.topbar` 4 · `.fx-pts` 9 · `#overlay` 50 · `#modal` 60 · `#etoile` 85 · `#boot` 95.
- §2.4 de `ARCHITECTURE.md` recopié intégralement : `padding-top:max(20px,var(--sat))`, `.topbar{padding-top:max(30px,calc(10px + var(--sat)))}`, `viewport-fit=cover`, `user-select:none` + exception `input`, `prefers-reduced-motion`, `input[type=text],input[type=password]`.
- Boutons : mêmes règles que Bamboozled (border-bottom 5px, `:active` translate 3px), variantes `.b-gold .b-vert .b-rouge .b-ghost .b-sm`.

---

## 8. Fichiers et outils

### 8.1 Layout du repo
```
emi-quiz/
  index.html            ← GÉNÉRÉ, committé (GitHub Pages, branche main, racine)
  src/template.html     ← tout le HTML/CSS/JS avec le marqueur  /*__DATA__*/
  data/data.json        ← { CATS, BOTS, QCM, VF, SENS, ORDRE, OUVERTE, ETOILE }
  tools/build.py        ← data.json → index.html (json.dumps ensure_ascii=False, séparateurs stables), écriture atomique
  tools/verify.py       ← contrôles bloquants (8.2), exécuté par build.py avant le rename
  tools/audit.py        ← qualité éditoriale (8.3), lecture seule, exit 1 si bloquant
  tools/add.py          ← ajout contrôlé d'items (dry-run par défaut, délègue à audit puis build)
  tools/playtest.mjs    ← Playwright (8.4)
  package.json, .gitignore (node_modules, captures/)
  SPEC.md, ARCHITECTURE.md (ce doc + celui de Bamboozled pour référence)
```
Éditer une question = éditer `data.json`, jamais `index.html`. Les skills Claude Code deviennent trois `SKILL.md` qui pointent sur `tools/` (vendorés dans le repo).

### 8.2 `verify.py` — bloquant à chaque build
1. `index.html` contient exactement un `<script>`.
2. `node --check` sur le script extrait.
3. `const DATA=` re-parsé en JSON strict et **égal** à `data.json` (round-trip).
4. Tous les ids du squelette DOM (§7.1) présents.
5. Schéma : chaque item a `id` unique, `mat` (chaîne, `"emi"`, `"croissance"` ou `"mbf"`), `cat` ∈ CATS, `ch`, `diff`, `why` ; `qcm` a 4 `choices` et `0 ≤ a < 4` ; `vf.a` booléen ; `sens.a` ∈ {up,down,same,ambig} ; `ordre.steps` 3-6 ; `ouverte` a `model` et `points` ; `etoile` a 5 `clues` et un `mat` ; `qcmm` a `ok` ≥ 2, `ko` ≥ 3, `koWhy` aligné ; `q` chaîne ou liste de variantes ; `trap` ∈ liste §10 / §10 bis. Chaque entrée de `CATS` porte également un `mat` (`"emi"`, `"croissance"` ou `"mbf"`) ; toutes les matières présentes dans les items sont référencées dans au moins une catégorie.
6. Volumes minimaux par catégorie (§3) — **warning** en v1, bloquant à partir de la cible.
7. Taille : `index.html` ≥ 95 % de la taille du précédent build (protection troncature, remplace le plancher fixe).

### 8.3 `audit.py`
Repris de `bamboozle-questions` : `strict_dup`, `fuzzy_dup` (ratio > 0.72), `answer_in_question`, `multi_question`, `answer_too_long` (> 75), `duplicate_in_lot`. Ajouts : `qcm_choice_dup` (deux choix identiques après normalisation), `qcm_correct_longest` (la bonne réponse est la plus longue dans > 40 % des qcm d'une catégorie → signalé), `sens_no_ctx` (un `sens` sans cadre est ambigu → bloquant), `convention` (regex sur « compte financier positif » sans « sortie » → signalé).

### 8.4 `playtest.mjs`
- Serveur `python3 -m http.server` local, comme Bamboozled.
- `scenario` : `?seed=42&bots=weak` (acc = 0.1 partout) — le joueur répond toujours juste (le script lit `S.q` et clique la bonne réponse) et **traverse les 5 manches** ; puis `?seed=43&bots=strong` et réponses fausses → duel → élimination → bilan. Zéro `pageerror`.
- `srs` : après une mauvaise réponse sur `id X`, l'item est en boîte 0 et sort en premier à l'émission suivante (même seed).
- `layout` : premier élément visible ≥ 59 px (`.topbar` **et** `header h1`), bouton « Suivant » cliquable en bas de la carte la plus longue (`ordre` à 6 étapes + `why` de 3 lignes), safe-area 59+34 émulée.
- Captures SHA-256 comparées à `captures/baseline.json` — utiles seulement parce que le seed rend le rendu déterministe.

---

## 9. Plan de construction (échéance < 3 semaines)

| Jour | Livrable |
|---|---|
| J1 | `template.html` : head, CSS, squelette, `S`, `render`, boot, setup (catégories), pupitres, bots. `build.py` + `verify.py`. Coup d'envoi jouable (`qcm`, `vf`), feux, `why`. 40 items. |
| J2 | Duels, éliminations, bilan. SRS (`pickDue`, boîtes, jauges). Export/import. 100 items. |
| J3 | Coup par coup (`sens`, `ordre`, coup bas). `audit.py`, `add.py`. 160 items. |
| J4 | Coup fatal : horloges, `GEN` × 6, `qcm` 3 choix. Son + haptique. |
| J5 | Coup de maître (`ouverte`, paliers, cagnotte), étoile, règne, palmarès. |
| J6 | `playtest.mjs` (scenario, srs, layout), déploiement Pages, test iPhone réel. Banque à 270+. |
| J7 | Mode Express v1.1 (4 candidats / 3 bots / 60 s / 3 questions). Banque 232 items. |
| J8 | Cibles v1 atteintes : 267 items, 8 générateurs `calc`. |
| J9 | Consolidations et corrections. |
| J10 | Mémo (cheatsheet) : modal plein écran avec recherche. |
| J11 | Structure multi-matière branchée en v1 transparente (`mat` sur items et CATS ; setup filtre par matière ; getMats). |
| J11-bis | SPEC §2/§3/§8.2 explicités « `"emi"` ou `"croissance"` » ; verify.py contrôle `ALLOWED_MATS`. |
| J12 | Enrichissement banque EMI depuis sources 2025-2026 (`sources/pdfs_2025/`) : +10 items, WARN SENS résolus. 265 items. |
| J13 | Lot ORDRE + OUVERTE (+10 items) : chaque catégorie a désormais ≥ 2 ORDRE et ≥ 3 OUVERTE. Baselines de captures régénérées. 275 items. |
| J14 | Rééquilibrage `qcm_correct_longest` sur smi (100 %→12 %) et parite (88 %→12 %) : 14 QCM patchés, positions `a` réparties, distracteurs allongés en préservant les traps. +6 items ORDRE/OUVERTE. 281 items. **Cible ORDRE v1 (25) atteinte.** |
| J15 | Plomberie multi-matière au grand jour : `getMats()` se base sur les items (pas CATS) → sélecteur reste transparent tant qu'aucun item d'une seconde matière n'existe. 12 CATS croissance vides ajoutées à data.json (structure prête) : `residu`, `kaldor`, `harrod`, `solow`, `mrw`, `convergence`, `ak`, `romer`, `aghion`, `malthus`, `olg`, `institutions`. |
| J16-J22 | Peuplement de la matière croissance depuis `sources/croissance_2025/` : QCM, VF, SENS, ORDRE, OUVERTE pour les 12 cats croissance. 12 étoiles croissance ajoutées. Rééquilibrages `qcm_correct_longest` par cat. 369 items totaux (293 EMI + 92 croissance + 16 étoiles). |
| J23 | Complétion des 5 formats × 12 cats croissance. Base : 92 items croissance. Signalements audit : 18 → 5. |
| J24 | Polissage OUVERTE : 14 items dont `model` dépassait 350 char raccourcis (4 EMI + 10 croissance), sens économique et notations préservés. Audit : 5 → 4 signalements. |
| J25 | Rééquilibrage `qcm_correct_longest` sur les 4 dernières cats EMI (pen, si, cot, tcr) : 8 distracteurs allongés incarnant des confusions typiques §10 (stock-flux, clôture d'économie, sens du TCR, paradoxe Feldstein-Horioka, sens des flux Sud→Nord, convention certain/incertain, arbitrage triangulaire, OTC vs bourse). Audit : **0 signalement**. |
| J26 | 11 générateurs `calc` croissance ajoutés (residu, kaldor, harrod, solow, mrw, convergence, ak, romer, aghion, olg, malthus). **institutions** : pas de générateur (formule d'Acemoglu-Robinson non tractable numériquement, assumé). Registre `GEN_MAT` + filtre par matière dans `nextFatalQ`. Zéro doublon sur 55 000 tirages (statistiquement testé). |
| J27 | Fix des 7 générateurs EMI hérités souffrant de collisions ou de valeurs invraisemblables : **uip** (bad3 identique à bad2, 100 % dups), varTCR, neer, bdp, cross, ppa, pen_valo. Introduction du **pattern reject-sampling** (max 20 tentatives) comme standard des générateurs à distracteurs contraints. Zéro doublon sur 380 000 tirages. |
| J28 | Premier test iPhone réel via `python3 -m http.server 8080 --bind 0.0.0.0` sur LAN (192.168.1.55:8080). Golden path validé sur iPhone : tap zones, safe-area, KaTeX, matières EMI et croissance, coup fatal, coup de maître. |
| J29 | Playtest.mjs étendu : scenario 3 croissance (mat=croissance préseeded, joueur juste, weak → victory), mode `gens` (500 iter/gen dans le contexte page réel, 19 gens × 500 = 9500 tirages), `playThrough` instrumenté avec paramètre `recorder`. Baseline captures rafraîchie (drift de +36 Ko JS attendu). |
| J30 | Scenario 3b **fatal-probe** : injection directe de `S.manche="fatal"` puis 24 appels à `nextFatalQ()` pour probing forcé du filtre GEN_MAT. Résultat typique : 12/24 calc, 9/11 générateurs distincts, 0 hors matière. Assertion durcie « ≥ 6 calc et 0 foreign ». Doc SPEC §9 mise à jour. |
| J31 | 8 étoiles croissance ajoutées (et-17 à et-24) : Résidu de Solow, Fil du rasoir de Harrod, Faits stylisés de Kaldor, MRW, Convergence conditionnelle, Modèle AK, Non-rivalité des idées, Critique de Jones. Parité étoiles atteinte : **12 EMI + 12 croissance = 24**. |
| J32 | Enrichissement banque EMI depuis 15 fichiers `sources/drive-download-*` : 6 VF (si×2, equil×2, mf×2) + 2 SENS (si, forex) — cats les plus faibles remontées à ≥ 5. Correction du modèle d'allocation d'id (unicité **cross-bank**, pas par bank). Étoile OLG Diamond ajoutée (et-25) : 13 étoiles croissance, couvrant les 12 cats. Doc SPEC.md finalisée. **377 items, 25 étoiles, 0 signalement audit**. |

| J42-bis | SRS : SM-2 / FSRS conservés, SPEC §5 réécrite en conséquence ; `pickDue` respecte enfin les paliers et les ex æquo et pondère le tirage par la faiblesse de la catégorie. |
| J42 | Matière `mbf` (Banque et marché) : format `qcmm` à réservoirs (format du partiel, tout ou rien), variantes de formulation, verify/audit/add étendus. 34 catégories (17 notions + 17 auteurs), 34 cours, 357 items (151 qcmm, 123 vf, 36 sens, 14 ordre, 33 ouvertes) + 12 étoiles, 8 générateurs `calc` mbf. Playtest : scénarios 4, 4b, 4c. Sources : diapos chap. 1-4, chap. 5, Carré, ESRB, Cœuré, VoxEU, articles fondateurs (OCR), partiels 2020 et 2026. Contradictions : NOTES.md. |

**Patterns clés stabilisés J24→J32** :
- **Reject-sampling GEN** : chaque générateur avec distracteurs contraints boucle jusqu'à 20 fois pour garantir 4 réponses toutes distinctes. Cassure discrète du déterminisme par seed (au bord des collisions) mais préservation du principe « distracteurs = confusions du prof, pas remplissage ».
- **Registre `GEN_MAT`** : map `{name → mat}` co-localisée avec `GEN`. Filtre appliqué dans `nextFatalQ` (`Object.keys(GEN).filter(n => GEN_MAT[n] === S.mat)`) + fallback qcm3 si aucun générateur disponible pour la matière.
- **`playThrough(recorder)`** : signature étendue pour capturer les questions vues sans modifier les scenarios existants. Base pour futures assertions (couverture par cat, séquencement des formats).
- **`fatal-probe`** : injection d'état + boucle `nextFatalQ()` synchrone → couverture d'intégration sans dépendance à la victoire naturelle du joueur.
- **Ids `cat-nnn` uniques cross-bank** : la numérotation n'est PAS par bank. Un `si-021` en VF interdit `si-021` ailleurs. `verify.py` règle 5 enforce ce contrat globalement. Toute nouvelle allocation manuelle doit prendre `max(id) + 1` sur toutes les banks confondues pour la cat.

**Note d'écart honnête** : `institutions` n'a pas de générateur `calc`. Aucun modèle d'Acemoglu-Robinson ne produit un calcul de tête crédible ; toute tentative aboutirait à du remplissage. Le format `calc` reste 11/12 pour croissance (contre 8/12 pour EMI où 4 cats sans gen). Non-défaut par design.

---

**État v1 (fin J32) — cibles atteintes** :
- Émission complète jouable EMI (12 cats, 292 items) et Croissance (12 cats, 85 items). Total : **377 items** dont **25 étoiles mystère** (12 EMI + 13 croissance).
- 19 générateurs `calc` (8 EMI + 11 croissance), tous zéro-doublon sur 380 000 tirages, filtre par matière opérationnel dans le coup fatal.
- `playtest.mjs all` : 3 scenarios + fatal-probe + gens + srs + layout, **zéro erreur**, **zéro pageerror**, hashes stables.
- Audit `tools/audit.py` : **0 signalement, 0 bloquant**.
- Test iPhone réel validé (WiFi LAN), safe-area OK, KaTeX OK.
- Doc SPEC.md à jour, plan §9 renseigné J1→J32.

---

## 10. Pièges du prof → règles de distracteurs

Extraits des diapos « erreurs fréquentes » et « conseils ». Chaque `trap` est une clé autorisée ; l'audit vérifie qu'un item avec `trap` a bien un distracteur qui l'incarne.

| `trap` | Confusion | Distracteur type |
|---|---|---|
| `signe-bdp` | Signe du compte financier ; haut/bas de la balance | « entrée nette de capitaux » quand c'est une sortie |
| `stock-flux` | PEN (stock) vs solde courant (flux) | « la PEN diminue exactement du déficit courant » |
| `bc-bcour` | Balance commerciale vs balance courante | ajouter/oublier revenus primaires |
| `certain-incertain` | Sens de lecture du taux ; une hausse = appréciation ou dépréciation | l'inverse du bon sens |
| `niveau-log` | Multiplier des logs, comparer un ratio à une différence | `Eᵃ/E` au lieu de `eᵃ − e` |
| `horizon` | Taux annualisé vs horizon de l'anticipation | 4 % sur 3 mois compté 4 % |
| `sens-parite` | Sens de `i − i*` vs `eᵃ − e` | appréciation ↔ dépréciation inversées |
| `fixe-flexible` | Modèle à prix fixes (MF) vs prix flexibles (monétaire) | conclure « inflation immédiate » sous MF |
| `mf-regime` | Efficacité des politiques selon régime × mobilité | budgétaire efficace en flexible + mobilité parfaite |
| `bs-etapes` | Balassa-Samuelson sans la contagion salariale | sauter une étape |
| `ml-symetrie` | Marshall-Lerner : symétrie, courbe en J | « une dépréciation améliore tout de suite le solde » |
| `endo-exo` | Variable endogène/exogène, équilibre de marché | traiter `e` comme exogène sous PNCTI |
| `statique-dyn` | MF statique vs Dornbusch dynamique (CT/LT) | pas de surajustement dans Dornbusch |
| `sterilise` | Intervention stérilisée sans effet sur LM | « la stérilisation déplace LM » |

### 10 bis. Banque et marché — pièges → `trap`

| `trap` | Confusion |
|---|---|
| `ai-exante-expost` | Sélection adverse (ex ante, Leland-Pyle) vs aléa moral (ex post, Diamond 1984) |
| `auteur-role` | Signal (Leland-Pyle) / contrôleur délégué (Diamond) / assureur de liquidité (Diamond-Dybvig) |
| `desintermediation` | Croire à la désintermédiation ; mesure en valeur vs en volume |
| `actif-passif` | Risque d'actif vs de passif ; illiquidité vs insolvabilité |
| `rationnement-prix` | Stiglitz-Weiss : la banque rationne au lieu de monter le taux |
| `levier-sens` | Ratio de levier FP/A vs levier A/FP ; sens de la variation |
| `rwa-actif` | FP/RWA (pondéré) vs FP/A (non pondéré) |
| `lineaire` | Finance-croissance linéaire vs en cloche ; corrélation ≠ causalité |
| `bulle-type` | Rationnelle / mimétique / comportementale : information et rationalité |
| `minsky-regimes` | Financement couvert / spéculatif / Ponzi |
| `paradoxe` | Tranquillité (Minsky) vs crédibilité (Borio) |
| `cua-law` | Cleaning up afterwards vs leaning against the wind |
| `micro-macro` | Microprudentiel vs macroprudentiel |
| `bale-version` | Mesure attribuée au mauvais accord de Bâle |
| `canal` | Canal du crédit strict / large vs prise de risque vs prix d'actifs |
| `date-auteur` | Mauvaise date ou mauvais auteur |

---

## Annexe A — Bots (`DATA.BOTS`)

```json
[
 {"name":"La Cambiste",      "acc":{"qcm":0.70,"vf":0.70,"sens":0.45,"ordre":0.35,"calc":0.65,"qcm3":0.75}},
 {"name":"Le Bachoteur",     "acc":{"qcm":0.60,"vf":0.75,"sens":0.55,"ordre":0.55,"calc":0.40,"qcm3":0.65}},
 {"name":"L'Arbitragiste",   "acc":{"qcm":0.50,"vf":0.55,"sens":0.60,"ordre":0.40,"calc":0.75,"qcm3":0.60}}
]
```
Calibrage visé : un joueur à ~60 % de bonnes réponses atteint le coup fatal deux émissions sur trois. `?bots=weak|strong` surcharge tout à 0.1 / 0.9 (playtest et réglage).

## Annexe B — Ce que cette spec ne fixe pas encore
- Le nom définitif et l'icône (base64 inlinée comme Bamboozled).
- Les textes d'intro de manche (`T.intro.envoi`, …) — à écrire avec l'UI.
- Le barème exact des points du coup fatal (aucun en v1 : le titre suffit).
- Si le règne doit survivre à une réinstallation : non en v1 (localStorage seulement, export/import pour le reste).
