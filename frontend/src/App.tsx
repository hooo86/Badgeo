import { FormEvent, useEffect, useState } from "react";
import * as api from "./api";
import { useLoad } from "./ui";
import Attendance from "./pages/Attendance";
import Audit from "./pages/Audit";
import Corrections from "./pages/Corrections";
import Dashboard from "./pages/Dashboard";
import Devices from "./pages/Devices";
import Employees from "./pages/Employees";
import { Leaves, Shifts } from "./pages/Planning";
import Reports from "./pages/Reports";
import Mobile from "./mobile/Mobile";
import Backups from "./pages/Backups";
import LicencePage, { Activation, ChangePassword } from "./pages/Licence";
import Users from "./pages/Users";

function Login({ onDone }: { onDone: () => void }) {
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setBusy(true);
    const f = new FormData(e.currentTarget);
    try { await api.login(String(f.get("u")), String(f.get("p"))); onDone(); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="login"><form className="card" onSubmit={submit}>
      <img src="/logo.svg" alt="Badgeo" height={44} style={{ justifySelf: "start" }} />
      <h1 style={{ fontSize: 22, margin: 0 }}>Connexion</h1>
      <input name="u" placeholder="Utilisateur" autoComplete="username" required /><input name="p" type="password" placeholder="Mot de passe" autoComplete="current-password" required />
      <button disabled={busy}>Se connecter</button>{err && <div className="err">{err}</div>}</form></div>
  );
}

type Route = { path: string; label: string; roles?: string[]; el: (w: api.Who) => JSX.Element };
const HR = ["sysadmin", "hr_manager", "hr_staff"];
const ROUTES: Route[] = [
  { path: "dashboard", label: "Tableau de bord", el: () => <Dashboard /> },
  { path: "pointages", label: "Pointages et feuilles", el: () => <Attendance /> },
  { path: "personnel", label: "Personnel", el: (w) => <Employees canWrite={HR.includes(w.role ?? "")} /> },
  { path: "horaires", label: "Horaires et équipes", el: (w) => <Shifts canWrite={["sysadmin", "hr_manager"].includes(w.role ?? "")} /> },
  { path: "absences", label: "Absences et autorisations", el: (w) => <Leaves canWrite={HR.includes(w.role ?? "")} /> },
  { path: "anomalies", label: "Anomalies", roles: HR, el: () => <Attendance onlyAnomalies /> },
  { path: "corrections", label: "Corrections", roles: HR, el: (w) => <Corrections canReview={["sysadmin", "hr_manager"].includes(w.role ?? "")} /> },
  { path: "pointeuses", label: "Pointeuses", roles: ["sysadmin", "device_admin", "hr_manager", "hr_staff"], el: (w) => <Devices canWrite={["sysadmin", "device_admin"].includes(w.role ?? "")} /> },
  { path: "rapports", label: "Rapports", el: () => <Reports /> },
  { path: "utilisateurs", label: "Utilisateurs et rôles", roles: ["sysadmin"], el: () => <Users /> },
  { path: "sauvegardes", label: "Sauvegardes", roles: ["sysadmin"], el: () => <Backups /> },
  { path: "licence", label: "Licence et compte", el: (w) => <LicencePage canEdit={w.role === "sysadmin"} /> },
  { path: "journaux", label: "Journaux d'audit", roles: ["sysadmin", "hr_manager"], el: () => <Audit /> },
];

function LicenceBanner() {
  const { data } = useLoad(api.licence, [], 600000);
  const l = data?.licence;
  if (!l) return null;
  if (l.expiree) return <div className="banner bad" style={{ margin: 0, borderRadius: 0 }}>Licence expirée : Badgeo est en lecture seule (la sauvegarde reste possible). <a href="#/licence">Saisir une nouvelle clé</a></div>;
  if (l.essai || (l.jours_restants !== null && l.jours_restants <= 30)) return <div className="banner" style={{ margin: 0, borderRadius: 0 }}>{l.essai ? "Licence d'essai" : "Licence"} : {l.jours_restants} jour(s) restant(s). <a href="#/licence">Détails</a></div>;
  return null;
}

function Admin({ who, onLogout }: { who: api.Who; onLogout: () => void }) {
  const routes = ROUTES.filter((r) => !r.roles || r.roles.includes(who.role ?? ""));
  const read = () => location.hash.replace("#/", "") || "dashboard";
  const [path, setPath] = useState(read());
  useEffect(() => { const h = () => setPath(read()); window.addEventListener("hashchange", h); return () => window.removeEventListener("hashchange", h); }, []);
  const route = routes.find((r) => r.path === path) ?? routes[0];
  return (
    <div className="shell">
      <aside className="side"><img src="/logo.svg" alt="Badgeo" />
        {routes.map((r) => <a key={r.path} href={`#/${r.path}`} className={r.path === route.path ? "on" : ""}>{r.label}</a>)}
        <div className="who"><b>{who.name}</b><div className="muted">{who.role}</div><button className="ghost sm" style={{ marginTop: 8 }} onClick={onLogout}>Déconnexion</button></div></aside>
      <div style={{ minWidth: 0 }}><LicenceBanner /><main className="content" key={route.path}>{route.el(who)}</main></div>
    </div>
  );
}

export default function App() {
  const [logged, setLogged] = useState(api.isLogged());
  const [lic, setLic] = useState<api.LicenceState | null>(null), [licErr, setLicErr] = useState("");
  const loadLic = () => api.licence().then(setLic).catch((e) => setLicErr(e.message));
  useEffect(() => { loadLic(); }, []);
  const [who, setWho] = useState<api.Who | null>(null), [err, setErr] = useState("");
  const logout = () => { api.setToken(null); setWho(null); setLogged(false); };
  useEffect(() => { const h = () => logout(); window.addEventListener("badgeo:logout", h); return () => window.removeEventListener("badgeo:logout", h); }, []);
  useEffect(() => { if (logged) api.whoami().then(setWho).catch((e) => setErr(e.message)); }, [logged]);
  if (licErr) return <div className="login"><div className="banner bad">{licErr}</div></div>;
  if (!lic) return <div className="login"><p className="muted">Chargement…</p></div>;
  if (lic.requise && !lic.active) return <Activation state={lic} onDone={loadLic} />;
  if (!logged) return <Login onDone={() => setLogged(true)} />;
  if (!who) return <div className="login">{err ? <div className="banner bad">{err}</div> : <p className="muted">Chargement…</p>}</div>;
  if (who.must_change_password) return <ChangePassword forced onDone={() => { setWho(null); api.whoami().then(setWho); }} />;
  if (who.role === null) return <div className="login"><div className="card"><h2>Accès non configuré</h2><p>Votre compte n'a pas de rôle. Contactez l'administrateur.</p><button onClick={logout}>Déconnexion</button></div></div>;
  return who.role === "employee" ? <Mobile onLogout={logout} /> : <Admin who={who} onLogout={logout} />;
}
