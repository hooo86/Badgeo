import ar from "./locales/ar";
import en from "./locales/en";

export type Lang = "fr" | "en" | "ar";
export const LANGS: { code: Lang; label: string; dir: "ltr" | "rtl"; locale: string }[] = [
  { code: "fr", label: "Français", dir: "ltr", locale: "fr-FR" },
  { code: "en", label: "English", dir: "ltr", locale: "en-GB" },
  { code: "ar", label: "العربية", dir: "rtl", locale: "ar-DZ" },
];
const KEY = "badgeo.lang";
const DICT: Record<string, Record<string, string>> = { en, ar };

function detect(): Lang {
  try { const v = localStorage.getItem(KEY); if (v === "fr" || v === "en" || v === "ar") return v; } catch { /* ignoré */ }
  const n = (navigator.language || "fr").toLowerCase();
  return n.startsWith("ar") ? "ar" : n.startsWith("en") ? "en" : "fr";
}
let current: Lang = detect();

export const getLang = () => current;
export const isRtl = () => current === "ar";
export const locale = () => LANGS.find((l) => l.code === current)!.locale;

export function setLang(l: Lang) {
  current = l;
  try { localStorage.setItem(KEY, l); } catch { /* ignoré */ }
  applyLang();
}
export function applyLang() {
  const l = LANGS.find((x) => x.code === current)!;
  document.documentElement.lang = l.code;
  document.documentElement.dir = l.dir;
}

/** Les clés sont les textes français : le français sert de langue source et de repli. */
export function t(key: string, vars?: Record<string, string | number>): string {
  let s = (current === "fr" ? undefined : DICT[current]?.[key]) ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
  // En arabe, les nombres (et leur « % ») restent lus de gauche à droite à l'intérieur de la phrase
  if (current === "ar") s = s.replace(/\d[\d.,:]*%?/g, (m) => `\u2066${m}\u2069`);
  return s;
}

/** Marque un texte à traduire plus tard (étiquettes stockées dans des tables) ; sert aussi à l'extraction des clés. */
export const tk = (key: string) => key;

/** Messages renvoyés par le serveur (en français) : traduits à l'affichage quand le texte est exactement celui-ci. */
export const SERVER_MESSAGES = [
  tk("Session expirée"), tk("Identifiants invalides"), tk("Trop de tentatives, réessayez dans une minute."),
  tk("Mot de passe actuel incorrect."), tk("Le nouveau mot de passe doit être différent."),
  tk("Vous devez d'abord changer votre mot de passe provisoire."),
  tk("Aucune licence valable pour ce poste : activez Badgeo."),
  tk("Licence expirée : l'application est en lecture seule. Saisissez une nouvelle clé."),
  tk("Clé d'activation incorrecte : vérifiez qu'elle a été copiée en entier."),
  tk("Clé d'activation non valable : elle n'a pas été délivrée par l'éditeur ou a été modifiée."),
  tk("Seul l'administrateur système peut remplacer la licence."),
  tk("Validation réservée au responsable RH."), tk("L'auteur d'une correction ne peut pas la valider."),
  tk("Export réservé aux profils RH."), tk("Fichier manquant (champ 'file')."),
  tk("Sauvegarde introuvable."), tk("Fichier de sauvegarde illisible."), tk("Sauvegarde corrompue (somme de contrôle différente)."),
  tk("Phrase de passe incorrecte ou fichier altéré."),
  tk("Aucun employé lié à ce compte."), tk("Le pointage mobile est désactivé par l'administrateur."),
  tk("Pointage mobile autorisé uniquement depuis le réseau de l'entreprise."), tk("Pointage déjà enregistré à l'instant."),
  tk("Employé non actif."), tk("Accès refusé."),
];
