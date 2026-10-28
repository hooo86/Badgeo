import { ReactNode, useCallback, useEffect, useState } from "react";

export const STATUS: Record<string, [string, string]> = {
  present: ["Présent", "ok"], in_progress: ["En cours", "info"], incomplete: ["Incomplet", "bad"], no_punch: ["Sans pointage", "warn"],
  absent: ["Absent", "bad"], leave: ["Congé", "info"], sick: ["Arrêt maladie", "info"], mission: ["Mission", "info"],
  permission: ["Permission", "info"], holiday: ["Férié", ""], rest: ["Repos", ""], pending: ["À venir", ""], scheduled: ["Planifié", ""],
};
export const ANOMALY: Record<string, string> = {
  missing_out: "Sortie manquante", missing_in: "Entrée manquante", odd_punches: "Nombre impair", duplicate_punch: "Doublon",
  no_shift: "Sans horaire", punch_on_rest_day: "Jour de repos", punch_on_holiday: "Jour férié", punch_during_leave: "Pendant congé",
  long_presence: "Présence > 16 h", before_earliest_in: "Avant heure min.",
};
export const hm = (m: number | null | undefined) => (m == null ? "—" : `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}`);
// Server timestamps carry the company's UTC offset; display them as written, not converted to the browser's zone.
export const time = (iso: string | null) => (iso ? iso.slice(11, 16) : "—");
export const dateFr = (iso: string) => new Date(iso.length === 10 ? iso + "T00:00:00" : iso).toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit", month: "short" });
export const dateTime = (iso: string | null) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)} ${iso.slice(11, 16)}` : "—");
export const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
export const monthStart = () => today().slice(0, 8) + "01";

export const StatusPill = ({ status }: { status: string }) => {
  const [label, tone] = STATUS[status] ?? [status, ""];
  return <span className={`pill ${tone}`}>{label}</span>;
};
export const Pill = ({ tone = "", children }: { tone?: string; children: ReactNode }) => <span className={`pill ${tone}`}>{children}</span>;

/** Loads data, exposes loading/error and a reload function. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = [], every = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(() => { setLoading(true); fn().then((d) => { setData(d); setError(""); }).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, deps);
  useEffect(() => { load(); if (!every) return; const t = setInterval(load, every); return () => clearInterval(t); }, [load, every]);
  return { data, error, loading, reload: load };
}

export const ErrorBanner = ({ error }: { error: string }) => (error ? <div className="banner bad">{error}</div> : null);

export function Pager({ page, count, size, onPage }: { page: number; count: number; size: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(count / size));
  return (
    <div className="pager">
      <span className="muted small">{count} résultat(s)</span>
      <span className="right row">
        <button className="ghost sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>Précédent</button>
        <span className="small">Page {page} / {pages}</span>
        <button className="ghost sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Suivant</button>
      </span>
    </div>
  );
}

export const Field = ({ label, children }: { label: string; children: ReactNode }) => <label className="field">{label}{children}</label>;
