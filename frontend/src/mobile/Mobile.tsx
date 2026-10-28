import { useEffect, useState } from "react";
import * as api from "../api";
import { getLang, LANGS, setLang, t, tk, type Lang } from "../i18n";
import { getMode, setMode, type Mode } from "../theme";
import { dateFr, ErrorBanner, hm, Icon, Logo, Pill, StatusPill, time, useLoad } from "../ui";

type Tab = "pointer" | "historique" | "planning" | "profil";
const ICON: Record<Tab, string> = { pointer: "fingerprint", historique: "history_toggle_off", planning: "calendar_month", profil: "person" };
const LABEL: Record<Tab, string> = { pointer: tk("Pointer"), historique: tk("Historique"), planning: tk("Planning"), profil: tk("Profil") };

function Clock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => { const i = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(i); }, []);
  return <div className="clock" aria-live="off">{now.toLocaleTimeString("fr-FR")}</div>;
}

function Pointer() {
  const { data: me, error, reload } = useLoad(api.me, [], 30000);
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState(""), [ok, setOk] = useState("");
  const punch = async () => {
    setBusy(true); setMsg(""); setOk("");
    try { const r = await api.mePunch(); setOk(t("Pointage enregistré à {time}", { time: time(r.timestamp) })); reload(); } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  };
  if (!me) return <div className="m-body"><ErrorBanner error={error} /><p className="muted">{t("Chargement…")}</p></div>;
  const d = me.today, n = d.punch_times.length, nextIn = n % 2 === 0;
  const enabled = me.mobile_punch_enabled && me.mobile_punch_allowed_here;
  return (
    <div className="m-body">
      <div className="row"><div><h1 style={{ fontSize: 22, margin: 0 }}>{t("Bonjour {name}", { name: me.employee.first_name })}</h1><div className="muted small">{new Date().toLocaleDateString(getLang() === "ar" ? "ar-DZ" : getLang() === "en" ? "en-GB" : "fr-FR", { dateStyle: "full" })}</div></div><div className="end" style={{ textAlign: "end" }}><Clock /><StatusPill status={d.status} /></div></div>
      <ErrorBanner error={error || msg} />
      {ok && <div className="banner"><Icon name="check_circle" />{ok}</div>}
      <button className="badge-btn" onClick={punch} disabled={!enabled || busy} aria-label={nextIn ? t("Badger entrée") : t("Badger sortie")}>
        <Icon name={nextIn ? "login" : "logout"} className="flip" /><b>{busy ? "…" : nextIn ? t("BADGER ENTRÉE") : t("BADGER SORTIE")}</b><span className="small">{enabled ? t("Appuyer pour valider") : t("Indisponible")}</span></button>
      {!me.mobile_punch_enabled && <div className="banner bad"><Icon name="block" />{t("Le pointage mobile est désactivé. Utilisez la pointeuse du site.")}</div>}
      {me.mobile_punch_enabled && !me.mobile_punch_allowed_here && <div className="banner bad"><Icon name="wifi_off" />{t("Pointage possible uniquement depuis le réseau de l'entreprise.")}</div>}
      <div className="card"><h2><Icon name="timelapse" className="muted" />{t("Synthèse de la journée")}</h2>
        <div className="row"><span className="muted">{t("Travail estimé")}</span><b className="end mono">{hm(d.worked_min)}</b></div>
        <div className="dayline"><span>{t("Arrivée")}</span><b className="mono">{d.first_in ? time(d.first_in) : "—"}</b></div>
        <div className="dayline"><span>{t("Dernier pointage")}</span><b className="mono">{n ? d.punch_times[n - 1].slice(11, 16) : "—"}</b></div>
        {d.late_min > 0 && <div className="dayline"><span>{t("Retard")}</span><b className="err mono">{d.late_min} min</b></div>}
        <div className="punches" style={{ marginTop: 8 }}>{d.punch_times.map((p, i) => <span key={i}>{p.slice(11, 16)}</span>)}</div></div>
    </div>
  );
}

