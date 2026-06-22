// Deterministic animation filmstrip.
//
// Captures exact frames of a page's CSS/Web animations by pausing every running
// animation and scrubbing its currentTime to fixed timestamps — so frames land
// precisely at T = 0, step, 2*step, ... regardless of how slow screenshotting is.
// Lets a reviewer (human or model) judge pacing, overlap, and stutter from a
// single contact sheet instead of guessing from one static frame.
//
// Usage: node filmstrip.mjs <url> <durationMs> <stepMs> <outDir> [w] [h]
import { chromium } from "playwright";
import { mkdirSync, rmSync } from "fs";

const url = process.argv[2];
const durMs = +process.argv[3] || 5000;
const stepMs = +process.argv[4] || 120;
const outDir = process.argv[5] || "tools/screenshots/out/strip";
const W = +process.argv[6] || 1280;
const H = +process.argv[7] || 340;

rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
await page.goto(url, { waitUntil: "networkidle" });
// Wait for the island to mount and its animations to exist before grabbing them.
await page.waitForSelector(".bi-glyph", { state: "attached" });
await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));

// Grab every animation (running + delayed/pending) and pause them so we can scrub.
// They all start at mount, so their timelines are aligned: setting currentTime=T
// on each yields a consistent global snapshot at time T.
const animCount = await page.evaluate(() => {
  window.__anims = document.getAnimations();
  window.__anims.forEach((a) => a.pause());
  return window.__anims.length;
});
console.log(`found ${animCount} animations`);
if (animCount === 0) { console.error("no animations found — aborting"); await browser.close(); process.exit(1); }

const clip = { x: 0, y: 0, width: W, height: H };
let i = 0;
for (let t = 0; t <= durMs; t += stepMs) {
  await page.evaluate((time) => {
    window.__anims.forEach((a) => {
      try { a.currentTime = time; } catch {}
    });
  }, t);
  await page.screenshot({ path: `${outDir}/f${String(i).padStart(3, "0")}.png`, clip });
  i++;
}
console.log(`captured ${i} frames @ ${stepMs}ms step into ${outDir}`);
await browser.close();
