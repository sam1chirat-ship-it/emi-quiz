#!/usr/bin/env node
/*
 * playtest.mjs — validation runtime avant commit (SPEC §8.4).
 *
 * Modes :
 *   scenario  — parcours joueur juste (bots=weak, seed=42) puis joueur
 *               faux (bots=strong, seed=43). Zéro pageerror.
 *   srs       — après mauvaise réponse sur X, X en boîte 0 et resort en
 *               priorité à la reprise.
 *   layout    — safe-area 59+34 émulée, viewport iPhone SE, premier
 *               élément visible >= 59 px, bouton Suivant cliquable.
 *   all       — enchaîne les trois.
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
    return { phase: S.phase, fmt: S.qFmt, manche: S.manche, a: S.q ? S.q.a : null, steps: S.q ? (S.q.steps || null) : null, choices: S.q ? (S.q.choices || null) : null };
  });
  if (info.fmt === "qcm" || info.fmt === "qcm3") {
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
    return { fmt: S.qFmt, a: S.q ? S.q.a : null, steps: S.q ? (S.q.steps || null) : null };
  });
  if (info.fmt === "qcm" || info.fmt === "qcm3") {
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

async function playThrough(page, strategy, maxIter = 300) {
  for (let i = 0; i < maxIter; i++) {
    const S = await getState(page);
    if (!S) return;
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
    if (!srs || !srs[firstId] || srs[firstId].box !== 0) {
      errs.push(`srs : après réponse fausse, ${firstId} devrait être box=0 (obs: ${JSON.stringify(srs && srs[firstId])})`);
    }
    results.push(`  id=${firstId} box=${srs[firstId] && srs[firstId].box} due<=now=${srs[firstId] && srs[firstId].due <= Date.now()}`);
    if (pageErrors.length) errs.push("srs pageerrors: " + pageErrors.join(" | "));
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
  const allModes = modeList.includes("all") ? ["scenario", "srs", "layout"] : modeList;
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