const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);

function History() {
  const [mode, setM] = useState<"week" | "month">("week"), [offset, setOffset] = useState(0);
  const base = new Date();
  let from: Date, to: Date;
  if (mode === "week") { const dow = (base.getDay() + 6) % 7; from = new Date(base.getFullYear(), base.getMonth(), base.getDate() - dow + offset * 7); to = new Date(from.getFullYear(), from.getMonth(), from.getDate() + 6); }
  else { from = new Date(base.getFullYear(), base.getMonth() + offset, 1); to = new Date(base.getFullYear(), base.getMonth() + offset + 1, 0); }
  const { data, error } = useLoad(() => api.meHistory(iso(from), iso(to)), [mode, offset]);
  const pct = data && data.totals.expected_min ? Math.round((100 * data.totals.worked_min) / data.totals.expected_min) : 0;
  return (
    <div className="m-body">
      <div><div className="eyebrow">{t("Feuille de temps")}</div><h1 style={{ fontSize: 22, margin: 0 }}>{t("Historique d'activité")}</h1></div>
      <div className="seg full"><button className={mode === "week" ? "on" : ""} onClick={() => { setM("week"); setOffset(0); }}>{t("Semaine")}</button><button className={mode === "month" ? "on" : ""} onClick={() => { setM("month"); setOffset(0); }}>{t("Mois")}</button></div>
      <div className="row"><button className="ghost sm" onClick={() => setOffset(offset - 1)} aria-label={t("Période précédente")}><Icon name="chevron_left" className="flip" /></button><b className="end" style={{ margin: "0 auto" }}>{dateFr(iso(from))} – {dateFr(iso(to))}</b><button className="ghost sm" onClick={() => setOffset(offset + 1)} aria-label={t("Période suivante")}><Icon name="chevron_right" className="flip" /></button></div>
      <ErrorBanner error={error} />
      {data && <div className="card"><div className="muted small">{t("Cumul")}</div><div className="row"><span className="mono" style={{ fontSize: 30, fontWeight: 700 }}>{hm(data.totals.worked_min)}</span><span className="muted mono">/ {hm(data.totals.expected_min)}</span>{data.totals.overtime_min > 0 && <Pill tone="info" icon="trending_up">+{hm(data.totals.overtime_min)} {t("sup. pot.")}</Pill>}</div>
        <div className="bar-track" style={{ margin: "8px 0" }}><div className="bar-fill" style={{ width: `${Math.min(100, pct)}%` }} /></div><div className="small muted">{t("{n}% réalisé · retards cumulés {m} min", { n: pct, m: data.totals.late_min })}</div></div>}
      {data?.days.map((d) => (
        <div className="card" key={d.id}><div className="row"><b>{dateFr(d.work_date)}</b><span className="end"><StatusPill status={d.status} /></span></div>
          <div className="punches" style={{ margin: "8px 0" }}>{d.punch_times.length ? d.punch_times.map((p, i) => <span key={i}>{p.slice(11, 16)}</span>) : <span className="muted">{t("Aucun pointage")}</span>}</div>
          <div className="row small muted"><span>{t("Travail")} {hm(d.worked_min)}</span>{d.late_min > 0 && <span className="err">{t("Retard {n} min", { n: d.late_min })}</span>}{d.anomalies.length > 0 && <span className="err"><Icon name="info" />{t("Anomalie : à régulariser auprès des RH")}</span>}</div></div>))}
      {data && !data.days.length && <p className="muted">{t("Aucune journée sur cette période.")}</p>}
    </div>
  );
}

