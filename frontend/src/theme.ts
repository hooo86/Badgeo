export type Mode = "light" | "dark" | "auto";
const KEY = "badgeo.theme";

export const getMode = (): Mode => {
  try { const v = localStorage.getItem(KEY); if (v === "light" || v === "dark" || v === "auto") return v; } catch { /* stockage indisponible */ }
  return "auto";
};
export const resolve = (m: Mode): "light" | "dark" =>
  m === "auto" ? (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light") : m;

export function applyTheme(m: Mode) {
  const r = resolve(m);
  document.documentElement.dataset.theme = r;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", r === "dark" ? "#080d1a" : "#2563eb");
}
export function setMode(m: Mode) {
  try { localStorage.setItem(KEY, m); } catch { /* ignoré */ }
  applyTheme(m);
}
/** Suit le réglage du système tant que le mode « auto » est choisi. */
export function watchSystem() {
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener("change", () => { if (getMode() === "auto") applyTheme("auto"); });
}
