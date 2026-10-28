import { FormEvent, useEffect, useState } from "react";
import * as api from "./api";
import Attendance from "./pages/Attendance";
import Audit from "./pages/Audit";
import Corrections from "./pages/Corrections";
import Dashboard from "./pages/Dashboard";
import Devices from "./pages/Devices";
import Employees from "./pages/Employees";
import { Leaves, Shifts } from "./pages/Planning";
import Reports from "./pages/Reports";
import Mobile from "./mobile/Mobile";

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
  { path: "journaux", label: "Journaux d'audit", roles: ["sysadmin", "hr_manager"], el: () => <Audit /> },
];

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
      <main className="content" key={route.path}>{route.el(who)}</main>
    </div>
  );
}

export default function App() {
  const [logged, setLogged] = useState(api.isLogged());
  const [who, setWho] = useState<api.Who | null>(null), [err, setErr] = useState("");
  const logout = () => { api.setToken(null); setWho(null); setLogged(false); };
  useEffect(() => { const h = () => logout(); window.addEventListener("badgeo:logout", h); return () => window.removeEventListener("badgeo:logout", h); }, []);
  useEffect(() => { if (logged) api.whoami().then(setWho).catch((e) => setErr(e.message)); }, [logged]);
  if (!logged) return <Login onDone={() => setLogged(true)} />;
  if (!who) return <div className="login">{err ? <div className="banner bad">{err}</div> : <p className="muted">Chargement…</p>}</div>;
  if (who.role === null) return <div className="login"><div className="card"><h2>Accès non configuré</h2><p>Votre compte n'a pas de rôle. Contactez l'administrateur.</p><button onClick={logout}>Déconnexion</button></div></div>;
  return who.role === "employee" ? <Mobile onLogout={logout} /> : <Admin who={who} onLogout={logout} />;
}
