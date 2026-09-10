# Bamboozled — Architecture de `index.html`

Document destiné à répliquer l'application pour un autre jeu. Il décrit
exactement ce qui existe **aujourd'hui** dans `~/dev/bamboozled/index.html`,
sans invention : les numéros de ligne renvoient au fichier versionné dans
`main` (état du working tree au moment de la rédaction). Aucun autre fichier
source n'existe : ni bundler, ni framework, ni backend interne.

---

## 1. Vue d'ensemble

- **Taille du fichier** : `477 480` octets (~466 Ko).
- **Nombre de lignes** : `2 882`.
- **Découpage physique** (par n° de ligne) :

  | Bloc | Lignes | Contenu |
  |---|---|---|
  | `<!DOCTYPE html>` + `<head>` métas | 1–13 | Doctype, viewport, méta iOS/PWA, `theme-color`. |
  | Icônes `data:image/png;base64` | 14 (une seule ligne monstre) | `apple-touch-icon` + `icon` inlinés en base64 — pas d'asset externe. |
  | Google Fonts | 15–17 | `preconnect` + `<link>` vers Monoton, Bebas Neue, Lora. |
  | `<style>…</style>` | 18–681 | Tout le CSS (~660 lignes), aucun fichier externe. |
  | `</head><body>` + topbar + squelette DOM | 683–706 | Barre du haut, `header`, huit conteneurs statiques (podiums/stage/overlay/modal/boot/portal/fog/secret/cups/banner/logwrap). |
  | `<script>` | 707–2881 | Tout le JS (~2 170 lignes). Débute par la constante `DATA`, puis `I18N`, puis toute la logique. |
  | `</script></body></html>` | 2880–2882 | Fin. |

- **Sections logiques à l'intérieur du `<script>`** (marqueurs textuels
  présents ou lignes de démarcation) :

  | Section | Lignes | Marqueur |
  |---|---|---|
  | Constante `DATA` (JSON inlinée) | 708 | `const DATA={"fr":…};` — **une seule ligne** de 240 563 caractères. |
  | Constante `I18N` (dictionnaires) | 710–1400 | `const I18N={fr:{…}, …}`, avec `Object.assign` pour hériter (`en` → `it`). |
  | Sélection de langue | 1401–1408 | `let LANG="fr"; const T=()=>I18N[LANG]; const D=()=>DATA[LANG];` |
  | IA (Claude API) | 1400–1424 | `const AI={…}`, `topUpAI`, `setDiff`, `diffShort`. |
  | Clé API personnelle | 1425–1432 | `USER_KEY_STORAGE`, `userApiKey`, `saveUserKey`. |
  | Reset / Export / Import de partie | 1434–1449 | `askResetGame`, `exportGame`, `importGame`. |
  | Mode « écran secondaire » | 1451–1459 | `toggleTableMode`. |
  | Appel Claude + fetch AI | 1461–1487 | `askClaude`, `fetchAIQuestions`, `fetchAIWango`. |
  | Config proxy | 1499–1500 | `const API_URL="https://bamboozle-ai.sam1chirat.workers.dev"; const API_MODEL="claude-opus-5";` |
  | State `S` + `newGame` | 1503–1518 | `let S=null; function newGame(names){…}`. |
  | Helpers state | 1519–1525 | `cp`, `shuffle`, `log`, `fmt`, `pick`. |
  | Mémoire longue `SEEN` | 1527–1546 | `SEEN`, `seenLoad`, `seenSave`, `qid`, `pickFresh`. |
  | Questions | 1548–1567 | `drawQuestion`, `goRetro`, `angelSkip`, `goFriends`, `gainFor`, `lossFor`. |
  | Bamboozle + `answer()` | 1568–1626 | `triggerBamboozle`, `answer`. |
  | Tours | 1628–1650 | `resolveContract`, `endTurn`, `nextPlayer`. |
  | Échelle de la Chance | 1652–1697 | `LADDER`, `GOAL`, `STATIONS`, `climbLadder`, `handleStation`. |
  | Anneau Arc-en-ciel (blackjack) | 1699–1744 | `RCOLORS`, `bjCard`, `bjTotal`, `startRing`, `bjHit`, `bjStand`, `bjEnd`. |
  | Singe Doré | 1746–1770 | `yankTail`, `yankResult`, `stayBelow`. |
  | Roue + Doubles | 1774–1867 | `spinWheel`, `wheelDouble`, `dblPick`, `dblResolve`, `resolveWheel`. |
  | Mudhut / Time Torturing Tree | 1871–1895 | `bwOK`, `enterMudhut`, `payMudhut`, `startTTT`, `tttAnswer`, `tttQ`, `tttFail`. |
  | Wicked Wango | 1897–1944 | `drawWQ`, `actionWango`, `wangoOK`, `wangoNext`, `wangoStop`, `wangoFail`. |
  | Duel (Face-Off) | 1946–1975 | `startDuel`, `duelPick`, `duelEnd`, `finishDuel`. |
  | Google Card Deck | 1977–2051 | `drawG`, `actionGoogle`, `chooseGoogleTarget`, `renderGoogleButtons`. |
  | Gages (dares) | 2053–2068 | `daresHTML`, `refreshDares`, `dareDone`, `dareSlip`, `dareDrop`. |
  | Finale | 2070–2101 | `startFinal`, `finalBegin`, `finalQ`, `finalAnswer`, `finalFault`, `finalEnd`. |
  | Timer | 2103–2119 | `TI`, `startTimer`, `stopTimer`, `updTimer`. |
  | UI générique | 2122–2197 | `meterHTML`, `showEvent`, `marqueeCascade`, `dropConfetti`, `showStamp`, `hideStamp`, `askModal`, `closeModal`, `pickTarget`, `podMenu`, `refreshMenu`. |
  | Son WebAudio | 2200–2224 | `SFX`, `actx`, `tone`, `sfx`, `toggleSFX`. |
  | Porte secrète | 2227–2302 | `norm`, `openPortal`, `raiseFog`, `askWorthy`, `worthyYes`/`No`, `openSecret`, `closeSecret`, `trySecret`. |
  | Cups (mini-jeu carte) | 2306–2477 | `CUPS`, `SUITS`, `SINGLE`, `cupsDeck`, `cupsEval`, `openCups`, `cupsPickSet`, `cupsPickGo`, `closeCups`, `cupsDeal`, `cupsShow`, `cupsSit`, `cupsCheckWin`, `cupsSuggest`, `cupsSeal`, `renderCups`. |
  | Moteur à ressorts | 2481–2497 | `springTo`. |
  | Signature sonore / haptique | 2503–2534 | `VIB`, listener `pointerdown`, `fx`. |
  | Bandeau de verdict | 2536–2551 | `BT`, `buzz`, `banner`, `hideBanner`. |
  | Effets de plateau (score / floating) | 2554–2573 | `PREV`, `animScore`, `floatPts`. |
  | Rendu | 2575–2809 | `renderLog`, `renderPodiums`, `render` (le gros switch phase-par-phase). |
  | Setup / boot | 2810–2879 | `setupNames`, `renderSetup`, `addPlayer`, `drawPlist`, `tryStart`, IIFE boot, IIFE ResizeObserver `--pile-bas`, appels `renderSetup()`, `topUpAI()`. |

