#!/usr/bin/env node
/*
 * playtest.mjs — validation runtime avant commit (SPEC §8.4).
 *
 * Modes :
 *   scenario  — 3 runs : (1) EMI bots=weak seed=42 joueur juste ; (2) EMI
 *               bots=strong seed=43 joueur faux ; (3) mat=croissance
 *               bots=strong seed=44 joueur faux. Zéro pageerror partout.
 *   gens      — dans le contexte de la page, tire 500 échantillons par
 *               générateur (GEN emi + croissance) et vérifie 0 doublon
 *               et cohérence cat ↔ GEN_MAT.
 *   srs       — après mauvaise réponse sur X, X en boîte 0 et resort en
 *               priorité à la reprise.
 *   layout    — safe-area 59+34 émulée, viewport iPhone SE, premier
 *               élément visible >= 59 px, bouton Suivant cliquable.
 *   all       — enchaîne les quatre.
 *
 * Options :
 *   --update-baseline   fige les hashes de captures/baseline.json
 *   --headed            désactive le headless (debug visuel)
 *   --keep-server       ne kill pas le serveur en fin (debug)
 *
 * Serveur : python3 -m http.server sur un port haut libre, tué à la
 * sortie. Aucun accès réseau externe (le jeu n'a pas de worker).
 */

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { chromium } from "playwright";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import net from "node:net";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = dirname(__dirname);
const CAPTURES_DIR = join(REPO, "captures");
const BASELINE = join(CAPTURES_DIR, "baseline.json");

const args = process.argv.slice(2);
const modes = args.filter(a => !a.startsWith("--"));
const flags = new Set(args.filter(a => a.startsWith("--")));
const UPDATE_BASELINE = flags.has("--update-baseline");
const HEADED = flags.has("--headed");
const KEEP_SERVER = flags.has("--keep-server");

const HOST = "127.0.0.1";

async function pickFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, HOST, () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
  });
}

async function startHttpServer(port) {
  const p = spawn("python3", ["-m", "http.server", String(port), "--bind", HOST], {
    cwd: REPO,
    stdio: ["ignore", "ignore", "pipe"],
    detached: false,
  });
  // Attend que le serveur soit prêt.
  const deadline = Date.now() + 4000;
  while (Date.now() < deadline) {
    try {
      const ok = await new Promise((res) => {
        const sk = net.connect(port, HOST, () => { sk.end(); res(true); });
        sk.on("error", () => res(false));
      });
      if (ok) return p;
    } catch (_) { /* retry */ }
    await sleep(80);
  }
  throw new Error("serveur http.server pas prêt dans 4 s");
}

function stopHttpServer(p) {
  if (!p) return;
  try { p.kill("SIGTERM"); } catch (_) {}
}

function baselineLoad() {
  if (!existsSync(BASELINE)) return {};
  try { return JSON.parse(readFileSync(BASELINE, "utf8")); }
  catch (_) { return {}; }
}
function baselineSave(obj) {
  if (!existsSync(CAPTURES_DIR)) mkdirSync(CAPTURES_DIR, { recursive: true });
  writeFileSync(BASELINE, JSON.stringify(obj, null, 2) + "\n");
}

async function capture(page, name, baseline, results) {
  const buf = await page.screenshot({ fullPage: false });
  const h = createHash("sha256").update(buf).digest("hex").slice(0, 16);
  const prev = baseline[name];
  if (!prev) {
    results.push(`  NEW    ${name}  h=${h}`);
    baseline[name] = h;
  } else if (prev !== h) {
    results.push(`  CHANGED ${name}  ${prev} → ${h}`);
    if (UPDATE_BASELINE) baseline[name] = h;
  } else {
    results.push(`  match  ${name}  h=${h}`);
  }
}

// ---------------------------------------------------------------- helpers
async function bootAndSetup(page, url) {
  await page.goto(url);
  await page.evaluate(() => localStorage.clear());
  await page.goto(url); // reload post clear
  // Boot
  await page.locator('#boot [data-act="bootStart"]').click();
  // Setup → Lancer
  await page.locator('[data-act="startShow"]').click();
  // Intro coup d'envoi
  await page.locator('[data-act="introOK"]').click();
  await page.waitForFunction(() => window.eval && window.eval("S && S.phase === 'q'"));
}

async function getState(page) {
  return await page.evaluate(() => window.eval("JSON.parse(JSON.stringify(S))"));
}

