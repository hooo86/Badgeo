import { FormEvent, useState } from "react";
import * as api from "../api";
import { t, tk } from "../i18n";
import { ErrorBanner, Field, Icon, Pill, useLoad } from "../ui";

const ROLES: Record<string, string> = { sysadmin: tk("Administrateur système"), device_admin: tk("Administrateur des pointeuses"), hr_manager: tk("Responsable RH"),
  hr_staff: tk("Gestionnaire RH"), dept_head: tk("Responsable de direction"), viewer: tk("Consultation"), employee: tk("Employé (application mobile)") };

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
      form.reset(); setRole("viewer"); setMsg(""); setInfo(t("Compte {name} créé : mot de passe provisoire, à changer à la première connexion.", { name: u.username })); reload(); emps.reload();
    } catch (x) { setMsg((x as Error).message); }
  };
  const toggle = (u: api.UserRow) => api.patch(`/users/${u.id}/`, { is_active: !u.is_active }).then(reload).catch((e) => setMsg(e.message));
  const reset = (u: api.UserRow) => { const p = prompt(t("Nouveau mot de passe provisoire pour {name} (10 caractères minimum) :", { name: u.username })); if (p) api.patch(`/users/${u.id}/`, { password: p }).then(() => setInfo(t("Mot de passe provisoire défini ; l'utilisateur devra le changer."))).catch((e) => setMsg(e.message)); };
  const scoped = role === "dept_head" || role === "viewer";
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Sécurité")}</div><h1>{t("Utilisateurs et rôles")}</h1></div></div>
      <form className="card filters pad-b" onSubmit={add}>
        <Field label={t("Identifiant")}><input name="username" required dir="ltr" /></Field><Field label={t("Prénom")}><input name="first_name" /></Field><Field label={t("Nom")}><input name="last_name" /></Field>
        <Field label={t("E-mail")}><input name="email" type="email" dir="ltr" /></Field>
        <Field label={t("Rôle")}><select name="role" value={role} onChange={(e) => setRole(e.target.value)}>{Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{t(v)}</option>)}</select></Field>
        {role === "employee" && <Field label={t("Employé lié")}><select name="employee" required><option value="">—</option>{emps.data?.results.filter((x) => !x.user).map((x) => <option key={x.id} value={x.id}>{x.last_name} {x.first_name} (#{x.matricule})</option>)}</select></Field>}
        {scoped && <Field label={t("Périmètre (Ctrl pour plusieurs)")}><select name="scopes" multiple size={3}>{units.data?.results.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</select></Field>}
        <Field label={t("Mot de passe provisoire")}><input name="password" type="password" minLength={10} required autoComplete="new-password" /></Field><button><Icon name="person_add" />{t("Créer")}</button></form>
      <ErrorBanner error={error || msg} />{info && <div className="banner"><Icon name="check_circle" />{info}</div>}
      <div className="table-wrap"><table><thead><tr><th>{t("Identifiant")}</th><th>{t("Nom")}</th><th>{t("Rôle")}</th><th>{t("État")}</th><th></th></tr></thead>
        <tbody>{data?.results.map((u) => (<tr key={u.id}><td><b dir="ltr">{u.username}</b>{u.must_change_password && <div className="small muted">{t("mot de passe provisoire")}</div>}</td><td>{u.first_name} {u.last_name}</td>
          <td>{t(ROLES[u.role] ?? u.role)}</td><td><Pill tone={u.is_active ? "ok" : "bad"}>{u.is_active ? t("Actif") : t("Désactivé")}</Pill></td>
          <td><div className="row"><button className="sm ghost" onClick={() => reset(u)}><Icon name="key" />{t("Nouveau mot de passe")}</button><button className="sm ghost" onClick={() => toggle(u)}>{u.is_active ? t("Désactiver") : t("Réactiver")}</button></div></td></tr>))}</tbody></table></div>
    </>
  );
}
