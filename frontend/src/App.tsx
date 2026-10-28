import { FormEvent, useEffect, useState } from "react";
import * as api from "./api";
import { t, tk, type Lang } from "./i18n";
import Mobile from "./mobile/Mobile";
import Attendance from "./pages/Attendance";
import Audit from "./pages/Audit";
import Backups from "./pages/Backups";
import Corrections from "./pages/Corrections";
import Dashboard from "./pages/Dashboard";
import Devices from "./pages/Devices";
import Employees from "./pages/Employees";
import LicencePage, { Activation, ChangePassword } from "./pages/Licence";
import { Leaves, Shifts } from "./pages/Planning";
import Reports from "./pages/Reports";
import Users from "./pages/Users";
import { Icon, LangSwitch, Logo, ThemeSwitch, useLoad } from "./ui";

function Login({ onDone, onLang }: { onDone: () => void; onLang: (l: Lang) => void }) {
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setBusy(true);
    const f = new FormData(e.currentTarget);
    try { await api.login(String(f.get("u")), String(f.get("p"))); onDone(); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="login"><div className="corner"><LangSwitch onChange={onLang} /><ThemeSwitch /></div>
      <form className="card" onSubmit={submit}>
        <Logo height={44} />
        <h1 style={{ fontSize: 22, margin: 0 }}>{t("Connexion")}</h1>
        <input name="u" placeholder={t("Utilisateur")} autoComplete="username" required />
        <input name="p" type="password" placeholder={t("Mot de passe")} autoComplete="current-password" required />
        <button disabled={busy}><Icon name="login" />{t("Se connecter")}</button>{err && <div className="err">{t(err)}</div>}</form></div>
  );
}

type Route = { path: string; label: string; icon: string; roles?: string[]; el: (w: api.Who) => JSX.Element };
const HR = ["sysadmin", "hr_manager", "hr_staff"];
const ROUTES: Route[] = [
  { path: "dashboard", label: tk("Tableau de bord"), icon: "dashboard", el: () => <Dashboard /> },
  { path: "pointages", label: tk("Pointages et feuilles"), icon: "history_toggle_off", el: () => <Attendance /> },
  { path: "personnel", label: tk("Personnel"), icon: "groups", el: (w) => <Employees canWrite={HR.includes(w.role ?? "")} /> },
  { path: "horaires", label: tk("Horaires et équipes"), icon: "calendar_view_week", el: (w) => <Shifts canWrite={["sysadmin", "hr_manager"].includes(w.role ?? "")} /> },
  { path: "absences", label: tk("Absences et autorisations"), icon: "event_available", el: (w) => <Leaves canWrite={HR.includes(w.role ?? "")} /> },
  { path: "anomalies", label: tk("Anomalies"), icon: "fmd_bad", roles: HR, el: () => <Attendance onlyAnomalies /> },
  { path: "corrections", label: tk("Corrections"), icon: "rule", roles: HR, el: (w) => <Corrections canReview={["sysadmin", "hr_manager"].includes(w.role ?? "")} /> },
  { path: "pointeuses", label: tk("Pointeuses"), icon: "podcasts", roles: ["sysadmin", "device_admin", "hr_manager", "hr_staff"], el: (w) => <Devices canWrite={["sysadmin", "device_admin"].includes(w.role ?? "")} /> },
  { path: "rapports", label: tk("Rapports"), icon: "summarize", el: () => <Reports /> },
  { path: "utilisateurs", label: tk("Utilisateurs et rôles"), icon: "manage_accounts", roles: ["sysadmin"], el: () => <Users /> },
  { path: "sauvegardes", label: tk("Sauvegardes"), icon: "cloud_sync", roles: ["sysadmin"], el: () => <Backups /> },
  { path: "licence", label: tk("Licence et compte"), icon: "verified_user", el: (w) => <LicencePage canEdit={w.role === "sysadmin"} /> },
  { path: "journaux", label: tk("Journaux d'audit"), icon: "receipt_long", roles: ["sysadmin", "hr_manager"], el: () => <Audit /> },
];
const ROLE_LABEL: Record<string, string> = { sysadmin: tk("Administrateur système"), device_admin: tk("Administrateur des pointeuses"), hr_manager: tk("Responsable RH"),
  hr_staff: tk("Gestionnaire RH"), dept_head: tk("Responsable de direction"), viewer: tk("Consultation"), employee: tk("Employé") };

