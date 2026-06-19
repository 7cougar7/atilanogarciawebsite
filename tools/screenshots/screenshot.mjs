// Visual-verification screenshots. Captures each given path in both light and dark
// theme by flipping the site's `dark_mode` localStorage key (the same key the theme
// system uses) and reloading.
//
// Usage (Django dev server must be running):
//   cd tools/screenshots && npm install && npx playwright install chromium
//   node screenshot.mjs                 # default pages
//   node screenshot.mjs / /resume/      # specific paths
//   BASE_URL=http://127.0.0.1:8000 node screenshot.mjs
//
// Output PNGs land in tools/screenshots/out/ (gitignored).
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = process.env.BASE_URL || "http://127.0.0.1:8000";
const args = process.argv.slice(2);
const paths = args.length ? args : ["/", "/resume/", "/kky/", "/graduation/"];

const here = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(here, "out");
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();

for (const path of paths) {
  const slug = path.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "") || "home";
  for (const theme of ["light", "dark"]) {
    await page.goto(BASE + path, { waitUntil: "networkidle" });
    // Set the theme the way a user's toggle would, then reload so the no-flicker
    // inline setter applies it before paint.
    await page.evaluate((t) => {
      localStorage.setItem("dark_mode", t === "dark" ? "true" : "false");
    }, theme);
    await page.reload({ waitUntil: "networkidle" });
    await page.waitForTimeout(900); // let React islands mount + glass cards fade in
    const file = resolve(OUT, `${slug}__${theme}.png`);
    await page.screenshot({ path: file, fullPage: true });
    console.log(`saved ${file}`);
  }
}

await browser.close();