async function answerJuste(page) {
  const info = await page.evaluate(() => {
    const S = window.eval("S");
    return { phase: S.phase, fmt: S.qFmt, manche: S.manche, a: S.q ? S.q.a : null, good: S.q ? (S.q.good || null) : null, steps: S.q ? (S.q.steps || null) : null, choices: S.q ? (S.q.choices || null) : null };
  });
  if (info.fmt === "qcmm") {
    for (const i of info.good) await page.locator(`[data-act="mPick"][data-v="${i}"]`).click();
    await page.locator('[data-act="mValid"]').click();
  } else if (info.fmt === "qcm" || info.fmt === "qcm3") {
    await page.locator(`.choices > button[data-v="${info.a}"]`).first().click();
  } else if (info.fmt === "vf") {
    await page.locator(`[data-act="answer"][data-v="${info.a ? "true" : "false"}"]`).click();
  } else if (info.fmt === "sens") {
    await page.locator(`[data-act="answer"][data-v="${info.a}"]`).click();
  } else if (info.fmt === "ordre") {
    for (let k = 0; k < info.steps.length; k++) {
      await page.locator(`[data-act="order"][data-v="${k}"]`).click();
    }
    await page.locator('[data-act="orderValid"]').click();
  } else if (info.fmt === "calc") {
    // Générateur : a=0 par convention.
    await page.locator(`.choices > button[data-v="${info.a}"]`).click();
  } else if (info.fmt === "ouverte") {
    // Maître : reveal puis Su.
    await page.locator('[data-act="reveal"]').click();
    await page.locator('[data-act="grade"][data-v="su"]').click();
    return;
  }
}

async function answerFaux(page) {
  const info = await page.evaluate(() => {
    const S = window.eval("S");
    return { fmt: S.qFmt, a: S.q ? S.q.a : null, good: S.q ? (S.q.good || null) : null, n: S.q && S.q.choices ? S.q.choices.length : 0, steps: S.q ? (S.q.steps || null) : null };
  });
  if (info.fmt === "qcmm") {
    // Coche une seule proposition fausse : tout ou rien → faux garanti.
    const bad = [...Array(info.n).keys()].find(i => !info.good.includes(i));
    await page.locator(`[data-act="mPick"][data-v="${bad}"]`).click();
    await page.locator('[data-act="mValid"]').click();
  } else if (info.fmt === "qcm" || info.fmt === "qcm3") {
    const bad = (info.a + 1) % 4;
    await page.locator(`.choices > button[data-v="${bad}"]`).first().click();
  } else if (info.fmt === "vf") {
    await page.locator(`[data-act="answer"][data-v="${info.a ? "false" : "true"}"]`).click();
  } else if (info.fmt === "sens") {
    const bad = ({ up: "down", down: "up", same: "up", ambig: "down" })[info.a] || "up";
    await page.locator(`[data-act="answer"][data-v="${bad}"]`).click();
  } else if (info.fmt === "ordre") {
    // Répond dans un ordre inverse (garanti faux si n>=2).
    for (let k = info.steps.length - 1; k >= 0; k--) {
      await page.locator(`[data-act="order"][data-v="${k}"]`).click();
    }
    await page.locator('[data-act="orderValid"]').click();
  } else if (info.fmt === "calc") {
    const bad = (info.a + 1) % 4;
    await page.locator(`.choices > button[data-v="${bad}"]`).click();
  } else if (info.fmt === "ouverte") {
    // Reveal puis Pas su pour couper court.
    await page.locator('[data-act="reveal"]').click();
    await page.locator('[data-act="grade"][data-v="pasSu"]').click();
    return;
  }
}

async function tapNext(page) {
  const btn = page.locator('[data-act="next"]').first();
  if (await btn.count() === 0) return false;
  await btn.click();
  return true;
}

async function playThrough(page, strategy, maxIter = 300, recorder = null) {
  const seenIds = new Set();
  for (let i = 0; i < maxIter; i++) {
    const S = await getState(page);
    if (!S) return;
    if (recorder && S && S.q && S.q.id && !seenIds.has(S.q.id)) {
      seenIds.add(S.q.id);
      recorder.push({ id: S.q.id, fmt: S.qFmt, cat: S.q.cat, manche: S.manche });
    }
    if (S.screen === "bilan") return;

    if (S.phase === "intro") {
      await page.locator('[data-act="introOK"]').click();
      await sleep(200);
      continue;
    }

    if (S.manche === "fatal" && S.phase === "q") {
      // Cible joueur seulement.
      const isPlayer = (S.fatal.cur === 0 && S.fatal.a === 0) || (S.fatal.cur === 1 && S.fatal.b === 0);
      if (isPlayer) {
        if (strategy === "juste") await answerJuste(page);
        else await answerFaux(page);
        await sleep(1400); // verdictHide + nextFatalQ
      } else {
        await sleep(1400);
      }
      continue;
    }

    if (S.manche === "etoile" && S.phase === "guess") {
      if (!S.etoile.proposed) {
        // Propose le vrai nom pour juste, un nom incorrect pour faux.
        const proposal = strategy === "juste" ? S.etoile.name : "xxx-inconnu";
        await page.locator('#etoileGuess').fill(proposal);
        await page.locator('[data-act="etoilePropose"]').click();
        await sleep(200);
        continue;
      }
      await page.locator('[data-act="etoileNext"]').click();
      await sleep(200);
      continue;
    }

    if (S.phase === "q" || S.phase === "duel") {
      if (strategy === "juste") await answerJuste(page);
      else await answerFaux(page);
      await sleep(150);
      await tapNext(page);
      await sleep(200);
      continue;
    }

    if (S.phase === "elim") {
      await tapNext(page);
      await sleep(180);
      continue;
    }

    // maître normal : phase="q" ouverte déjà géré via answerJuste/Faux.
    if (S.manche === "maitre" && S.phase === "q") {
      if (strategy === "juste") await answerJuste(page);
      else await answerFaux(page);
      await sleep(200);
      continue;
    }

    // Phase inattendue → sortie
    return;
  }
}