function LicenceBanner() {
  const { data } = useLoad(api.licence, [], 600000);
  const l = data?.licence;
  if (!l) return null;
  if (l.expiree) return <div className="banner bad" style={{ margin: 0, borderRadius: 0 }}><Icon name="warning" />{t("Licence expirée : Badgeo est en lecture seule (la sauvegarde reste possible).")} <a href="#/licence">{t("Saisir une nouvelle clé")}</a></div>;
  if (l.essai || (l.jours_restants !== null && l.jours_restants <= 30))
    return <div className="banner" style={{ margin: 0, borderRadius: 0 }}><Icon name="info" />{l.essai ? t("Licence d'essai") : t("Licence")} : {t("{n} jour(s) restant(s)", { n: l.jours_restants ?? 0 })} <a href="#/licence">{t("Détails")}</a></div>;
  return null;
}

function Admin({ who, onLogout, onLang }: { who: api.Who; onLogout: () => void; onLang: (l: Lang) => void }) {
  const routes = ROUTES.filter((r) => !r.roles || r.roles.includes(who.role ?? ""));
  const read = () => location.hash.replace("#/", "") || "dashboard";
  const [path, setPath] = useState(read());
  useEffect(() => { const h = () => setPath(read()); window.addEventListener("hashchange", h); return () => window.removeEventListener("hashchange", h); }, []);
  const route = routes.find((r) => r.path === path) ?? routes[0];
  return (
    <div className="shell">
      <aside className="side"><div className="brand"><Logo height={34} /><span className="tag">{who.role === "sysadmin" ? "Admin" : "RH"}</span></div>
        <nav style={{ display: "contents" }} aria-label={t("Navigation")}>
          {routes.map((r) => <a key={r.path} href={`#/${r.path}`} className={r.path === route.path ? "on" : ""} aria-current={r.path === route.path ? "page" : undefined}><Icon name={r.icon} />{t(r.label)}</a>)}
        </nav>
        <div className="who"><b>{who.name}</b><div className="muted">{t(ROLE_LABEL[who.role ?? ""] ?? who.role ?? "")}</div></div></aside>
      <div className="main">
        <LicenceBanner />
        <div className="topbar"><LangSwitch onChange={onLang} /><ThemeSwitch />
          <button className="ghost sm" onClick={onLogout}><Icon name="logout" className="flip" />{t("Déconnexion")}</button></div>
        <main className="content" key={route.path}>{route.el(who)}</main>
      </div>
    </div>
  );
}

export default function App() {
  const [, setTick] = useState(0);
  const onLang = (_: Lang) => setTick((n) => n + 1);  // le changement de langue remonte tout l'arbre (clé ci-dessous)
  return <Inner key={String(document.documentElement.lang)} onLang={onLang} />;
}

function Inner({ onLang }: { onLang: (l: Lang) => void }) {
  const [logged, setLogged] = useState(api.isLogged());
  const [lic, setLic] = useState<api.LicenceState | null>(null), [licErr, setLicErr] = useState("");
  const loadLic = () => api.licence().then(setLic).catch((e) => setLicErr(e.message));
  useEffect(() => { loadLic(); }, []);
  const [who, setWho] = useState<api.Who | null>(null), [err, setErr] = useState("");
  const logout = () => { api.setToken(null); setWho(null); setLogged(false); };
  useEffect(() => { const h = () => logout(); window.addEventListener("badgeo:logout", h); return () => window.removeEventListener("badgeo:logout", h); }, []);
  useEffect(() => { if (logged) api.whoami().then(setWho).catch((e) => setErr(e.message)); }, [logged]);
  if (licErr) return <div className="login"><div className="banner bad">{t(licErr)}</div></div>;
  if (!lic) return <div className="login"><p className="muted">{t("Chargement…")}</p></div>;
  if (lic.requise && !lic.active) return <Activation state={lic} onDone={loadLic} onLang={onLang} />;
  if (!logged) return <Login onDone={() => setLogged(true)} onLang={onLang} />;
  if (!who) return <div className="login">{err ? <div className="banner bad">{t(err)}</div> : <p className="muted">{t("Chargement…")}</p>}</div>;
  if (who.must_change_password) return <ChangePassword forced onDone={() => { setWho(null); api.whoami().then(setWho); }} />;
  if (who.role === null) return <div className="login"><div className="card"><h2>{t("Accès non configuré")}</h2><p>{t("Votre compte n'a pas de rôle. Contactez l'administrateur.")}</p><button onClick={logout}>{t("Déconnexion")}</button></div></div>;
  return who.role === "employee" ? <Mobile onLogout={logout} onLang={onLang} /> : <Admin who={who} onLogout={logout} onLang={onLang} />;
}
