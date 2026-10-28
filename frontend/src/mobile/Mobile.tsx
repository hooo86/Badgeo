import { useEffect, useState } from "react";
import * as api from "../api";
import { dateFr, ErrorBanner, hm, Pill, StatusPill, time, today, useLoad } from "../ui";

type Tab = "pointer" | "historique" | "planning" | "profil";
const ICON: Record<Tab, string> = {
  pointer: "M12 3a6 6 0 00-6 6v3m12 0V9a6 6 0 00-9-5.2M12 8v5m-3 2v2m6-2v4M9 21h6",
  historique: "M12 7v5l3 2m6-2a9 9 0 11-18 0 9 9 0 0118 0z",
  planning: "M8 3v3m8-3v3M4 9h16M5 5h14a1 1 0 011 1v13a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1z",
  profil: "M16 11a4 4 0 10-8 0 4 4 0 008 0zM4 21c0-4 4-6 8-6s8 2 8 6",
};
const LABEL: Record<Tab, string> = { pointer: "Pointer", historique: "Historique", planning: "Planning", profil: "Profil" };
const Icon = ({ tab }: { tab: Tab }) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={ICON[tab]} /></svg>;

function Clock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  return <div className="clock" aria-live="off">{now.toLocaleTimeString("fr-FR")}</div>;
}

function Pointer() {
  const { data: me, error, reload } = useLoad(api.me, [], 30000);
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState(""), [ok, setOk] = useState("");
  const punch = async () => {
    setBusy(true); setMsg(""); setOk("");
    try { const r = await api.mePunch(); setOk(`Pointage enregistré à ${time(r.timestamp)}`); reload(); } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  };
  if (!me) return <div className="m-body"><ErrorBanner error={error} /><p className="muted">Chargement…</p></div>;
  const t = me.today, n = t.punch_times.length, nextIn = n % 2 === 0;
  const enabled = me.mobile_punch_enabled && me.mobile_punch_allowed_here;
  return (
    <div className="m-body">
      <div className="row"><div><h1 style={{ fontSize: 22, margin: 0 }}>Bonjour {me.employee.first_name}</h1><div className="muted small">{new Date().toLocaleDateString("fr-FR", { dateStyle: "full" })}</div></div><div className="right"><Clock /><StatusPill status={t.status} /></div></div>
      <ErrorBanner error={error || msg} />
      {ok && <div className="banner">{ok}</div>}
      <button className="badge-btn" onClick={punch} disabled={!enabled || busy} aria-label={nextIn ? "Badger entrée" : "Badger sortie"}>
        <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M9 12l2 2 4-4M12 3a9 9 0 100 18 9 9 0 000-18z" /></svg>
        <b>{busy ? "…" : nextIn ? "BADGER ENTRÉE" : "BADGER SORTIE"}</b><span className="small">{enabled ? "Appuyer pour valider" : "Indisponible"}</span></button>
      {!me.mobile_punch_enabled && <div className="banner bad">Le pointage mobile est désactivé. Utilisez la pointeuse du site.</div>}
      {me.mobile_punch_enabled && !me.mobile_punch_allowed_here && <div className="banner bad">Pointage possible uniquement depuis le réseau de l'entreprise.</div>}
      <div className="card"><h2>Synthèse de la journée</h2>
        <div className="row"><span className="muted">Travail estimé</span><b className="right">{hm(t.worked_min)}</b></div>
        <div className="dayline"><span>Arrivée</span><b>{t.first_in ? time(t.first_in) : "—"}</b></div>
        <div className="dayline"><span>Dernier pointage</span><b>{n ? t.punch_times[n - 1].slice(11, 16) : "—"}</b></div>
        {t.late_min > 0 && <div className="dayline"><span>Retard</span><b className="err">{t.late_min} min</b></div>}
        <div className="punches" style={{ marginTop: 8 }}>{t.punch_times.map((p, i) => <span key={i}>{p.slice(11, 16)}</span>)}</div></div>
    </div>
  );
}

const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);