// -------------------------------------------------------- captures helpers
async function withPage(browser, url, baseUrl, callback) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 }, // iPhone 15 Pro logique
    deviceScaleFactor: 3,
  });
  const page = await context.newPage();
  const pageErrors = [];
  const consoleErrors = [];
  page.on("pageerror", e => pageErrors.push(String(e)));
  page.on("console", msg => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
  try {
    await callback(page, pageErrors, consoleErrors);
  } finally {
    await context.close();
  }
}

// ------------------------------------------------------------ scenario mode
async function runScenario(baseUrl, browser, baseline, results) {
  results.push("[scenario]");
  const errs = [];

  // Run 1 : bots=weak, seed=42, joueur juste → doit atteindre Maître.
  await withPage(browser, `${baseUrl}/index.html?seed=42&bots=weak`, baseUrl, async (page, pageErrors) => {
    await bootAndSetup(page, `${baseUrl}/index.html?seed=42&bots=weak`);
    await capture(page, "scenario-1-envoi-q1", baseline, results);
    await playThrough(page, "juste", 400);
    await capture(page, "scenario-1-bilan", baseline, results);
    const S = await getState(page);
    const bilanOK = S && S.screen === "bilan" && (S.phase === "victory" || S.phase === "over");
    if (!bilanOK) errs.push("scenario 1 : n'a pas atteint le bilan");
    if (pageErrors.length) errs.push("scenario 1 pageerrors: " + pageErrors.join(" | "));
    results.push(`  → screen=${S?.screen} phase=${S?.phase} pageerrors=${pageErrors.length}`);
  });

  // Run 2 : bots=strong, seed=43, joueur faux → joueur doit être out.
  await withPage(browser, `${baseUrl}/index.html?seed=43&bots=strong`, baseUrl, async (page, pageErrors) => {
    await bootAndSetup(page, `${baseUrl}/index.html?seed=43&bots=strong`);
    await capture(page, "scenario-2-envoi-q1", baseline, results);
    await playThrough(page, "faux", 400);
    await capture(page, "scenario-2-bilan", baseline, results);
    const S = await getState(page);
    const joueurOut = S && S.players && S.players[0].out;
    if (!joueurOut) errs.push("scenario 2 : joueur devait être éliminé");
    if (pageErrors.length) errs.push("scenario 2 pageerrors: " + pageErrors.join(" | "));
    results.push(`  → screen=${S?.screen} phase=${S?.phase} joueur.out=${joueurOut} pageerrors=${pageErrors.length}`);
  });

  // Run 3 : mat=croissance, bots=weak, seed=44, joueur juste → le joueur
  // atteint le coup fatal, ce qui exerce au moins un générateur calc et
  // permet de vérifier le filtrage par GEN_MAT.
  const CROISSANCE_CATS = ["residu","kaldor","harrod","solow","mrw","convergence","ak","romer","aghion","malthus","olg","institutions"];
  await withPage(browser, `${baseUrl}/index.html?seed=44&bots=weak`, baseUrl, async (page, pageErrors) => {
    const url = `${baseUrl}/index.html?seed=44&bots=weak`;
    await page.goto(url);
    await page.evaluate((cats) => {
      localStorage.clear();
      localStorage.setItem("emi.settings.v1", JSON.stringify({
        mat: "croissance", cats: cats, sfx: false, express: false,
      }));
    }, CROISSANCE_CATS);
    await page.goto(url);
    await page.locator('#boot [data-act="bootStart"]').click();
    await page.locator('[data-act="startShow"]').click();
    await page.locator('[data-act="introOK"]').click();
    await page.waitForFunction(() => window.eval && window.eval("S && S.phase === 'q'"));
    await capture(page, "scenario-3-envoi-q1", baseline, results);
    const seen = [];
    await playThrough(page, "juste", 400, seen);
    await capture(page, "scenario-3-bilan", baseline, results);
    const S = await getState(page);
    const bilanOK = S && S.screen === "bilan";
    if (!bilanOK) errs.push("scenario 3 : n'a pas atteint le bilan");
    if (S && S.mat !== "croissance") errs.push(`scenario 3 : S.mat="${S?.mat}" (attendu "croissance")`);
    // Vérifie que toutes les questions vues (items bank ET calc générés)
    // sont bien de la matière croissance. seen est peuplé pendant playThrough.
    const GEN_MAT_JSON = await page.evaluate(() => JSON.stringify(window.eval("GEN_MAT")));
    const CATS_JSON = await page.evaluate(() => JSON.stringify(window.eval("DATA.CATS")));
    const GEN_MAT_OBJ = JSON.parse(GEN_MAT_JSON);
    const CATS_OBJ = JSON.parse(CATS_JSON);
    let calcTotal = 0, calcForeign = [], bankForeign = [];
    for (const q of seen) {
      if (typeof q.id !== "string") continue;
      if (q.id.startsWith("calc-")) {
        calcTotal++;
        const name = q.id.split("-")[1];
        if (GEN_MAT_OBJ[name] !== "croissance") calcForeign.push(name);
      } else {
        const catMat = CATS_OBJ[q.cat] && CATS_OBJ[q.cat].mat;
        if (catMat !== "croissance") bankForeign.push(q.id);
      }
    }
    if (calcForeign.length) errs.push(`scenario 3 : générateurs non-croissance appelés : ${calcForeign.join(",")}`);
    if (bankForeign.length) errs.push(`scenario 3 : items hors matière : ${bankForeign.slice(0,3).join(",")}`);
    if (pageErrors.length) errs.push("scenario 3 pageerrors: " + pageErrors.join(" | "));
    results.push(`  → screen=${S?.screen} phase=${S?.phase} mat=${S?.mat} vues=${seen.length} calc=${calcTotal - calcForeign.length}/${calcTotal} pageerrors=${pageErrors.length}`);
  });

  // Run 4 : mat=mbf (Banque et marché), bots=weak, seed=45, joueur juste.
  // Exerce le QCM à réponses multiples (qcmm) : cocher les bonnes, valider.
  // Puis run 4b : même matière, bots=strong, joueur faux (une case fausse
  // cochée → tout ou rien → faux), qui doit finir éliminé.
  // Enfin 4c : fatal-probe mbf (aucun générateur calc) → qcm3 tirés des qcmm.
  const MBF_CATS = await (async () => {
    const d = JSON.parse(readFileSync(new URL("../data/data.json", import.meta.url), "utf-8"));
    return Object.keys(d.CATS).filter(c => d.CATS[c].mat === "mbf");
  })();
  async function bootMbf(page, url) {
    await page.goto(url);
    await page.evaluate((cats) => {
      localStorage.clear();
      localStorage.setItem("emi.settings.v1", JSON.stringify({ mat: "mbf", cats, sfx: false, express: false }));
    }, MBF_CATS);
    await page.goto(url);
    await page.locator('#boot [data-act="bootStart"]').click();
    await page.locator('[data-act="startShow"]').click();
    await page.locator('[data-act="introOK"]').click();
    await page.waitForFunction(() => window.eval && window.eval("S && S.phase === 'q'"));
  }
  await withPage(browser, `${baseUrl}/index.html?seed=45&bots=weak`, baseUrl, async (page, pageErrors) => {
    await bootMbf(page, `${baseUrl}/index.html?seed=45&bots=weak`);
    await capture(page, "scenario-4-envoi-q1", baseline, results);
    const first = await getState(page);
    if (first.qFmt !== "qcmm") errs.push(`scenario 4 : 1re question en ${first.qFmt} (attendu qcmm)`);
    else if (!(first.q.good.length >= 1 && first.q.good.length < first.q.choices.length)) errs.push("scenario 4 : good incohérent");
    const seen = [];
    await playThrough(page, "juste", 400, seen);
    await capture(page, "scenario-4-bilan", baseline, results);
    const S = await getState(page);
    if (!(S && S.screen === "bilan")) errs.push("scenario 4 : n'a pas atteint le bilan");
    const foreign = seen.filter(q => !q.id.startsWith("calc-") && !MBF_CATS.includes(q.cat));
    if (foreign.length) errs.push(`scenario 4 : items hors matière : ${foreign.slice(0,3).map(q => q.id).join(",")}`);
    const nQcmm = seen.filter(q => q.fmt === "qcmm").length;
    if (!nQcmm) errs.push("scenario 4 : aucun qcmm posé");
    if (pageErrors.length) errs.push("scenario 4 pageerrors: " + pageErrors.join(" | "));
    results.push(`  → screen=${S?.screen} phase=${S?.phase} mat=${S?.mat} vues=${seen.length} qcmm=${nQcmm} pageerrors=${pageErrors.length}`);
  });
  await withPage(browser, `${baseUrl}/index.html?seed=46&bots=strong`, baseUrl, async (page, pageErrors) => {
    await bootMbf(page, `${baseUrl}/index.html?seed=46&bots=strong`);
    await playThrough(page, "faux", 400);
    const S = await getState(page);
    if (!(S && S.players && S.players[0].out)) errs.push("scenario 4b : joueur devait être éliminé");
    const qcmmErr = (S && S.errors || []).filter(e => e.fmt === "qcmm");
    if (!qcmmErr.length || !qcmmErr.every(e => e.snap && Array.isArray(e.snap.choices))) errs.push("scenario 4b : erreurs qcmm sans snapshot");
    if (pageErrors.length) errs.push("scenario 4b pageerrors: " + pageErrors.join(" | "));
    results.push(`  → 4b screen=${S?.screen} joueur.out=${S?.players?.[0]?.out} erreurs qcmm=${qcmmErr.length} pageerrors=${pageErrors.length}`);
  });
  await withPage(browser, `${baseUrl}/index.html?seed=47`, baseUrl, async (page, pageErrors) => {
    await bootMbf(page, `${baseUrl}/index.html?seed=47`);
    const probe = await page.evaluate(() => {
      S.manche = "fatal"; S.qIdx = 0; S.fatal = { a: 0, b: 1, cur: 0 };
      S.clocks = [90000, 90000]; S.newlyRed = null; S.elimInfo = null;
      const out = [];
      for (let i = 0; i < 12; i++) {
        window.nextFatalQ();
        out.push({ fmt: S.qFmt, n: S.q.choices.length, a: S.q.a, cat: S.q.cat });
      }
      return out;
    });
    // Alternance calc (générateurs mbf) / qcm3 (tiré des qcmm) : tout doit
    // rester dans la matière mbf ; qcm3 = 3 choix, calc = 4 choix.
    const bad = probe.filter(x => !MBF_CATS.includes(x.cat) || !(x.a >= 0 && x.a < x.n)
      || (x.fmt === "qcm3" && x.n !== 3) || (x.fmt === "calc" && x.n !== 4) || (x.fmt !== "qcm3" && x.fmt !== "calc"));
    const nCalc = probe.filter(x => x.fmt === "calc").length;
    if (bad.length) errs.push(`scenario 4c fatal-probe mbf : ${bad.length} tirages invalides`);
    if (!nCalc) errs.push("scenario 4c fatal-probe mbf : aucun calc mbf tiré");
    if (pageErrors.length) errs.push("scenario 4c pageerrors: " + pageErrors.join(" | "));
    results.push(`  → 4c fatal-probe mbf : ${probe.length - bad.length}/${probe.length} valides · ${nCalc} calc`);
  });

  // Run 3b : fatal-probe. Boot en croissance, force S.manche="fatal" et
  // appelle nextFatalQ() N fois pour vérifier directement le filtrage
  // GEN_MAT sur des tirages calc effectifs (le run 3 naturel n'exerce
  // pas toujours le calc, car les weak bots capitulent avant le fatal).
  await withPage(browser, `${baseUrl}/index.html?seed=44`, baseUrl, async (page, pageErrors) => {
    const url = `${baseUrl}/index.html?seed=44`;
    await page.goto(url);
    await page.evaluate((cats) => {
      localStorage.clear();
      localStorage.setItem("emi.settings.v1", JSON.stringify({
        mat: "croissance", cats, sfx: false, express: false,
      }));
    }, CROISSANCE_CATS);
    await page.goto(url);
    await page.locator('#boot [data-act="bootStart"]').click();
    await page.locator('[data-act="startShow"]').click();
    await page.locator('[data-act="introOK"]').click();
    await page.waitForFunction(() => window.eval && window.eval("S && S.phase === 'q'"));
    // Injection d'état : bascule direct en coup fatal, joueur = a (index 0).
    await page.evaluate(() => {
      S.manche = "fatal";
      S.qIdx = 0;
      S.fatal = { a: 0, b: 1, cur: 0 };
      S.clocks = [90000, 90000];
      S.newlyRed = null; S.elimInfo = null;
    });
    const N = 24;
    const probe = await page.evaluate((N) => {
      const GEN_MAT = window.eval("GEN_MAT");
      const ids = [];
      for (let i = 0; i < N; i++) {
        window.nextFatalQ();
        const id = S && S.q ? S.q.id : null;
        const fmt = S && S.qFmt ? S.qFmt : null;
        ids.push({ id, fmt });
      }
      // Retour synchrone (pas de timers actifs vu qu'on ne clique pas).
      return { ids, GEN_MAT };
    }, N);
    const calcIds = probe.ids.filter(x => x.id && x.id.startsWith("calc-"));
    const foreign = calcIds.filter(x => {
      const name = x.id.split("-")[1];
      return probe.GEN_MAT[name] !== "croissance";
    });
    if (foreign.length) errs.push(`scenario 3b fatal-probe : ${foreign.length} générateurs non-croissance : ${foreign.map(x => x.id.split("-")[1]).slice(0,5).join(",")}`);
    if (calcIds.length < 6) errs.push(`scenario 3b fatal-probe : trop peu de calc tirés (${calcIds.length}/${N})`);
    if (pageErrors.length) errs.push("scenario 3b pageerrors: " + pageErrors.join(" | "));
    // Comptage des générateurs distincts exercés (idéal : couverture max = 11).
    const distinct = new Set(calcIds.map(x => x.id.split("-")[1]));
    results.push(`  → fatal-probe : ${calcIds.length}/${N} calc · ${distinct.size}/11 générateurs distincts · 0 hors matière`);
  });

  return errs;
}