- **Choix « fichier unique »** : le projet est distribué tel quel (GitHub
  Pages sans build ; on ouvre `index.html` en local ou derrière un
  `python3 -m http.server`). Conséquences :
  - Pas de bundler, pas d'import ES modules, pas de transpilation. Le
    JS reste ES2020 « à plat » et doit tourner directement dans Safari
    iOS et Chromium.
  - Toutes les banques de données sont **inlinées**. Modifier une
    question = modifier `index.html`. La skill `bamboozle-patch`
    encapsule ce risque : voir §9.
  - Une modification de deux caractères peut invalider le fichier
    (crochet de trop dans `DATA`, ligne cassée par un éditeur qui
    reformate). Les garde-fous existent pour ça (§9 & §10).
  - Le fichier fait 470 Ko ; on doit rester **sous 300 Ko de plancher**
    obligatoire (`bamboozle-patch/verify.py` refuse toute écriture qui
    tombe en dessous — protection contre les troncatures d'éditeur).

---

## 2. Structure CSS

Le bloc `<style>` (lignes 18–681) est monolithique. Aucune règle n'utilise
`@import`, ni de préprocesseur. Toutes les valeurs sont litérales.

### 2.1 Variables (`:root`, lignes 19–37)

| Variable | Valeur | Rôle |
|---|---|---|
| `--ink` | `#120821` | Fond nuit, base des dégradés du body et du boot. |
| `--ink2` | `#1B0F33` | Cartes (`.card`, `#modal .sheet`). |
| `--ink3` | `#251543` | Fond plus clair, plaques (`.plist .pi`, `.dare`). |
| `--nyellow` | `#FFD54A` | Or / accent principal (bouton `b-gold`, timer, titre). |
| `--nviolet` | `#B26CFF` | Violet néon (sous-titre, dots, ombre des cartes). |
| `--norange` | `#FF7A3D` | Orange (rétro, action bonus, roue, banner « fire »). |
| `--nblue` | `#4FC3F7` | Bleu néon (eyebrow, réponse, timer normal). |
| `--nred` | `#FF4D5A` | Rouge (miss, `stamp`, banner « bad »). |
| `--nmint` | `#4DE6A8` | Menthe (bonus Friends, banner « good », gain). |
| `--cream` | `#FFF4E0` | Texte principal. |
| `--muted` | `#8E7FA8` | Texte secondaire, hint. |
| `--line` | `rgba(178,108,255,.35)` | Bordures faibles. |
| `--sat/--sab/--sal/--sar` | `env(safe-area-inset-*, 0px)` | Réservations iPhone. |
| `--journal-h` | `calc(60px + var(--sab))` | Hauteur du journal replié. |
| `--banner-max-h` | `80px` | **Obsolète** (voir §10, bug #B1). |
| `--pile-bas` | `96px` par défaut, réécrite au runtime par ResizeObserver | Hauteur RÉELLE de la pile fixe en bas — seule source de vérité pour le padding du stage. |
| `--sans` | `'Bebas Neue','Arial Narrow',Arial,sans-serif` | Typo affichage (podium, boutons, titres). |
| `--serif` | `'Lora',Georgia,serif` | Typo corps de texte. |
| Alias rétro-compat | `--stage`, `--panel`, `--panel2`, `--gold`, `--magenta`, `--cyan`, `--red`, `--dim`, `--plum`, `--plum2`, `--plum3`, `--mustard`, `--perk`, `--logoblue`, `--brick`, `--mint`, `--cream2:#D8CBB6` | Anciens noms mappés sur les nouveaux. Certaines règles CSS les utilisent encore — ne pas les retirer. |

### 2.2 Familles typographiques

- **Google Fonts** chargées ligne 17 : `Monoton`, `Bebas Neue`, `Lora`
  (italiques inclus, poids 400/600).
- **Monoton** : enseigne (`header h1`, `#cups h2`, `#boot .bootB`,
  `#secret .sectitle`). Utilisée uniquement pour les gros titres.
- **Bebas Neue** (`var(--sans)`) : boutons, podiums, `eyebrow`, `sub`,
  `timer`, `banner`. Toutes les majuscules d'ambiance.
- **Lora** (`var(--serif)`) : corps de texte, question, réponse, hint.
- Fallback système systématique : `Arial Narrow`, `Georgia`.

### 2.3 Classes structurantes

- **Cartes** : `.card` (rectangle violet nuit à ombre violette, animation
  `breathe`), `.card.live` (rampe d'ampoules + balayage `sweep` unique),
  `.card.drop-in` (entrée descendante). Le rectangle centré des écrans de
  transition est `.dialog-card` (créé lors du chantier « rectangles
  centrés »).
- **Boutons** : `button` (fond violet nuit, `border-bottom-width:5px`
  effet Duolingo, `:active` translate 3px). Variantes :
  `.b-gold`, `.b-mg` (orange), `.b-cy` (bleu), `.b-rd` (rouge),
  `.b-ghost` (transparent), `.b-sm` (compact), `.b-xs` (topbar).
  Le premier bouton d'une `.btnrow` prend **toute la largeur** (`flex:1
  1 100%`), les suivants se partagent la ligne suivante — hiérarchie
  visuelle imposée en juin (§10, bug #B4).
- **Podiums** : `#podiums` en grid `auto-fit,minmax(108px,1fr)`, avec
  variantes `.n5` et `.n9` pour 5+ et 9+ joueurs. `.pod.active` porte
  l'anneau jaune, `.pod.win/lose/entering/receding` animent les
  transitions de score et de tour.
- **Bandeau (`#banner`)** : `position:relative`. **Ne PAS repasser
  `position:fixed`** — voir §10, bug #B1. Le JS le déplace juste après
  `#podiums` à chaque `banner()`.
- **Journal (`#logwrap`)** : `position:fixed;bottom:0`, `z-index:40`,
  `max-height:var(--journal-h)`, dépliable en `max-height:calc(180px +
  var(--sab))`. Sa hauteur RÉELLE alimente `--pile-bas` via un
  ResizeObserver (§10, bug #B2).
- **Écrans modaux plein écran** : chacun est un `<div>` fixed inset:0
  masqué par défaut, activé par `.show`. Liste complète : `#boot`,
  `#portal`, `#fog`, `#secret`, `#cups`, `#modal`, `#overlay`.

### 2.4 Règles critiques à ne jamais casser

1. **Safe-area haute**. `body` porte `padding-top:max(20px,var(--sat))`
   et `.topbar` porte `padding-top:max(30px,calc(10px + var(--sat)))`.
   Le `max()` est un plancher obligatoire — Safari iOS peut résoudre
   `env(safe-area-inset-top)` à `0` sur certaines versions et couper la
   barre d'état sinon (bug #B3, revenu trois fois).

2. **Empilement du bas d'écran (pile-bas)**. Une **seule** source de
   vérité : la hauteur réelle de `#logwrap`, mesurée par
   `ResizeObserver` et écrite dans `--pile-bas`. `#stage` porte
   `padding-bottom:calc(var(--pile-bas) + 24px)`. Le padding-bottom
   n'est PAS sur `body` (comportement instable en mobile) mais sur
   `#stage`. Fallback si pas d'observer : `--pile-bas:220px`.
   Toute nouvelle règle du type `#stage{padding-bottom:XXpx}` casse ce
   contrat.

3. **Bandeau non-fixé**. `#banner` est `position:relative`. `banner()`
   en JS l'insère dans le flux, entre `#podiums` et `#stage`, pour
   qu'il ne puisse jamais recouvrir un bouton d'action.

4. **Z-index (à respecter)** :

   | Élément | z-index |
   |---|---|
   | `body::before / ::after` (scanlines, vignette) | 2 |
   | `header`, `#podiums`, `#stage`, `#logwrap` (flux) | 3 |
   | `.topbar` | 4 |
   | `.fx-pts` (chip flottante des podiums) | 9 |
   | `#logwrap` (fixed) | 40 |
   | `#overlay` (grand écran d'événement) | 50 |
   | `#modal` (boîtes de dialogue) | 60 |
   | `body.table-mode #podiums` (mode écran secondaire) | 70 |
   | `#cups` | 84 |
   | `#secret` (porte secrète) | 85 |
   | `#fog` (brume rouge) | 88 |
   | `#portal` (extinction CRT) | 92 |
   | `#boot` (démarrage) | 95 |

   Aucune règle ne doit dépasser 95 sans raison forte ; l'ordre est
   destiné à empiler correctement les événements rares au-dessus du
   plateau normal.

5. **Sélection texte** (`user-select`) : le `body` est
   `user-select:none;-webkit-touch-callout:none`. Une règle inverse la
   politique pour `input, textarea, #logwrap, #logwrap *` uniquement.
   Ne pas retirer sinon le menu iOS ressort sur appui long partout
   (bug #B5).

6. **prefers-reduced-motion**. Une méta-règle en fin de style désactive
   toutes les animations si le système le demande :
   `*,*::before,*::after{animation:none !important}`. Toute nouvelle
   animation doit se plier à ce filet.

---

## 3. État de jeu

### 3.1 L'objet `S` (défini par `newGame`, ligne 1505)

```
S = {
  screen:  "setup" | "game" | "final" | "winner",   // écran macro
  players: Player[],                                 // 2..∞
  cur:     Number,                                   // index du joueur actif
  phase:   "question" | "action" | "wheel" | "wango"
         | "ring"     | "yank"   | "monkeygate"
         | "duel"     | "card"   | "double" | "ttt", // état de la scène
  q:       [String, String] | {t,x,ans} | null,      // question courante
  showA:   Boolean,                                  // réponse révélée ?
  isRetro: Boolean,
  isFriends: Boolean,
  retroUsed: Boolean,
  bonus:   String,                                   // défi bonus du tour (piochée dans D().B)
  usedQ, usedR, usedF, usedH, usedWQ: Number[],      // indices déjà tirés dans les banques
  deckG:   Number[],                                 // deck mélangé de Google Cards (indices dans D().G)
  deckDBL: Number[]?,                                // deck mélangé pour les Doubles de la roue
  wango:   { lvl, bank, state, cats, q, showA } | null,
  wangoDouble: Boolean,                              // prochaine Google Card doublée
  turnGain: Number,                                  // total marqué ce tour (pour la synthèse)
  bonusQ:   Object|null,                             // question bonus enchaînée
  ttt:     { idx } | null,
  final:   { idx, qn, ok, started } | null,
  duel:    { a:Number,b:Number,after:Function } | null,
  card:    { deck, c, dblPending } | null,           // Google Card en cours
  dbcard:  { c, after } | null,                      // « Double de la roue » en cours
  bj:      { me:Card[], monkey:Card[], state } | null, // blackjack de l'Anneau
  isDouble: Boolean,                                 // double 6/6 etc. sur la roue
  lastB:   String[],                                 // 6 derniers défis bonus (anti-répétition courte)
  log:     String[],                                 // 30 dernières entrées de journal
  warned:  Object?,                                  // banques épuisées déjà signalées
  timer, timerMax: Number,                           // écrit par startTimer
}
```

### 3.2 L'objet `Player`

```
{
  name:     String,    // saisi au setup, max 14 caractères
  score:    Number,    // ≥ 0 en permanence
  angel:    Number,    // Angel Passes en poche (max 2)
  mudhut:   Number,    // tours restants d'abri (0 = pas abrité)
  hopping:  Number,    // questions à cloche-pied restantes
  dbl:      Boolean,   // prochaine réponse compte double
  streak:   Number,    // mauvaises réponses consécutives (3 = Bamboozle)
  combo:    Number,    // bonnes réponses consécutives (≥3 = bandeau "fire")
  dares:    Object[],  // gages en cours (dépilés à la fin du tour du joueur ciblé)
  lastGain: Number,
  rung:     Number,    // 0..LADDER (6) — position sur l'Échelle
  seen:     { [rung:Number]: true }, // stations déjà franchies (hut/ring/monkey)
  shield:   Boolean,   // absorbe la prochaine perte
  contract: Number|null, // index d'un adversaire visé par un contrat
  pending:  Number?,   // station en attente d'être jouée
  skip:     Boolean?,  // tour à passer (Silence Radio)
}
```

### 3.3 Persistance localStorage

Deux clés (et deux seulement) :

| Clé | Format | Ligne | Écrit par | Lu par |
|---|---|---|---|---|
| `bamboozle.seen.v1` | `JSON.stringify([...Set])`, coupé aux 4 000 derniers hashes | 1521 | `seenSave()` | `seenLoad()` |
| `bamboozle.userApiKey.v1` | Chaîne brute (clé Anthropic) | 1410 | `saveUserKey()` | `userApiKey()` |

- `bamboozle.seen.v1` mémorise les questions déjà posées, par hash 32
  bits (`qid()`, ligne 1525). Assure qu'une question ne revient jamais,
  y compris **entre parties**. Rotation FIFO à 4 000 entrées.
- `bamboozle.userApiKey.v1` héberge la clé Anthropic personnelle
  optionnelle. Si présente, `askClaude()` bypass le proxy Cloudflare.

**Aucune** autre donnée n'est persistée. La partie en cours n'est PAS
sauvegardée automatiquement : `exportGame()`/`importGame()` (§3.4)
sont les seuls moyens d'y revenir plus tard.

### 3.4 Export / Import de partie (JSON)

`exportGame()` (ligne 1436) construit :

```
{
  version: 1,
  ts:      Date.now(),
  S:       S,                       // sérialisation directe
  SEEN:    { key: "bamboozle.seen.v1",
             set: [...SEEN.set] }   // snapshot des hashes vus
}
```

et déclenche un download `bamboozle-YYYY-MM-DD-HH-MM-SS.json`.
`importGame(ev)` (ligne 1447) attend la même structure minimale
(`j.S.players` non vide), réhydrate `S`, réinjecte `SEEN` si présent,
puis appelle `render()`.

---

## 4. Machine à états

Deux niveaux :

- `S.screen` (macro-écran) — quel gros pan de rendu est visible.
- `S.phase` (scène de jeu) — sub-état pendant `S.screen === "game"`.

### 4.1 Niveau `S.screen`

```
              tryStart()
   setup ─────────────────▶ game
                              │
                              │  score >= GOAL  (nextPlayer, l.1646)
                              │  OU yank réussi (yankResult, l.1758)
                              ▼
                            final
                              │
                     ┌────────┴─────────┐
              finalEnd(true)       finalEnd(false)
                     │                  │
                     ▼                  ▼
                  winner            game (score = 2/3 GOAL, rung=0)
                     │
             askResetGame()
                     │  (S = null)
                     ▼
                  setup
```

Fonction pilote de chaque bascule :

- `setup → game` : `tryStart()` (l.2847) → `newGame(names)` (l.1505).
- `game → final` : `nextPlayer()` (l.1642) détecte `score >= GOAL = 1500`
  et appelle `startFinal(q)` ; ou `yankResult(true)` (l.1748) appelle
  `startFinal(S.cur)`.
- `final → winner` : `finalEnd(true, …)` (l.2094).
- `final → game` (échec finale) : `finalEnd(false, …)` (l.2098) —
  score ramené à `round(GOAL*2/3)`, rung=0, `S.final=null`.
- `winner → setup` : `askResetGame()` (l.1434) sur confirmation.
- `setup → setup` (nouvelle partie sans passer par winner) : idem, `S=null`.

### 4.2 Niveau `S.phase` (à l'intérieur de `screen==="game"`)

```
                     drawQuestion()               answer(ok=true, …)
   ┌─── question ────────────────────────────────────▶ action
   │                              │       │
   │       answer(ok=false)       │       └── (score >= GOAL) ──▶ final (via nextPlayer)
   │                              │
   ▼                              ▼
 endTurn ◀── (via handleStation) ── one of :
                                    ├── spinWheel()         → wheel
                                    ├── actionWango()       → wango
                                    ├── actionGoogle()      → card
                                    └── payMudhut()         → endTurn direct
   wheel  ── resolveWheel(n)  ─────▶ ttt / wango / duel / question(bonus) / …
                                     ou double (si isDouble) → dblResolve → endTurn
   ring   ── bjEnd(verdict)   ─────▶ endTurn
   yank   ── yankResult(ok)   ─────▶ startFinal / endTurn
   monkeygate ── yankTail()  ─────▶ yank
                stayBelow()  ─────▶ endTurn
   duel   ── duelEnd(w)       ─────▶ finishDuel → endTurn
   card   ── (choix Google)   ─────▶ endTurn (ou nouvelle question si "replay")
   double ── dblResolve(kind) ─────▶ endTurn ou question
   ttt    ── tttAnswer(ok)*3  ─────▶ endTurn ou triggerBamboozle
   wango  ── wangoOK/Fail/Stop ────▶ endTurn (ou wango niveau suivant)
```

**Toutes** les transitions passent par `endTurn()` → `nextPlayer()`
sauf trois cas particuliers :

- `answer(true, …)` reste dans `S.phase="action"` (le joueur choisit
  encore son avantage) — c'est le seul chemin qui ne rebascule pas
  vers un autre joueur.
- `handleStation()` (l.1671) intercepte avant `endTurn` pour jouer
  hut/ring/monkey si la station a été franchie pendant la montée.
- `resolveWheel` + `isDouble` déclenche `wheelDouble` avant
  `endTurn` — l'événement rare s'intercale.

---

## 5. Fonctions cœur

Signatures effectives, effets de bord, appelants.

### `pickFresh(bank, used)` — l.1541
- **Rôle** : tirer un élément de `bank` en évitant à la fois `used`
  (dans la partie courante) ET `SEEN.set` (mémoire longue localStorage).
- **Retour** : l'entrée choisie (tuple `[q,a]` ou objet `{t,x,ans}` ou
  `{k,t,x,…}`).
- **Effets** : push l'indice choisi dans `used` ; `seenMark` sur la
  question ; log `T().bankOut` **une seule fois par banque** via
  `S.warned[tag]` quand la banque est intégralement épuisée.
- **Appelants** : `drawQuestion`, `goRetro`, `goFriends`, `drawWQ`
  (via une variante), `tttQ`, `finalQ`.
- **Contrat de fraîcheur** : la skill `bamboozle-playtest` vérifie
  qu'aucun doublon ne peut sortir avant `bank.length` tirages (§9).

### `render()` — l.2624
- **Rôle** : reconstruire le contenu de `#stage` en fonction de
  `S.screen` puis `S.phase`. Appelle `renderPodiums()` avant tout.
- **Signature** : `()`. Pas de paramètre, opère intégralement sur `S`.
- **Effets** : `innerHTML` sur `#stage`. Détache/rattache `#banner`
  quand invoqué par `banner()`. `updTimer()` réappelé si `S.timer`
  visible. Vibration/haptique déclenchés depuis `banner`/`fx`, pas
  depuis `render`.
- **Appelants** : à peu près partout. C'est le point unique de rendu ;
  toute mutation de `S` qui doit se voir déclenche `render()`.

### `answer(ok, bonus)` — l.1590
- **Rôle** : trancher une question (ok = bonne réponse ; bonus = défi
  du tour relevé).
- **Effets** :
  - Décrémente `p.hopping` si > 0.
  - Si `ok`: gain = `gainFor(p) + (bonus?50:0)`, reset streak, ajoute
    au score, log, résout un contrat gagné, `banner("good"|"fire")`,
    bascule vers `S.phase="action"` (sauf si `S.bonusQ`).
  - Sinon : incrémente `streak`, à `>=3` déclenche `triggerBamboozle`
    et arrête. Applique la perte (`lossFor(p)`), sauf si Angel Pass
    (askModal) ou bouclier (`shield`). `endTurn` en fin.
- **Appelants** : boutons de la carte question dans `render()`
  (`onclick="answer(true|false, …)"`).

### `nextPlayer()` — l.1642
- **Rôle** : passer la main au joueur suivant, ou lancer la finale.
- **Effets** :
  - Détecte score >= `GOAL=1500` → `startFinal(index)` et return.
  - `S.cur = (S.cur+1) % players.length`.
  - Reset `S.turnGain`, `S.bonusQ`, `S.phase="question"`.
  - Si `cp().skip` : consomme le flag et saute au joueur d'après.
  - Décrémente `mudhut` si le joueur entrant y était.
  - `log(T().turn(name, hopping))`, `drawQuestion()`, `render()`.
- **Appelé par** : `endTurn` uniquement.

### `askClaude(prompt)` — l.1461
- **Rôle** : appeler l'API Anthropic (soit direct avec clé user, soit
  via le proxy Cloudflare).
- **Signature** : `async (prompt:String) => any` (parse le JSON du
  premier bloc `text` de la réponse).
- **Effets** : `fetch` POST vers `https://api.anthropic.com/v1/messages`
  si `userApiKey()` est présente, sinon vers `API_URL`. Le proxy
  ne veut pas d'entêtes Anthropic (le worker les ajoute côté serveur).
- **Repli** : aucun ici ; l'appelant (`fetchAIQuestions`,
  `fetchAIWango`) capte l'exception, met `AI.err=true` et
  **retombe silencieusement** sur les banques locales via `pickFresh`.
- **Appelé par** : `fetchAIQuestions` (l.1470), `fetchAIWango` (l.1483).

### `triggerBamboozle(p, why)` — l.1571
- **Rôle** : sanction rare (3 miss d'affilée, échec du TTT, échec de la
  finale). Perd **la moitié** du score.
- **Effets** : abri Mudhut absorbe intégralement la sanction si `p.mudhut>0`.
  Sinon `p.score -= floor(score/2)`, log, `fx("bamboozle")`,
  `showStamp("You've been Bamboozled !")`, `endTurn`.
- **Appelé par** : `answer` (streak≥3), `tttFail` (l.1897).

### `climbLadder(p, n)` — l.1662
- **Rôle** : bouger le joueur sur l'Échelle de la Chance de `n` barreaux
  (positif ou négatif), avec clamp `[0, LADDER=6]`.
- **Effets** : marque les stations franchies (`p.pending = rung`) pour
  jeu ultérieur. Log différent pour monté vs. redescente.
- **Appelé par** : `spinWheel` (+1 systématique), `resolveWheel` (Ladder
  +2), `yankResult` (+1 sur succès).

### `exportGame() / importGame(ev)` — l.1436 / 1447
Cf. §3.4.

### `renderPodiums()` — l.2577
Rebuild le grid des podiums. Applique classes de bonus (Mudhut, Hopping,
Angel, Double, Shield), la barre de progression vers GOAL, l'échelle
(`.ladder`), les gages, et les animations de score (`animScore` via
`PREV`).

---

## 6. Le système de données

### 6.1 Forme de `DATA` (ligne 708)

Objet JSON stringifié, `const DATA = {…};` **sur une seule ligne** de
240 563 caractères (indispensable au parseur JSON de la skill
`bamboozle-patch`, qui capture entre `const DATA=` et `};\n`).

Structure par langue :

```
DATA = {
  fr: { Q, R, WQ, G, WHEEL, LV, B, F, H, YANK, DBL },
  en: { Q, R, WQ, G, WHEEL, LV, B, F, H, YANK, DBL },
  it: { Q, R, WQ, G, WHEEL, LV, B, F, H, YANK, DBL },
}
```

### 6.2 Formats exacts par catégorie

- **`Q` — Questions standard** : `Array<[question:String, answer:String]>`.
  Exemple `fr`:
  ```
  ["Quel réseau social est célèbre pour ses vidéos courtes et ses danses ?", "TikTok"]
  ```
- **`R` — Questions rétro / répliques cultes** : même schéma que `Q`.
  Exemple `fr`:
  ```
  ["« Je suis ton père. » — quel film ?", "Star Wars : L'Empire contre-attaque"]
  ```
- **`H` — Questions d'expert** : même schéma que `Q`. Utilisées par TTT
  question 3 et par la finale (questions 3 et 5).
- **`F` — Friends (spéciales)** : même schéma que `Q`.
- **`WQ` — Wicked Wango** : `Array<{t:String, x:String, ans:String}>`.
  `t` = étiquette catégorie en MAJUSCULES. Exemple :
  ```
  {"t":"RÉPLIQUE CULTE","x":"« Je suis ton père. » — De quel film ?","ans":"Star Wars, épisode V…"}
  ```
- **`G` — Google Cards** : `Array<{k, a?, t, x}>`. `k` ∈ `dare`,
  `boon`, `attack`, `random`... — pilote le comportement.
  Exemple :
  ```
  {"k":"dare","a":"pen","t":"LA VOIX DU WANGO","x":"Jusqu'à son prochain tour, le joueur parle EN CHANTANT."}
  ```
- **`WHEEL` — Faces de la Roue de Mayhem** : `Object` clefé par la
  somme des dés (`"2".."12"`), chaque valeur étant `{t:String, x:String}`.
  11 entrées (2 à 12).
- **`LV` — Paliers Wicked Wango** : `Array<{n:Number, g:Number, c:String, d:String}>`.
  7 entrées (`n=1..7`). `g` = gain de base, `c` = consigne affichée, `d` ∈
  `wq` (question Wango), `word` (mot à épeler à l'envers) — d'autres
  variantes possibles.
- **`B` — Défis bonus du tour** : `Array<String>`. Chaîne libre.
  Exemple `fr` : `"épeler la réponse à l'envers"`.
- **`YANK` — Épreuves physiques pour tirer la queue du Singe** :
  `Array<String>`. Ex : `"Tenir en équilibre sur un pied, 20 s"`.
- **`DBL` — Doubles de la Roue (événements rares)** :
  `Array<{k:String, t:String, x:String}>`. `k` ∈ `mirror`, `tribut`,
  `impot`, `shield`, `replay`, `goldrain`, `roulette`, `contract`.
  Le `k` pilote un `switch` dans `dblResolve` (l.1791).

### 6.3 Volumes actuels par langue

Mesuré depuis le `DATA` du fichier courant :

| Cat | `fr` | `en` | `it` |
|---|---|---|---|
| `Q`  | 777 | 412 | 457 |
| `R`  |  71 |  74 |  70 |
| `WQ` |  58 |  58 |  58 |
| `G`  |  17 |  17 |  17 |
| `WHEEL` | 11 (2→12) | 11 | 11 |
| `LV` |   7 |   7 |   7 |
| `B`  |  40 |  40 |  30 |
| `F`  | 168 | 170 | 172 |
| `H`  |  74 |  80 |  80 |
| `YANK` | 15 | 15 | 15 |
| `DBL` |  8 |   8 |   8 |

### 6.4 Parsing / re-sérialisation sans altération

C'est le contrat le plus subtil du projet. Voir `bamboozle-patch/scripts/patch_data.py` (§9) :

- On trouve exactement `const DATA=` (ligne 708) et le premier `};\n`
  qui la termine.
- On parse en Python avec `json.loads` (le contenu EST du JSON strict,
  pas du JS).
- On applique la transformation Python (add, dedupe, rewrite).
- On re-sérialise avec `json.dumps(data, ensure_ascii=False,
  separators=(', ', ': '))` — les séparateurs sont ceux d'origine et
  garantissent un round-trip exact.
- On réécrit le fichier atomiquement (temp + rename).
- `bamboozle-patch/verify.py` re-parse le JSON depuis le fichier final
  pour valider avant de rendre l'écriture visible.

Toute édition manuelle du bloc `DATA` (via `Edit` classique) est
**interdite** — la moindre chaîne mal échappée peut passer `node
--check` (le JS reste valide) mais casser le tirage.

---

## 7. Internationalisation

### 7.1 Organisation

- **`I18N`** est un objet `{ fr, en, it }` défini lignes 710–1400.
- `I18N.fr` est l'écriture pleine (la référence canonique).
- `I18N.en` est écrite en plein aussi, plus courte que `fr`.
- `I18N.it` est construit avec `Object.assign({}, I18N.en, {…})` :
  il **hérite** de l'anglais pour toute la structure (fonctions,
  formatters, clefs mineures) puis **surcharge** uniquement les
  chaînes visibles à l'utilisateur en italien.

Le commentaire ligne 419 (`ITALIEN : hérite de l'anglais pour la
structure, tout le visible est traduit`) marque cette convention.

- Sélection : `let LANG="fr"; const LANGS=["fr","en","it"];`
  `cycleLang()` (bouton topbar) fait tourner l'index.
- `T() => I18N[LANG]` renvoie le pack courant. `D() => DATA[LANG]`
  fait la même chose côté banques.

### 7.2 Ajouter une langue

1. Ajouter une entrée `DATA["xx"] = { Q, R, WQ, G, WHEEL, LV, B, F, H, YANK, DBL }`.
2. Ajouter une entrée `I18N["xx"]`. Deux options :
   - Écrire tout en plein (comme `fr` et `en`).
   - Utiliser `Object.assign({}, I18N.en, {…})` et surcharger le visible
     (comme `it`).
3. Ajouter `"xx"` dans `LANGS` (l.1404). Le bouton `cycleLang()` fera
   tourner automatiquement.
4. Adapter `fmt(n)` (l.1522) pour le locale numérique si besoin :
   actuellement `"fr-FR"` si `LANG==="fr"`, sinon `"en-US"`.

### 7.3 Ce qu'il faut traduire

- Toutes les chaînes courtes (titres, boutons, bandeaux).
- Les **fonctions** formatteuses (`diffL:d=>…`, `first:n=>…`,
  `turn:(n,h)=>…`, etc.) : elles se comportent comme des templates.
- Les banques `Q/R/H/F/WQ/YANK/B/G/DBL/WHEEL/LV` de `DATA`.
- `secAnswers` (réponses attendues à l'énigme secrète) doit rester
  dans la même norme que `norm()` (`NFD`, sans accents, ASCII).

### 7.4 Ce qu'il ne faut PAS traduire

- Les identifiants CSS/DOM (`#logwrap`, `.pod`, etc.).
- Les valeurs `k` dans `DATA.xx.G` et `DATA.xx.DBL` (`"dare"`,
  `"boon"`, `"mirror"`, `"tribut"`, …) : ce sont des clefs pour un
  `switch` en JS. Seul `t` et `x` sont visibles.
- Les clefs de `WHEEL` (`"2".."12"`) : elles indexent la somme des dés.
- Les clefs d'`I18N` (`goal`, `first`, `turn`, `bz3`, …) — un renommage
  casse toutes les callsites.

---

## 8. Intégration API

### 8.1 Chemin complet d'un appel

1. **Déclencheur** : `topUpAI()` (l.1401) est appelé au démarrage
   (`renderSetup` fin de fichier) puis à chaque `drawQuestion`
   (l.1549). Il vérifie :
   - si `AI.q.length < 6` et pas déjà en vol → `fetchAIQuestions()`.
   - si `AI.w.length < 4` et pas déjà en vol → `fetchAIWango()`.

2. **Construction du prompt** : `fetchAIQuestions` (l.1470) construit
   un prompt selon la langue courante et la difficulté (`AI.diff` ∈
   `facile|normal|difficile`). Le prompt exclut les 30 derniers sujets
   dans `AI.seen`.

3. **Envoi** : `askClaude(prompt)` (l.1461) :
   - Si `userApiKey()` non vide : POST direct à
     `https://api.anthropic.com/v1/messages` avec entêtes
     `x-api-key`, `anthropic-version:2023-06-01`,
     `anthropic-dangerous-direct-browser-access:true`.
   - Sinon : POST au **proxy Cloudflare Worker**
     `https://bamboozle-ai.sam1chirat.workers.dev` (`API_URL`, l.1499).
     Le worker ajoute les entêtes Anthropic et détient la clé serveur.

4. **Réponse** : Claude renvoie un `content[]`. `askClaude` concatène
   les blocs `type==="text"`, retire les fences ```json``` éventuels,
   `JSON.parse` et renvoie l'objet.

5. **Traitement** :
   - `fetchAIQuestions` pousse les tuples valides dans `AI.q` (couples
     `[q, a]`) et mémorise 60 caractères du sujet dans `AI.seen`.
   - `fetchAIWango` pousse les objets `{t,x,ans}` valides dans `AI.w`.

6. **Utilisation** : dans `drawQuestion` (l.1552), si `AI.q` non vide
   et que la première question n'est pas déjà dans `SEEN`, on la
   consomme, on marque `seenMark`, et on court-circuite `pickFresh`.
   Idem pour Wango dans `drawWQ` (mécanisme équivalent).

### 8.2 Repli silencieux

- Une exception réseau (`fetch` rejette, JSON invalide, timeout de
  bord) est **capturée** dans le `try/catch` de `fetchAIQuestions`
  et `fetchAIWango`. `AI.err = true` est levé, `console.warn` en trace,
  et **c'est tout**.
- La partie continue : `drawQuestion` détectera que `AI.q` est vide et
  passera à `pickFresh(D().Q, S.usedQ)` — banque locale.
- Aucun message d'erreur n'est présenté à l'utilisateur : la skill
  `bamboozle-playtest` (mode par défaut) simule exactement ce cas en
  interceptant `page.route("**workers.dev**", route.abort())`.

### 8.3 Points où un échec est capté

- `askClaude` : ne capte pas — laisse remonter. C'est l'appelant qui
  décide.
- `fetchAIQuestions` (l.1470) et `fetchAIWango` (l.1483) : chacun a un
  `try/catch` unique qui absorbe **toute** exception.
- `topUpAI` : ne capte rien — il ne peut échouer que si les fetch
  échouent, et ceux-ci sont déjà protégés.
- `console.warn` conserve la trace, mais aucun `console.error` (par
  design : la skill playtest fail sur `console.error`).

---

## 9. Les garde-fous (skills)

Trois skills installées dans `~/.claude/skills/`, chacune un
`SKILL.md` + un dossier `scripts/`. Elles ne sont pas des fichiers du
repo `bamboozled` — mais aucun changement ne se fait sans elles.

### 9.1 `bamboozle-patch`

- **Rôle** : garant unique de la modification de `index.html`.
- **Fichiers** :
  - `SKILL.md` — spec de la skill.
  - `scripts/verify.py` — bibliothèque de vérifications.
  - `scripts/patch_replace.py` — remplacement de chaîne assertif (CLI + lib).
  - `scripts/patch_data.py` — mutation Python de la constante `DATA`.
- **Contrôles bloquants à chaque écriture** (via `verify.verify_all(candidate)`) :
  1. Le HTML contient **exactement un** bloc `<script>`.
  2. `node --check` passe sur le contenu extrait du script.
  3. La chaîne `workers.dev` apparaît **exactement 1 fois** dans le fichier.
  4. `const DATA=…;` reste parsable en JSON strict.
  5. Taille finale ≥ 300 000 octets.
- **Assertivité** : `patch_replace` refuse tout remplacement dont
  `src.count(old) != count` (par défaut 1) — évite les remplacements
  ambigus ou multiples.
- **Format `DATA`** : le round-trip utilise `separators=(', ', ': ')`
  pour reproduire le fichier tel quel.
- **Écriture atomique** : validation sur `.tmp`, puis `os.rename`.
  Aucun état intermédiaire visible.

### 9.2 `bamboozle-questions`

- **Rôle** : contrôle qualité éditoriale des banques `Q/H/R/F/WQ`.
- **Fichiers** :
  - `SKILL.md` — spec.
  - `scripts/core.py` — normalisation NFKD sans accents, détection
    doublons, faits périssables.
  - `scripts/audit.py` — analyse lecture seule (exit 1 si bloquant).
  - `scripts/add.py` — ajout contrôlé, dry-run par défaut, écriture
    déléguée à `bamboozle-patch`.
- **Contrôles bloquants** (chacun refuse l'ajout, `--force` outrepasse) :
  - `strict_dup` : mêmes question et réponse (après normalisation).
  - `fuzzy_dup` : réponse identique + question proche
    (`SequenceMatcher.ratio() > 0.72`).
  - `answer_in_question` : la réponse (sans articles) apparaît dans
    l'énoncé — devinable.
  - `multi_question` : l'énoncé contient plus d'un `?`.
  - `answer_too_long` : réponse > 75 caractères.
  - `duplicate_in_lot` : deux entrées identiques dans le fichier
    d'ajout.
- **Signalements non bloquants** :
  - `perishable` : `actuel/attuale/current`, `record`, `depuis/dal/since`,
    superlatifs mondiaux, années > 2015.
  - `cross_lang_answer_collision` : même réponse normalisée dans la
    même catégorie d'une autre langue (indication, jamais blocage).
- **Ce qui est explicitement HORS scope** : rapprochement inter-langues
  par similarité, mesure structurelle, `WQ` traité comme `{x,ans}` sans
  vérification par sous-type.

### 9.3 `bamboozle-playtest`

- **Rôle** : validation runtime avant commit. Silencieux si OK,
  bavard et exit non-zéro sinon.
- **Fichiers** : `SKILL.md` + `scripts/playtest.mjs` (unique).
- **Prérequis projet** : `package.json` avec `playwright`,
  `node_modules/`, `captures/`, `captures/baseline.json` (git-ignorés).
- **Modes** :
  - `scenario` (défaut) : partie 3 joueurs (Alice/Bob/Charlie), 6 tours,
    proxy Cloudflare bloqué par `page.route(…, route.abort())`. Vérifie
    zéro `console.error` et zéro `pageerror`.
  - `freshness` : `fr / en / it × Q / H / R / F / WQ`, `--draws` (400
    par défaut) tirages consécutifs par banque. Vérifie que le premier
    doublon tombe **exactement à `bank.length`**, jamais avant.
  - `both` : les deux.
  - `--live` : opt-in, laisse passer le proxy et consomme des jetons
    Anthropic.
- **Serveur** : `python3 -m http.server <port> --bind 127.0.0.1`
  (port haut vérifié libre, kill propre en fin).
- **Captures** : hash SHA-256 (16 hex) écrit dans `captures/baseline.json`.
  Trois issues possibles : `match`, `new`, `CHANGED` (warning, exit
  code inchangé). `--update-baseline` fige les hashes courants.

---

## 10. Pièges rencontrés (bugs récurrents)

Ces bugs sont revenus au moins deux fois. Chacun a sa contre-mesure
inscrite dans le fichier ; ne pas les retirer sans lire ce paragraphe.

### #B1 — Le bandeau EN FEU recouvre les boutons

- **Symptôme** : à la partie Paradise Pond avec un streak `≥3`,
  `#banner` (variant `.fire`) recouvre le bouton d'action en bas de la
  carte. Le jeu se bloque.
- **Cause première** : `#banner` était `position:fixed;bottom:var(--journal-h)`.
  Le padding-bottom réservé sur `body` (via `--banner-max-h:80px`) ne
  couvrait pas toujours la hauteur réelle du contenu du bandeau.
- **Correctif** :
  - `#banner` est passé à `position:relative`.
  - `banner()` en JS le déplace juste après `#podiums` avant de
    l'afficher (`insertBefore` implicite).
  - `--banner-max-h` est conservée mais marquée « obsolète » — ne pas
    la supprimer pour éviter tout `calc()` orphelin dans une refonte
    partielle.
- **Fichier** : commits `e847954` (correctif d'urgence) puis `f620533`
  (refonte pile-bas). Ligne 597 pour `#banner{position:relative}`.

### #B2 — Régression pile-bas (empilement)

- **Symptôme** : au moins trois régressions successives — le bouton
  d'action masqué par `#logwrap`, ou padding trop grand qui pousse le
  contenu hors écran, ou l'inverse.
- **Cause** : le padding-bottom mis sur `body` est mangé par le
  comportement `overflow` du root sur mobile. Il faut le porter sur un
  bloc en flux normal (`#stage`).
- **Correctif structurel (commit `f620533`)** :
  - Variable CSS `--pile-bas` initialisée à `96px`.
  - IIFE `initBottomPileObserver()` (l.2864) crée un `ResizeObserver`
    sur `#logwrap` qui écrit sa hauteur dans `--pile-bas` au runtime.
  - `#stage{padding-bottom:calc(var(--pile-bas) + 24px)}` (l.147).
  - `body{padding-bottom:0}` (explicite, ligne 42).
- **Belt-and-braces** : si l'observer manque, fallback `220px`,
  généreux, plutôt qu'un chevauchement.
- **Test permanent** : `test-bottom-layout.mjs` dans la skill
  playtest — reproduit l'état exact d'une capture 13:25 (Paradise Pond
  + streak ×3 + défi + journal 2 entrées, safe-area 59+34) et vérifie
  non-chevauchement + accessibilité au clic.

### #B3 — Safe-area haute (titre coupé par la barre d'état iOS)

- **Symptôme** : sur iPhone (Safari), le titre `BAMBOOZLED` remonte
  sous la Dynamic Island. Bug revenu 3 fois.
- **Cause** : `padding-top:var(--sat)` seul, sans plancher. Safari iOS
  peut résoudre `env(safe-area-inset-top)` à `0px` (mise à jour, cache
  CDN, viewport-fit manquant).
- **Correctif** (2 couches) :
  1. `<meta name="viewport" content="… viewport-fit=cover">` (ligne 5).
  2. `body{padding-top:max(20px,var(--sat))}` (l.42).
  3. `.topbar{padding:max(30px,calc(10px + var(--sat))) 12px 0}` (l.340).
- **Test permanent** : `test-bottom-layout.mjs` assertion « premier
  élément visible ≥ 59 px » sur DEUX cibles : `topbar` ET `header h1`.
  Si l'un remonte, le test échoue avant que l'utilisateur découvre.

### #B4 — Bouton primaire perdu dans la ligne

- **Symptôme** : sur la carte de question (`.card.live`), le bouton
  « Voir la réponse » + « OK » + « Miss » se partagent la même ligne,
  aucun ne domine — l'animateur cherche.
- **Correctif** : dans `.btnrow`, le **premier** bouton prend
  `flex:1 1 100%` (toute la largeur), les suivants
  `flex:1 1 0;min-width:0` (partagent la ligne suivante). CSS lignes
  152–155.
- **Piège** : ajouter un `.btnrow` sans se rendre compte que le
  premier enfant sera pleine largeur. Vérifier l'ordre.

### #B5 — Appui long sélectionne le texte / ouvre le menu iOS

- **Symptôme** : sur iPhone, appui long sur un podium ou une question
  ouvre le menu Copier/Définir/Partager.
- **Correctif** :
  ```
  body{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
  input,textarea,#logwrap,#logwrap *{
    -webkit-user-select:auto;user-select:auto;-webkit-touch-callout:default}
  ```
  Sélection autorisée UNIQUEMENT dans les champs (`#pname`,
  `#apiKeyInput`) et dans le journal (l'animateur peut vouloir
  copier).

### #B6 — Champ mot de passe en fond blanc opaque

- **Symptôme** : le champ « Clé de régie » (type `password`) apparaît
  en blanc pur, cassant la maquette violet nuit.
- **Cause** : la règle stylée ne visait que `input[type=text]`.
- **Correctif** : `input[type=text],input[type=password]{…}` (l.638–640).
  Toute nouvelle règle d'input doit inclure `password`.

### #B7 — 3 appels orphelins à `updAIBadge()` bloquent tout

- **Contexte** : lors d'un chantier de refonte, la fonction
  `updAIBadge()` a été supprimée mais trois callsites sont restés
  (drawQuestion, drawWQ, init boot). Quand `AI.q` avait des questions
  préchargées, la première question levait une `TypeError` non captée
  au démarrage → `newGame` ne terminait pas → `tryStart` avait déjà
  vidé `setupNames` → clic suivant sur « Lancer » → « il faut au moins
  2 candidats » → clic sur `✕` d'un candidat inexistant → crash de la
  liste.
- **Correctif** : suppression des trois appels résiduels.
- **Leçon** : quand on supprime une fonction, `grep` global obligatoire.
  Bien qu'il n'y ait pas d'ESM, `node --check` sur le script extrait
  ne détecte pas une référence à une fonction indéfinie (JS
  dynamique). Un `console.error` en runtime la ferait détecter par la
  skill playtest si les modes couvrent le chemin — d'où l'importance
  d'enrichir le scénario au fur et à mesure.

### #B8 — Roue : célébration de barreau + fait de fatigue

- **Contexte** : chaque tour de roue faisait grimper l'Échelle de la
  Chance ET affichait une célébration animée. En vraie partie, cet
  effet se déclenche 6 fois par joueur ; il fatigue l'écran.
- **Correctif** : la célébration a été supprimée. La montée est
  toujours loguée textuellement dans le journal. Voir commit `764f0fe`.
- **Leçon** : distinguer clairement « moment rare qu'on célèbre » de
  « progression continue qu'on trace ». Un événement fréquent ne doit
  jamais interrompre le rythme.

### #B9 — Portail secret : mot coupé au milieu

- **Contexte** : `#secret .sectitle` (nom : `ELASMAR`, 8 lettres)
  passait à la ligne au milieu du mot sur écran étroit.
- **Correctif** : `<span class="nobrk">` autour du mot, avec
  `white-space:nowrap` (l.416). À généraliser à tout titre court dont
  la coupure est incorrecte.

### #B10 — Faits périssables (dérive éditoriale lente)

- **Symptôme** : les questions vieillissent — présidents en poste,
  détenteurs de records, dates récentes.
- **Contre-mesure** : la skill `bamboozle-questions` marque
  `perishable` (non bloquant) sur détection lexicale. Le documentaire
  humain (checklist §SKILL) précise les cas à refuser malgré la non-
  détection. Voir aussi la campagne de nettoyage `61215a1` en `fr` et
  `86d5ba4` en `it`.

---

## Annexe A — Ce qu'il faut recréer pour un nouveau jeu

Un checklist pratique, dans l'ordre :

1. Cloner la structure `<head>` (métas iOS/PWA + fonts Google + `<style>`).
2. Copier `:root { --ink…--sar }` et les alias rétro-compat, ajuster
   la palette.
3. Copier le squelette DOM (12 divs statiques + topbar + header + logwrap).
4. Copier les IIFE de fin (boot + `initBottomPileObserver`) — c'est
   la couche mobile-safe.
5. Réécrire `DATA` avec les catégories pertinentes du nouveau jeu.
6. Réécrire `I18N.fr` (référence), puis `en` en plein, puis `it` avec
   `Object.assign({}, I18N.en, {…})`.
7. Réécrire la logique de tours (`newGame`, `answer`, `endTurn`,
   `nextPlayer`) — c'est le squelette réutilisable ; les scènes
   (`ring`, `wango`, `card`, `duel`) sont spécifiques et peuvent être
   supprimées ou remplacées.
8. Garder `SEEN` (mémoire longue localStorage) et `pickFresh` — c'est
   la garantie de fraîcheur.
9. Installer les trois skills en les adaptant au nom du nouveau
   projet : le contrat `verify_all` (script unique, `workers.dev`
   compté, DATA parsable, taille min) est directement recyclable.
10. Installer `bamboozle-playtest` et lui donner un smoke scenario +
    un test freshness — c'est le filet qui rattrape les régressions.

## Annexe B — Informations que je n'ai pas pu vérifier

- Le contenu exact du **worker Cloudflare** (`bamboozle-ai.sam1chirat.workers.dev`)
  n'est pas dans ce repo. Il est référencé une seule fois (l.1499) et
  son code source vit ailleurs (probablement un autre repo ou une
  console Cloudflare). Toute réplique doit refaire ce worker avec :
  proxy POST vers `https://api.anthropic.com/v1/messages`, ajout des
  entêtes `x-api-key` (secret Cloudflare) et `anthropic-version:
  2023-06-01`, retour brut de la réponse Anthropic.
- Le `test-bottom-layout.mjs` référencé dans le commit `f620533`
  n'est pas visible dans le layout des skills que j'ai lu ; il est
  probablement intégré dans `bamboozle-playtest/scripts/playtest.mjs`
  (mode scenario) plutôt qu'en fichier séparé. À vérifier au moment
  d'exécuter la skill.
