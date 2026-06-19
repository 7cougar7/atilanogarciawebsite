// Copy the FontAwesome assets from the npm package into Django's static tree so
// {% static 'fontawesome/css/all.min.css' %} resolves. Runs as part of `npm run build`
// (see package.json), replacing the old commit-a-zip + setup_fontawesome.py approach.
// The destination is gitignored and produced fresh at build time.
import { cpSync, mkdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const src = resolve(root, "node_modules/@fortawesome/fontawesome-free");
const dest = resolve(root, "mainwebsite/static/fontawesome");

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
for (const sub of ["css", "webfonts"]) {
  cpSync(resolve(src, sub), resolve(dest, sub), { recursive: true });
}
console.log(`FontAwesome assets copied to ${dest}`);