// ------------------------------------------------------------- gens mode
// Exécute chaque générateur GEN 500 fois dans le contexte réel de la page
// et vérifie 0 doublon + cohérence cat ↔ GEN_MAT. Complète les tests JS
// isolés (vm) parce qu'il consomme le rng et les CATS du build effectif.
async function runGens(baseUrl, browser, baseline, results) {
  results.push("[gens]");
  const errs = [];
  await withPage(browser, baseUrl, baseUrl, async (page, pageErrors) => {
    await page.goto(`${baseUrl}/index.html?seed=1`);
    const stats = await page.evaluate(() => {
      const GEN = window.eval("GEN");
      const GEN_MAT = window.eval("GEN_MAT");
      const rng = window.eval("rng");
      const CATS = window.eval("DATA.CATS");
      const perGen = {};
      for (const name of Object.keys(GEN)) {
        let dups = 0, catMismatch = 0, aErr = 0;
        for (let i = 0; i < 500; i++) {
          const g = GEN[name](rng);
          const cs = g.choices.map((c) => String(c));
          if (new Set(cs).size !== 4) dups++;
          if (g.a !== 0) aErr++;
          const mat = CATS[g.cat] && CATS[g.cat].mat;
          if (mat !== GEN_MAT[name]) catMismatch++;
        }
        perGen[name] = { mat: GEN_MAT[name], dups, catMismatch, aErr };
      }
      return perGen;
    });
    for (const [name, s] of Object.entries(stats)) {
      if (s.dups) errs.push(`gens ${name}[${s.mat}]: ${s.dups}/500 doublons`);
      if (s.catMismatch) errs.push(`gens ${name}[${s.mat}]: ${s.catMismatch}/500 cat ↔ GEN_MAT incohérents`);
      if (s.aErr) errs.push(`gens ${name}[${s.mat}]: ${s.aErr}/500 avec a ≠ 0`);
    }
    const n = Object.keys(stats).length;
    const totalDup = Object.values(stats).reduce((a, s) => a + s.dups, 0);
    const totalCat = Object.values(stats).reduce((a, s) => a + s.catMismatch, 0);
    results.push(`  ${n} gens × 500 iter · dups=${totalDup} · catMismatch=${totalCat}`);
    if (pageErrors.length) errs.push("gens pageerrors: " + pageErrors.join(" | "));
  });
  return errs;
}