function Planning() {
  const { data, error } = useLoad(api.mePlanning, []);
  return (
    <div className="m-body"><div><div className="eyebrow">{t("Planning")}</div><h1 style={{ fontSize: 22, margin: 0 }}>{t("14 prochains jours")}</h1></div><ErrorBanner error={error} />
      {data?.days.map((d) => (
        <div className="card" key={d.date}><div className="row"><Icon name={d.holiday ? "celebration" : d.shift ? (d.shift.crosses_midnight ? "bedtime" : "wb_sunny") : "home_work"} className="muted" /><b>{dateFr(d.date)}</b>
          {d.holiday ? <span className="end"><Pill>{t("Férié")}</Pill></span> : d.shift ? <span className="end mono" dir="ltr">{d.shift.start} → {d.shift.end}</span> : <span className="end"><Pill>{t("Repos")}</Pill></span>}</div>
          {d.shift && !d.holiday && <div className="small muted">{d.shift.name}{d.shift.crosses_midnight && ` · ${t("termine le lendemain")}`}</div>}</div>))}
    </div>
  );
}

function Profile({ onLogout, onLang }: { onLogout: () => void; onLang: (l: Lang) => void }) {
  const { data, error } = useLoad(api.me, []);
  const [mode, setM] = useState<Mode>(getMode());
  const themes: [Mode, string, string][] = [["light", tk("Clair"), "light_mode"], ["dark", tk("Sombre"), "dark_mode"], ["auto", tk("Auto"), "brightness_auto"]];
  return (
    <div className="m-body"><h1 style={{ fontSize: 22, margin: 0 }}>{t("Profil")}</h1><ErrorBanner error={error} />
      {data && <div className="card"><h2><Icon name="badge" className="muted" />{data.employee.first_name} {data.employee.last_name}</h2><div className="muted">{data.employee.job_title || "—"}</div>
        <div className="dayline"><span>{t("Matricule")}</span><b className="mono">{data.employee.matricule}</b></div><div className="dayline"><span>{t("Unité")}</span><b>{data.employee.org_unit ?? "—"}</b></div></div>}
      <div className="card"><h2><Icon name="tune" className="muted" />{t("Préférences")}</h2>
        <div className="opt"><Icon name="bedtime" /><div style={{ flex: 1 }}><b>{t("Mode nuit")}</b><div className="small muted">{t("Thème de l'application")}</div></div></div>
        <div className="seg full">{themes.map(([m, label, icon]) => <button key={m} className={mode === m ? "on" : ""} onClick={() => { setMode(m); setM(m); }}><Icon name={icon} />{t(label)}</button>)}</div>
        <div className="opt"><Icon name="translate" /><div style={{ flex: 1 }}><b>{t("Langue")}</b></div></div>
        <div className="seg full">{LANGS.map((l) => <button key={l.code} className={getLang() === l.code ? "on" : ""} onClick={() => { setLang(l.code); onLang(l.code); }}>{l.label}</button>)}</div></div>
      <div className="card"><h2><Icon name="verified_user" className="muted" />{t("Confidentialité")}</h2><p className="muted small">{t("Badgeo n'enregistre que l'heure de vos pointages. Aucune géolocalisation ni donnée biométrique n'est collectée par cette application.")}</p></div>
      <button className="ghost" onClick={onLogout}><Icon name="logout" className="flip" />{t("Se déconnecter")}</button></div>
  );
}

export default function Mobile({ onLogout, onLang }: { onLogout: () => void; onLang: (l: Lang) => void }) {
  const [tab, setTab] = useState<Tab>("pointer");
  return (
    <div className="m">
      <div className="m-top"><Logo height={30} /><span className="muted small">{t(LABEL[tab])}</span></div>
      {tab === "pointer" && <Pointer />}{tab === "historique" && <History />}{tab === "planning" && <Planning />}{tab === "profil" && <Profile onLogout={onLogout} onLang={onLang} />}
      <nav className="m-nav" aria-label={t("Navigation")}><div>{(Object.keys(LABEL) as Tab[]).map((k) => (
        <a key={k} href="#" className={tab === k ? "on" : ""} aria-current={tab === k ? "page" : undefined} onClick={(e) => { e.preventDefault(); setTab(k); }}><Icon name={ICON[k]} />{t(LABEL[k])}</a>))}</div></nav>
    </div>
  );
}
