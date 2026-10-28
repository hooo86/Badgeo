import { FormEvent, useState } from "react";
import * as api from "../api";
import { ErrorBanner, Field, Pill, useLoad } from "../ui";

const ROLES: Record<string, string> = { sysadmin: "Administrateur système", device_admin: "Administrateur des pointeuses", hr_manager: "Responsable RH",
  hr_staff: "Gestionnaire RH", dept_head: "Responsable de direction", viewer: "Consultation", employee: "Employé (application mobile)" };

export default function Users() {
  const { data, error, reload } = useLoad(() => api.list<api.UserRow>("/users/", { ordering: "username" }), []);
  const units = useLoad(() => api.list<{ id: number; name: string }>("/org-units/"), []);
  const emps = useLoad(() => api.list<api.Employee & { user: number | null }>("/employees/", { status: "active" }), []);
  const [msg, setMsg] = useState(""), [info, setInfo] = useState("");
  const [role, setRole] = useState("viewer");
  const add = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget), form = e.currentTarget;
    try {
      const u = await api.create<api.UserRow>("/users/", {
        username: f.get("username"), first_name: f.get("first_name"), last_name: f.get("last_name"), email: f.get("email"), role: f.get("role"),
        password: f.get("password"), scopes: f.getAll("scopes").map(Number),
      });
      if (f.get("employee")) await api.patch(`/employees/${f.get("employee")}/`, { user: u.id });
      form.reset(); setRole("viewer"); setMsg(""); setInfo(`Compte ${u.username} créé : mot de passe provisoire, à changer à la première connexion.`); reload(); emps.reload();
    } catch (x) { setMsg((x as Error).message); }
  };
  const toggle = (u: api.UserRow) => api.patch(`/users/${u.id}/`, { is_active: !u.is_active }).then(reload).catch((e) => setMsg(e.message));
  const reset = (u: api.UserRow) => { const p = prompt(`Nouveau mot de passe provisoire pour ${u.username} (10 caractères minimum) :`); if (p) api.patch(`/users/${u.id}/`, { password: p }).then(() => setInfo("Mot de passe provisoire défini ; l'utilisateur devra le changer.")).catch((e) => setMsg(e.message)); };
  const scoped = role === "dept_head" || role === "viewer";
  return (
    <>
      <div className="head"><div><div className="eyebrow">Sécurité</div><h1>Utilisateurs et rôles</h1></div></div>
      <form className="card filters" onSubmit={add}>
        <Field label="Identifiant"><input name="username" required /></Field><Field label="Prénom"><input name="first_name" /></Field><Field label="Nom"><input name="last_name" /></Field>
        <Field label="E-mail"><input name="email" type="email" /></Field>
        <Field label="Rôle"><select name="role" value={role} onChange={(e) => setRole(e.target.value)}>{Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
        {role === "employee" && <Field label="Employé lié"><select name="employee" required><option value="">—</option>{emps.data?.results.filter((x) => !x.user).map((x) => <option key={x.id} value={x.id}>{x.last_name} {x.first_name} (#{x.matricule})</option>)}</select></Field>}
        {scoped && <Field label="Périmètre (Ctrl pour plusieurs)"><select name="scopes" multiple size={3}>{units.data?.results.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</select></Field>}
        <Field label="Mot de passe provisoire"><input name="password" type="password" minLength={10} required autoComplete="new-password" /></Field><button>Créer</button></form>
      <ErrorBanner error={error || msg} />{info && <div className="banner">{info}</div>}
      <div className="table-wrap"><table><thead><tr><th>Identifiant</th><th>Nom</th><th>Rôle</th><th>État</th><th></th></tr></thead>
        <tbody>{data?.results.map((u) => (<tr key={u.id}><td><b>{u.username}</b>{u.must_change_password && <div className="small muted">mot de passe provisoire</div>}</td><td>{u.first_name} {u.last_name}</td>
          <td>{ROLES[u.role] ?? u.role}</td><td><Pill tone={u.is_active ? "ok" : "bad"}>{u.is_active ? "Actif" : "Désactivé"}</Pill></td>
          <td><div className="row"><button className="sm ghost" onClick={() => reset(u)}>Nouveau mot de passe</button><button className="sm ghost" onClick={() => toggle(u)}>{u.is_active ? "Désactiver" : "Réactiver"}</button></div></td></tr>))}</tbody></table></div>
    </>
  );
}