function History() {
  const [mode, setMode] = useState<"week" | "month">("week"), [offset, setOffset] = useState(0);
  const base = new Date();
  let from: Date, to: Date;
  if (mode === "week") { const dow = (base.getDay() + 6) % 7; from = new Date(base.getFullYear(), base.getMonth(), base.getDate() - dow + offset * 7); to = new Date(from.getFullYear(), from.getMonth(), from.getDate() + 6); }
  else { from = new Date(base.getFullYear(), base.getMonth() + offset, 1); to = new Date(base.getFullYear(), base.getMonth() + offset + 1, 0); }
  const { data, error } = useLoad(() => api.meHistory(iso(from), iso(to)), [mode, offset]);
  const pct = data && data.totals.expected_min ? Math.round((100 * data.totals.worked_min) / data.totals.expected_min) : 0;
  return (
    <div className="m-body">
      <div><div className="eyebrow">Feuille de temps</div><h1 style={{ fontSize: 22, margin: 0 }}>Historique d'activité</h1></div>
      <div className="seg"><button className={mode === "week" ? "on" : ""} onClick={() => { setMode("week"); setOffset(0); }}>Semaine</button><button className={mode === "month" ? "on" : ""} onClick={() => { setMode("month"); setOffset(0); }}>Mois</button></div>
      <div className="row"><button className="ghost sm" onClick={() => setOffset(offset - 1)} aria-label="Période précédente">‹</button><b className="right" style={{ margin: "0 auto" }}>{dateFr(iso(from))} – {dateFr(iso(to))}</b><button className="ghost sm" onClick={() => setOffset(offset + 1)} aria-label="Période suivante">›</button></div>
      <ErrorBanner error={error} />
      {data && <div className="card"><div className="muted small">Cumul</div><div className="row"><span style={{ fontSize: 30, fontWeight: 700 }}>{hm(data.totals.worked_min)}</span><span className="muted">/ {hm(data.totals.expected_min)}</span>{data.totals.overtime_min > 0 && <Pill tone="info">+{hm(data.totals.overtime_min)} sup. pot.</Pill>}</div>
        <div className="bar-track" style={{ margin: "8px 0" }}><div className="bar-fill" style={{ width: `${Math.min(100, pct)}%` }} /></div><div className="small muted">{pct}% réalisé · retards cumulés {data.totals.late_min} min</div></div>}
      {data?.days.map((d) => (
        <div className="card" key={d.id}><div className="row"><b>{dateFr(d.work_date)}</b><span className="right"><StatusPill status={d.status} /></span></div>
          <div className="punches" style={{ margin: "8px 0" }}>{d.punch_times.length ? d.punch_times.map((p, i) => <span key={i}>{p.slice(11, 16)}</span>) : <span className="muted">Aucun pointage</span>}</div>
          <div className="row small muted"><span>Travail {hm(d.worked_min)}</span>{d.late_min > 0 && <span className="err">Retard {d.late_min} min</span>}{d.anomalies.length > 0 && <span className="err">Anomalie : à régulariser auprès des RH</span>}</div></div>))}
      {data && !data.days.length && <p className="muted">Aucune journée sur cette période.</p>}
    </div>
  );
}

function Planning() {
  const { data, error } = useLoad(api.mePlanning, []);
  return (
    <div className="m-body"><div><div className="eyebrow">Planning</div><h1 style={{ fontSize: 22, margin: 0 }}>14 prochains jours</h1></div><ErrorBanner error={error} />
      {data?.days.map((d) => (
        <div className="card" key={d.date}><div className="row"><b>{dateFr(d.date)}</b>
          {d.holiday ? <Pill>Férié</Pill> : d.shift ? <><span className="right">{d.shift.start} → {d.shift.end}</span></> : <Pill>Repos</Pill>}</div>
          {d.shift && !d.holiday && <div className="small muted">{d.shift.name}{d.shift.crosses_midnight && " · termine le lendemain"}</div>}</div>))}
    </div>
  );
}

function Profile({ onLogout }: { onLogout: () => void }) {
  const { data, error } = useLoad(api.me, []);
  return (
    <div className="m-body"><h1 style={{ fontSize: 22, margin: 0 }}>Profil</h1><ErrorBanner error={error} />
      {data && <div className="card"><h2>{data.employee.first_name} {data.employee.last_name}</h2><div className="muted">{data.employee.job_title || "—"}</div>
        <div className="dayline"><span>Matricule</span><b>{data.employee.matricule}</b></div><div className="dayline"><span>Unité</span><b>{data.employee.org_unit ?? "—"}</b></div></div>}
      <div className="card"><h2>Confidentialité</h2><p className="muted small">Badgeo n'enregistre que l'heure de vos pointages. Aucune géolocalisation ni donnée biométrique n'est collectée par cette application.</p></div>
      <button className="ghost" onClick={onLogout}>Se déconnecter</button></div>
  );
}

export default function Mobile({ onLogout }: { onLogout: () => void }) {
  const [tab, setTab] = useState<Tab>("pointer");
  return (
    <div className="m">
      <div className="m-top"><img src="/logo.svg" alt="Badgeo" /><span className="muted small">{LABEL[tab]}</span></div>
      {tab === "pointer" && <Pointer />}{tab === "historique" && <History />}{tab === "planning" && <Planning />}{tab === "profil" && <Profile onLogout={onLogout} />}
      <nav className="m-nav" aria-label="Navigation"><div>{(Object.keys(LABEL) as Tab[]).map((t) => (
        <a key={t} href="#" className={tab === t ? "on" : ""} onClick={(e) => { e.preventDefault(); setTab(t); }}><Icon tab={t} />{LABEL[t]}</a>))}</div></nav>
    </div>
  );
}
