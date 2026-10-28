import { ReactNode, useCallback, useEffect, useState } from "react";
import { getLang, LANGS, locale, setLang, t, tk, type Lang } from "./i18n";
import { getMode, setMode, type Mode } from "./theme";

/** Icône Material Symbols (nom = ligature ; la police embarquée ne contient que les icônes utilisées). */
export const Icon = ({ name, fill, className = "" }: { name: string; fill?: boolean; className?: string }) => (
  <span className={`icon${fill ? " fill" : ""} ${className}`} aria-hidden="true">{name}</span>
);

export const Logo = ({ height = 36 }: { height?: number }) => (
  <svg viewBox="0 0 260 64" height={height} role="img" aria-label="Badgeo" style={{ direction: "ltr", flex: "none" }}>
    <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#3b82f6" /><stop offset="1" stopColor="#1e3a8a" /></linearGradient></defs>
    <rect x="12" y="4" width="40" height="56" rx="10" fill="url(#lg)" />
    <rect x="25" y="9" width="14" height="5" rx="2.5" fill="#fff" fillOpacity=".85" />
    <circle cx="32" cy="35" r="13" fill="#fff" />
    <path d="M25.5 35.5l5 5 9-10" fill="none" stroke="#1e3a8a" strokeWidth="4.2" strokeLinecap="round" strokeLinejoin="round" />
    <text x="68" y="44" fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="34" fontWeight="700" letterSpacing="-0.5" style={{ fill: "var(--logo-text)" }}>
      Badge<tspan style={{ fill: "var(--logo-accent)" }}>o</tspan></text>
  </svg>
);

const STATUS: Record<string, [string, string, string]> = {
  present: [tk("Présent"), "ok", "check_circle"], in_progress: [tk("En cours"), "info", "timelapse"], incomplete: [tk("Incomplet"), "bad", "report_problem"],
  no_punch: [tk("Sans pointage"), "warn", "history_toggle_off"], absent: [tk("Absent"), "bad", "block"], leave: [tk("Congé"), "info", "beach_access"],
  sick: [tk("Arrêt maladie"), "info", "medical_services"], mission: [tk("Mission"), "info", "flight_takeoff"], permission: [tk("Permission"), "info", "more_time"],
  holiday: [tk("Férié"), "", "celebration"], rest: [tk("Repos"), "", "bedtime"], pending: [tk("À venir"), "", "schedule"], scheduled: [tk("Planifié"), "", "event_available"],
};
export const statusLabel = (s: string) => t(STATUS[s]?.[0] ?? s);
export const STATUS_KEYS = Object.keys(STATUS);
export const ANOMALY: Record<string, string> = {
  missing_out: tk("Sortie manquante"), missing_in: tk("Entrée manquante"), odd_punches: tk("Nombre impair"), duplicate_punch: tk("Doublon"),
  no_shift: tk("Sans horaire"), punch_on_rest_day: tk("Jour de repos"), punch_on_holiday: tk("Jour férié"), punch_during_leave: tk("Pendant congé"),
  long_presence: tk("Présence > 16 h"), before_earliest_in: tk("Avant heure min."),
};
export const anomalyLabel = (a: string) => t(ANOMALY[a] ?? a);

export const hm = (m: number | null | undefined) => (m == null ? "—" : `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}`);
// Les horodatages du serveur portent le décalage de l'entreprise : on affiche l'heure telle qu'écrite, sans conversion.
export const time = (iso: string | null) => (iso ? iso.slice(11, 16) : "—");
const d0 = (iso: string) => new Date(iso.length === 10 ? iso + "T00:00:00" : iso);
export const dateFr = (iso: string) => d0(iso).toLocaleDateString(locale(), { weekday: "short", day: "2-digit", month: "short" });
export const dateLong = (iso?: string) => (iso ? d0(iso) : new Date()).toLocaleDateString(locale(), { dateStyle: "full" });
export const dateTime = (iso: string | null) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)} ${iso.slice(11, 16)}` : "—");
export const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
export const monthStart = () => today().slice(0, 8) + "01";

export const StatusPill = ({ status }: { status: string }) => {
  const [, tone, icon] = STATUS[status] ?? ["", "", ""];
  return <span className={`pill ${tone}`}>{icon && <Icon name={icon} />}{statusLabel(status)}</span>;
};
export const Pill = ({ tone = "", icon, children }: { tone?: string; icon?: string; children: ReactNode }) => (
  <span className={`pill ${tone}`}>{icon && <Icon name={icon} />}{children}</span>
);

/** Charge des données ; expose chargement, erreur et rechargement. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = [], every = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(() => { setLoading(true); fn().then((d) => { setData(d); setError(""); }).catch((e) => setError(t(e.message))).finally(() => setLoading(false)); }, deps);
  useEffect(() => { load(); if (!every) return; const i = setInterval(load, every); return () => clearInterval(i); }, [load, every]);
  return { data, error, loading, reload: load };
}

export const ErrorBanner = ({ error }: { error: string }) => (error ? <div className="banner bad" role="alert"><Icon name="error" />{t(error)}</div> : null);

export function Pager({ page, count, size, onPage }: { page: number; count: number; size: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(count / size));
  return (
    <div className="pager">
      <span className="muted small">{t("{n} résultat(s)", { n: count })}</span>
      <span className="end row">
        <button className="ghost sm" disabled={page <= 1} onClick={() => onPage(page - 1)}><Icon name="chevron_left" className="flip" />{t("Précédent")}</button>
        <span className="small">{t("Page {p} / {n}", { p: page, n: pages })}</span>
        <button className="ghost sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>{t("Suivant")}<Icon name="chevron_right" className="flip" /></button>
      </span>
    </div>
  );
}

export const Field = ({ label, children }: { label: string; children: ReactNode }) => <label className="field">{label}{children}</label>;

/** Sélecteurs de thème (clair / sombre / automatique) et de langue. */
export function ThemeSwitch() {
  const [mode, set] = useState<Mode>(getMode());
  const next: Record<Mode, Mode> = { auto: "light", light: "dark", dark: "auto" };
  const icon = { auto: "brightness_auto", light: "light_mode", dark: "dark_mode" }[mode];
  const label = { auto: tk("Thème : automatique"), light: tk("Thème : clair"), dark: tk("Thème : sombre") }[mode];
  return <button className="ghost icon-btn" title={t(label)} aria-label={t(label)} onClick={() => { setMode(next[mode]); set(next[mode]); }}><Icon name={icon} /></button>;
}
export function LangSwitch({ onChange }: { onChange: (l: Lang) => void }) {
  return (
    <label className="row" style={{ gap: 4 }} title={t("Langue")}>
      <Icon name="translate" className="muted" />
      <select aria-label={t("Langue")} value={getLang()} onChange={(e) => { setLang(e.target.value as Lang); onChange(e.target.value as Lang); }} style={{ padding: "6px 8px" }}>
        {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
      </select>
    </label>
  );
}
