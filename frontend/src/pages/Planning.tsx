import { FormEvent, useState } from "react";
import * as api from "../api";
import { t, tk } from "../i18n";
import { dateFr, ErrorBanner, Field, Icon, Pill, today, useLoad } from "../ui";

interface Shift { id: number; name: string; kind: string; start_time: string; end_time: string; break_minutes: number; late_grace_minutes: number; work_days: number[]; crosses_midnight: boolean; expected_minutes: number }
interface Leave { id: number; employee: number; kind: string; start_date: string; end_date: string; justified: boolean; note: string }
const DAYS = ["L", "M", "M", "J", "V", "S", "D"];
const KIND: Record<string, string> = { leave: tk("Congé"), permission: tk("Permission"), mission: tk("Mission"), sick: tk("Arrêt maladie"), rest: tk("Repos exceptionnel") };
const KIND_ICON: Record<string, string> = { leave: "beach_access", permission: "more_time", mission: "flight_takeoff", sick: "medical_services", rest: "bedtime" };
const SHIFT_KIND: Record<string, string> = { fixed: tk("Fixe"), flexible: tk("Variable"), night: tk("Nuit") };

export function Shifts({ canWrite }: { canWrite: boolean }) {
  const { data, error, reload } = useLoad(() => api.list<Shift>("/shifts/"), []);
  const [msg, setMsg] = useState("");
  const add = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget), form = e.currentTarget;
    try {
      await api.create("/shifts/", { name: f.get("name"), kind: f.get("kind"), start_time: f.get("start"), end_time: f.get("end"), break_minutes: Number(f.get("brk")),
        late_grace_minutes: Number(f.get("grace")), work_days: [0, 1, 2, 3, 4], ...(f.get("latest") ? { latest_in: f.get("latest") } : {}) });
      form.reset(); reload(); setMsg("");
    } catch (x) { setMsg((x as Error).message); }
  };
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Organisation du temps")}</div><h1>{t("Horaires et équipes")}</h1></div></div>
      {canWrite && <form className="card filters pad-b" onSubmit={add}>
        <Field label={t("Nom")}><input name="name" required /></Field>
        <Field label={t("Type")}><select name="kind"><option value="fixed">{t("Fixe")}</option><option value="flexible">{t("Variable")}</option><option value="night">{t("Nuit")}</option></select></Field>
        <Field label={t("Début")}><input type="time" name="start" required /></Field><Field label={t("Fin (après minuit si inférieur)")}><input type="time" name="end" required /></Field>
        <Field label={t("Pause (min)")}><input type="number" name="brk" defaultValue={60} style={{ width: 90 }} /></Field><Field label={t("Tolérance (min)")}><input type="number" name="grace" defaultValue={5} style={{ width: 90 }} /></Field>
        <Field label={t("Arrivée max (variable)")}><input type="time" name="latest" /></Field><button><Icon name="add" />{t("Créer (lun–ven)")}</button></form>}
      <ErrorBanner error={error || msg} />
      <div className="table-wrap"><table><thead><tr><th>{t("Horaire")}</th><th>{t("Plage")}</th><th>{t("Pause")}</th><th>{t("Durée théorique")}</th><th>{t("Tolérance")}</th><th>{t("Jours")}</th></tr></thead>
        <tbody>{data?.results.map((s) => (<tr key={s.id}><td><b>{s.name}</b> <Pill icon={s.kind === "night" ? "bedtime" : "wb_sunny"}>{t(SHIFT_KIND[s.kind] ?? s.kind)}</Pill></td>
          <td className="mono" dir="ltr">{s.start_time.slice(0, 5)} → {s.end_time.slice(0, 5)} {s.crosses_midnight && <Pill tone="info">+1 j</Pill>}</td>
          <td>{s.break_minutes} min</td><td className="mono">{Math.floor(s.expected_minutes / 60)}h{String(s.expected_minutes % 60).padStart(2, "0")}</td><td>{s.late_grace_minutes} min</td>
          <td>{DAYS.map((d, i) => <span key={i} style={{ opacity: s.work_days.includes(i) ? 1 : .25, fontWeight: 700, marginInlineEnd: 4 }}>{d}</span>)}</td></tr>))}
          {data && !data.results.length && <tr><td colSpan={6} className="muted">{t("Aucun horaire. Créez-en un, puis affectez-le via /api/shift-assignments/.")}</td></tr>}</tbody></table></div>
    </>
  );
}

export function Leaves({ canWrite }: { canWrite: boolean }) {
  const { data, error, reload } = useLoad(() => api.list<Leave>("/leaves/", { ordering: "-start_date" }), []);
  const emps = useLoad(() => api.list<api.Employee>("/employees/", { status: "active" }), []);
  const [msg, setMsg] = useState("");
  const add = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget), form = e.currentTarget;
    try { await api.create("/leaves/", { employee: Number(f.get("employee")), kind: f.get("kind"), start_date: f.get("from"), end_date: f.get("to"), justified: f.get("justified") === "on", note: f.get("note") }); form.reset(); reload(); setMsg(""); }
    catch (x) { setMsg((x as Error).message); }
  };
  const name = (id: number) => { const e = emps.data?.results.find((x) => x.id === id); return e ? `${e.last_name} ${e.first_name}` : `#${id}`; };
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Gestion du temps")}</div><h1>{t("Absences et autorisations")}</h1></div></div>
      {canWrite && <form className="card filters pad-b" onSubmit={add}>
        <Field label={t("Employé")}><select name="employee" required>{emps.data?.results.map((e) => <option key={e.id} value={e.id}>{e.last_name} {e.first_name}</option>)}</select></Field>
        <Field label={t("Nature")}><select name="kind">{Object.entries(KIND).map(([k, v]) => <option key={k} value={k}>{t(v)}</option>)}</select></Field>
        <Field label={t("Du")}><input type="date" name="from" defaultValue={today()} required /></Field><Field label={t("Au")}><input type="date" name="to" defaultValue={today()} required /></Field>
        <Field label={t("Note")}><input name="note" /></Field><label className="row"><input type="checkbox" name="justified" defaultChecked /> {t("Justifiée")}</label><button><Icon name="add" />{t("Enregistrer")}</button></form>}
      <ErrorBanner error={error || msg} />
      <div className="table-wrap"><table><thead><tr><th>{t("Employé")}</th><th>{t("Nature")}</th><th>{t("Période")}</th><th>{t("Justifiée")}</th><th>{t("Note")}</th><th></th></tr></thead>
        <tbody>{data?.results.map((l) => (<tr key={l.id}><td>{name(l.employee)}</td><td><Pill tone="info" icon={KIND_ICON[l.kind]}>{t(KIND[l.kind])}</Pill></td><td>{dateFr(l.start_date)} → {dateFr(l.end_date)}</td>
          <td><Pill tone={l.justified ? "ok" : "bad"}>{l.justified ? t("Oui") : t("Non")}</Pill></td><td>{l.note}</td>
          <td>{canWrite && <button className="sm danger" onClick={() => confirm(t("Supprimer ?")) && api.remove(`/leaves/${l.id}/`).then(reload)}><Icon name="delete" />{t("Supprimer")}</button>}</td></tr>))}
          {data && !data.results.length && <tr><td colSpan={6} className="muted">{t("Aucune absence enregistrée.")}</td></tr>}</tbody></table></div>
    </>
  );
}