// ------------------------------------------------------------- srs mode
async function runSRS(baseUrl, browser, baseline, results) {
  results.push("[srs]");
  const errs = [];

  await withPage(browser, `${baseUrl}/index.html?seed=99&bots=strong`, baseUrl, async (page, pageErrors) => {
    await page.goto(`${baseUrl}/index.html?seed=99&bots=strong`);
    await page.evaluate(() => localStorage.clear());
    await page.goto(`${baseUrl}/index.html?seed=99&bots=strong`);
    await page.locator('#boot [data-act="bootStart"]').click();
    await page.locator('[data-act="startShow"]').click();
    await page.locator('[data-act="introOK"]').click();
    // Répond faux à la première question, capture l'id.
    const firstId = await page.evaluate(() => window.eval("S.q.id"));
    await answerFaux(page);
    await page.locator('[data-act="next"]').first().click();
    const srs = await page.evaluate(() => JSON.parse(localStorage.getItem("emi.srs.v1")));
    const card = srs && srs[firstId];
    // Post-J38 : la carte a été « ratée » selon l'algo courant.
    //   - SM-2   : reps=0, lapses ≥ 1, interval=1.
    //   - FSRS   : state ∈ {learning, relearning}, lapses ≥ 1.
    //   - legacy : box=0.
    let failed = false;
    if (card) {
      if (card.algo === "sm2")       failed = (card.reps | 0) === 0 && (card.lapses | 0) >= 1;
      else if (card.algo === "fsrs") failed = ["learning", "relearning"].includes(card.state) && (card.lapses | 0) >= 1;
      else                            failed = (card.box | 0) === 0;
    }
    if (!failed) {
      errs.push(`srs : après réponse fausse, ${firstId} devrait être en échec (obs: ${JSON.stringify(card)})`);
    }
    results.push(`  id=${firstId} algo=${card && card.algo} reps=${card && card.reps} lapses=${card && card.lapses}`);
    if (pageErrors.length) errs.push("srs pageerrors: " + pageErrors.join(" | "));
  });

  // pickDue (SPEC §5.2) : (a) parmi les échus, la carte la moins maîtrisée
  // sort toujours ; (b) entre ex æquo, la catégorie la plus faible est
  // tirée plus souvent (poids 1 + part non maîtrisée).
  await withPage(browser, `${baseUrl}/index.html?seed=7`, baseUrl, async (page, pageErrors) => {
    await bootAndSetup(page, `${baseUrl}/index.html?seed=7`);
    const r = await page.evaluate(() => {
      const now = Date.now(), DAY = 86400000;
      const card = (reps, due, interval) => ({ algo: "sm2", due, last: now - DAY, reps, lapses: 0, ef: 2.5, interval });
      S.asked = [];
      // (a) bdp : deux qcm échus (reps 0 et 2), les autres à échéance future.
      const bdpQ = DATA.QCM.filter(it => it.cat === "bdp");
      const srsA = {};
      bdpQ.forEach(it => { srsA[it.id] = card(3, now + 5 * DAY, 10); });
      srsA[bdpQ[0].id] = card(2, now - DAY, 6);
      srsA[bdpQ[1].id] = card(0, now - DAY, 1);
      saveSRS(srsA);
      let okA = 0;
      for (let i = 0; i < 30; i++) if (pickDue("qcm", ["bdp"]).id === bdpQ[1].id) okA++;
      // (b) qcm bdp et pen tous échus à égalité ; tout le reste de bdp maîtrisé.
      const srsB = {};
      quizBank().filter(it => it.cat === "bdp").forEach(it => { srsB[it.id] = card(3, now + 5 * DAY, 10); });
      DATA.QCM.filter(it => it.cat === "bdp" || it.cat === "pen").forEach(it => { srsB[it.id] = card(0, now - DAY, 1); });
      saveSRS(srsB);
      let pen = 0;
      const n = 600;
      for (let i = 0; i < n; i++) if (pickDue("qcm", ["bdp", "pen"]).cat === "pen") pen++;
      const nPen = DATA.QCM.filter(it => it.cat === "pen").length;
      const nBdp = DATA.QCM.filter(it => it.cat === "bdp").length;
      return { okA, share: pen / n, uniform: nPen / (nPen + nBdp) };
    });
    if (r.okA !== 30) errs.push(`srs pickDue : la carte la moins maîtrisée n'est sortie que ${r.okA}/30 fois`);
    if (!(r.share > r.uniform + 0.04)) errs.push(`srs pickDue : pondération inopérante (pen ${r.share.toFixed(2)} vs uniforme ${r.uniform.toFixed(2)})`);
    results.push(`  pickDue : moins maîtrisée ${r.okA}/30 · catégorie faible ${r.share.toFixed(2)} (uniforme ${r.uniform.toFixed(2)})`);
    if (pageErrors.length) errs.push("srs pickDue pageerrors: " + pageErrors.join(" | "));
  });

  return errs;
}

