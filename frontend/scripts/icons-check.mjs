// Vérifie que chaque icône utilisée dans le code existe dans la police embarquée (rendu navigateur réel).
//   npm run build && node scripts/icons-check.mjs       (nécessite playwright)
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright"); // playwright est un outil de développement, hors dépendances du projet

const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? (f === "locales" ? [] : walk(p)) : /\.tsx?$/.test(f) ? [p] : []; });
const used = new Set();
for (const f of walk("src")) {
  const s = readFileSync(f, "utf8");
  for (const m of s.matchAll(/(?:Icon name=|\bicon[:=]\s*)"([a-z][a-z0-9_]+)"/g)) used.add(m[1]);
  // tables : [ "libellé", "tone", "icône" ] et { clé: "icône" }
  for (const m of s.matchAll(/(?:\b(?:ICON|KIND_ICON)\b[^=]*=\s*\{([^}]*)\})/g)) for (const v of m[1].matchAll(/"([a-z][a-z0-9_]+)"/g)) used.add(v[1]);
}
const STATUS_ICONS = [...readFileSync("src/ui.tsx", "utf8").matchAll(/\[tk\("[^"]+"\),\s*"[a-z]*",\s*"([a-z_]+)"\]/g)].map((m) => m[1]);
STATUS_ICONS.forEach((i) => used.add(i));
for (const m of readFileSync("src/mobile/Mobile.tsx", "utf8").matchAll(/"([a-z_]+)"/g)) if (/_|^(fingerprint|person|badge|tune|translate|bedtime)$/.test(m[1])) used.add(m[1]);
["ok", "bad", "warn", "info"].forEach((x) => used.delete(x)); // tons de pastilles, pas des icônes
const b = await chromium.launch();
const p = await b.newPage();
await p.goto("file://" + process.cwd() + "/dist/index.html").catch(() => {});
await p.setContent(`<style>@font-face{font-family:MS;src:url(file://${process.cwd()}/public/fonts/material-symbols.woff2) format("woff2");font-weight:100 700}
.i{font-family:MS;font-size:24px;font-feature-settings:"liga";white-space:nowrap}</style>${[...used].map((n) => `<span class="i" data-n="${n}">${n}</span><br>`).join("")}`);
await p.evaluate(() => document.fonts.ready);
const bad = await p.evaluate(() => [...document.querySelectorAll(".i")].filter((e) => e.getBoundingClientRect().width > 40).map((e) => e.dataset.n));
console.log(`${used.size} icônes utilisées ; ${bad.length} absente(s) de la police : ${bad.join(", ") || "aucune"}`);
await b.close();
process.exit(bad.length ? 1 : 0);
