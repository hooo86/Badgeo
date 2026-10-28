// Extrait les clés de traduction (textes français passés à t(...) ou tk(...)) et vérifie les dictionnaires.
//   node scripts/i18n-keys.mjs          → liste les clés manquantes en anglais / arabe (code de sortie 1 s'il en manque)
//   node scripts/i18n-keys.mjs --all    → liste toutes les clés
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? (f === "locales" ? [] : walk(p)) : /\.(tsx?|ts)$/.test(f) ? [p] : []; });
export const keys = new Set();
for (const f of walk("src")) {
  const s = readFileSync(f, "utf8");
  for (const m of s.matchAll(/\bt[k]?\(\s*"((?:[^"\\]|\\.)*)"/g)) keys.add(JSON.parse(`"${m[1]}"`));
}
const load = (lang) => {
  const s = readFileSync(`src/locales/${lang}.ts`, "utf8");
  const out = {};
  for (const m of s.matchAll(/^\s*"((?:[^"\\]|\\.)*)":\s*"((?:[^"\\]|\\.)*)",?\s*$/gm)) out[JSON.parse(`"${m[1]}"`)] = JSON.parse(`"${m[2]}"`);
  return out;
};
if (process.argv.includes("--all")) { console.log([...keys].sort().map((k) => JSON.stringify(k)).join("\n")); process.exit(0); }
let bad = 0;
for (const lang of ["en", "ar"]) {
  const d = load(lang);
  const missing = [...keys].filter((k) => !(k in d));
  const extra = Object.keys(d).filter((k) => !keys.has(k));
  const vars = [...keys].filter((k) => k in d && JSON.stringify((k.match(/\{\w+\}/g) || []).sort()) !== JSON.stringify((d[k].match(/\{\w+\}/g) || []).sort()));
  console.log(`${lang}: ${keys.size - missing.length}/${keys.size} traduits, ${extra.length} clé(s) inutilisée(s), ${vars.length} variable(s) incohérente(s)`);
  missing.forEach((k) => console.log("  manque :", JSON.stringify(k)));
  vars.forEach((k) => console.log("  variables :", JSON.stringify(k)));
  bad += missing.length + vars.length;
}
process.exit(bad ? 1 : 0);