// ------------------------------------------------------------- layout mode
async function runLayout(baseUrl, browser, baseline, results) {
  results.push("[layout]");
  const errs = [];

  const context = await browser.newContext({
    viewport: { width: 375, height: 667 }, // iPhone SE
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", e => pageErrors.push(String(e)));

  try {
    await page.goto(`${baseUrl}/index.html?seed=42`);
    // Émule safe-area 59+34 : injecte un style APRÈS le chargement (les
    // variables CSS écrasent les env() par cascade).
    await page.addStyleTag({
      content: `:root { --sat: 59px !important; --sab: 34px !important; }`,
    });
    await page.evaluate(() => localStorage.clear());
    await page.goto(`${baseUrl}/index.html?seed=42`);
    await page.addStyleTag({
      content: `:root { --sat: 59px !important; --sab: 34px !important; }`,
    });
    await page.locator('#boot [data-act="bootStart"]').click();

    // Vérifie que le premier élément visible (topbar) et le titre h1 sont
    // sous la safe-area (>=59 px du top).
    const layout = await page.evaluate(() => {
      const bar = document.querySelector(".topbar");
      const h1  = document.querySelector("header h1");
      return {
        topbarTop: bar ? bar.getBoundingClientRect().top : null,
        topbarPT: bar ? getComputedStyle(bar).paddingTop : null,
        h1Top:    h1  ? h1.getBoundingClientRect().top  : null,
      };
    });
    results.push(`  topbar.top=${layout.topbarTop} pad=${layout.topbarPT} · h1.top=${layout.h1Top}`);
    // .topbar est sticky top:0 mais avec padding-top interne au moins 30 px.
    // Le contenu utile (bouton SON) est donc à au moins 30 px du top. On
    // vérifie via le padding-top, qui doit être >= 30px (règle SPEC §7.4).
    const pt = parseFloat(layout.topbarPT || "0");
    if (pt < 30) errs.push(`layout : topbar padding-top ${pt} < 30 (safe-area haute cassée)`);
    // Idem pour h1 : sous la topbar collante, donc >= 30 px environ (une
    // petite marge de rendu tolérée : 20 px).
    if (layout.h1Top != null && layout.h1Top < 20) {
      errs.push(`layout : h1.top ${layout.h1Top} < 20 (probablement coupé par la barre d'état iOS)`);
    }

    await capture(page, "layout-topbar", baseline, results);
    // Entre en manche, répond faux au premier vrai qcm pour atteindre un
    // écran why (le plus long : énoncé + choix + why + Suivant).
    await page.locator('[data-act="startShow"]').click();
    await page.locator('[data-act="introOK"]').click();
    await page.waitForFunction(() => window.eval && window.eval("S && S.phase === 'q'"));
    await answerFaux(page);
    // Phase why : la carte peut dépasser le fold, mais on doit pouvoir la
    // faire scroller jusqu'au bouton Suivant.
    const nextBtn = page.locator('[data-act="next"]').first();
    await nextBtn.scrollIntoViewIfNeeded();
    const box = await nextBtn.boundingBox();
    const vh = 667;
    results.push(`  next button box=${box ? `${box.x.toFixed(0)},${box.y.toFixed(0)}+${box.width.toFixed(0)}x${box.height.toFixed(0)}` : "?"} (viewport h=${vh})`);
    if (!box) errs.push("layout : bouton Suivant introuvable en phase why");
    else if (box.y + box.height > vh) errs.push(`layout : bouton Suivant reste hors viewport après scroll (y+h=${box.y + box.height} > ${vh})`);
    else if (box.height < 30) errs.push(`layout : bouton Suivant trop petit (h=${box.height})`);
    // Vérifie qu'il est bien cliquable (visible dans le viewport).
    if (box) {
      const clickable = await nextBtn.isVisible();
      if (!clickable) errs.push("layout : bouton Suivant non visible");
    }
    await capture(page, "layout-why", baseline, results);
    if (pageErrors.length) errs.push("layout pageerrors: " + pageErrors.join(" | "));
  } finally {
    await context.close();
  }

  return errs;
}

// ---------------------------------------------------------------- main
async function main() {
  const modeList = modes.length ? modes : ["scenario"];
  const allModes = modeList.includes("all") ? ["scenario", "gens", "srs", "layout"] : modeList;
  const baseline = baselineLoad();
  const results = [];
  const errs = [];

  const port = await pickFreePort();
  const baseUrl = `http://${HOST}:${port}`;
  const server = await startHttpServer(port);

  const browser = await chromium.launch({ headless: !HEADED });

  try {
    for (const m of allModes) {
      if (m === "scenario") errs.push(...await runScenario(baseUrl, browser, baseline, results));
      else if (m === "gens") errs.push(...await runGens(baseUrl, browser, baseline, results));
      else if (m === "srs") errs.push(...await runSRS(baseUrl, browser, baseline, results));
      else if (m === "layout") errs.push(...await runLayout(baseUrl, browser, baseline, results));
      else results.push(`(mode inconnu: ${m})`);
    }
  } finally {
    await browser.close();
    if (!KEEP_SERVER) stopHttpServer(server);
  }

  if (UPDATE_BASELINE) baselineSave(baseline);
  else if (!existsSync(BASELINE)) baselineSave(baseline);

  for (const line of results) process.stdout.write(line + "\n");
  if (errs.length) {
    process.stderr.write("\n" + errs.length + " ERREUR(S) :\n");
    for (const e of errs) process.stderr.write("  - " + e + "\n");
    process.exit(1);
  }
  process.stdout.write("\nplaytest OK\n");
}

main().catch(err => {
  process.stderr.write("playtest: " + err.stack + "\n");
  process.exit(2);
});
