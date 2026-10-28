import { useState } from "react";
import * as api from "../api";
import { t, tk } from "../i18n";
import { anomalyLabel, dateFr, ErrorBanner, Field, hm, Icon, monthStart, Pager, StatusPill, today, useLoad } from "../ui";

const SIZE = 50;

export default function Attendance({ onlyAnomalies = false }: { onlyAnomalies?: boolean }) {
  const [from, setFrom] = useState(monthStart()), [to, setTo] = useState(today());
  const [status, setStatus] = useState(onlyAnomalies ? "incomplete,no_punch" : ""), [search, setSearch] = useState("");
  const [order, setOrder] = useState("-work_date"), [page, setPage] = useState(1);
  const [fix, setFix] = useState<api.Day | null>(null);
  const { data, error, reload } = useLoad(() => api.list<api.Day>("/attendance-days/", {
    work_date__gte: from, work_date__lte: to, status__in: status, search, ordering: order, page,
  }), [from, to, status, search, order, page]);
  const sort = (f: string) => setOrder(order === f ? `-${f}` : f);
  const arrow = (f: string) => (order === f ? <Icon name="expand_more" /> : order === `-${f}` ? <Icon name="expand_more" className="flip" /> : null);
  const flagged = (d: api.Day) => d.status === "incomplete" || d.anomalies.length > 0;

  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Gestion du temps")}</div><h1>{onlyAnomalies ? t("Anomalies et corrections") : t("Pointages et feuilles de temps")}</h1></div>
        <div className="row"><button className="ghost" onClick={() => api.download(`/reports/daily/?from=${from}&to=${to}&fmt=xlsx`, "presences.xlsx")}><Icon name="table_view" />Excel</button>
          <button className="ghost" onClick={() => api.download(`/reports/daily/?from=${from}&to=${to}&fmt=pdf`, "presences.pdf")}><Icon name="picture_as_pdf" />PDF</button></div></div>
      <div className="filters">
        <Field label={t("Du")}><input type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(1); }} /></Field>
        <Field label={t("Au")}><input type="date" value={to} onChange={(e) => { setTo(e.target.value); setPage(1); }} /></Field>
        <Field label={t("Statut")}><select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">{t("Tous")}</option><option value="incomplete,no_punch">{t("À examiner (incomplet / sans pointage)")}</option>
          <option value="present">{t("Présent")}</option><option value="absent">{t("Absent")}</option><option value="leave,sick,mission,permission">{t("Absences justifiées")}</option></select></Field>
        <Field label={t("Recherche")}><input placeholder={t("Nom ou matricule")} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></Field>
      </div>
      <ErrorBanner error={error} />
      <div className="table-wrap"><table>
        <thead><tr><th className="sort" onClick={() => sort("work_date")}>{t("Date")}{arrow("work_date")}</th><th className="sort" onClick={() => sort("employee__last_name")}>{t("Collaborateur")}{arrow("employee__last_name")}</th>
          <th>{t("Horaire")}</th><th>{t("Pointages")}</th><th className="sort" onClick={() => sort("late_min")}>{t("Retard")}{arrow("late_min")}</th><th>{t("Travail")}</th><th className="sort" onClick={() => sort("overtime_min")}>{t("HS pot.")}{arrow("overtime_min")}</th><th>{t("Statut")}</th><th></th></tr></thead>
        <tbody>{data?.results.map((d) => (
          <tr key={d.id} className={flagged(d) ? "flag" : ""}>
            <td>{dateFr(d.work_date)}</td>
            <td><b>{d.employee_name}</b><div className="small muted"><bdi dir="ltr">#{d.matricule}</bdi></div></td>
            <td>{d.shift_name ?? "—"}</td>
            <td><div className="punches">{d.punch_times.length ? d.punch_times.map((p, i) => <span key={i}>{p.slice(11, 16)}</span>) : "—"}</div>
              {d.anomalies.map((a) => <div key={a} className="small err">{anomalyLabel(a)}</div>)}</td>
            <td className="mono">{d.late_min ? `${d.late_min} min` : "—"}</td><td className="mono">{hm(d.worked_min)}</td><td className="mono">{d.overtime_min ? hm(d.overtime_min) : "—"}</td>
            <td><StatusPill status={d.status} /></td>
            <td>{["incomplete", "no_punch", "absent"].includes(d.status) && <button className="sm" onClick={() => setFix(d)}><Icon name="edit_calendar" />{t("Corriger")}</button>}</td>
          </tr>))}
          {data && !data.results.length && <tr><td colSpan={9} className="muted">{t("Aucune journée sur cette période.")}</td></tr>}</tbody></table>
        {data && <Pager page={page} count={data.count} size={SIZE} onPage={setPage} />}</div>
      {fix && <CorrectionDialog day={fix} onClose={(ok) => { setFix(null); if (ok) reload(); }} />}
    </>
  );
}

export function CorrectionDialog({ day, onClose }: { day: api.Day; onClose: (done: boolean) => void }) {
  const [kind, setKind] = useState("add_punch"), [tm, setTm] = useState("17:00"), [status, setStatus] = useState("absent");
  const [reason, setReason] = useState(""), [err, setErr] = useState("");
  const submit = async () => {
    try {
      await api.create("/corrections/", {
        employee: day.employee, work_date: day.work_date, kind, reason,
        ...(kind === "add_punch" ? { new_timestamp: `${day.work_date}T${tm}:00` /* naïf : interprété dans le fuseau de l'entreprise par le serveur */ } : { new_status: status }),
      });
      onClose(true);
    } catch (e) { setErr((e as Error).message); }
  };
  return (
    <div style={{ position: "fixed", inset: 0, background: "var(--overlay)", display: "grid", placeItems: "center", padding: 16, zIndex: 10 }} role="dialog" aria-modal="true">
      <div className="card" style={{ width: "100%", maxWidth: 440, display: "grid", gap: 12 }}>
        <h2><Icon name="edit_calendar" />{t("Proposer une correction")}</h2>
        <div className="muted">{day.employee_name} · {dateFr(day.work_date)} · {t("pointages actuels :")} {day.punch_times.map((p) => p.slice(11, 16)).join(", ") || t("aucun")}</div>
        <Field label={t("Type")}><select value={kind} onChange={(e) => setKind(e.target.value)}><option value="add_punch">{t("Ajouter un pointage manquant")}</option><option value="set_status">{t("Forcer le statut de la journée")}</option></select></Field>
        {kind === "add_punch" ? <Field label={t("Heure")}><input type="time" value={tm} onChange={(e) => setTm(e.target.value)} /></Field>
          : <Field label={t("Statut")}><select value={status} onChange={(e) => setStatus(e.target.value)}>{["present", "absent", "leave", "sick", "mission", "permission", "rest", "holiday"].map((s) => <option key={s} value={s}>{t({ present: tk("Présent"), absent: tk("Absent"), leave: tk("Congé"), sick: tk("Arrêt maladie"), mission: tk("Mission"), permission: tk("Permission"), rest: tk("Repos"), holiday: tk("Férié") }[s]!)}</option>)}</select></Field>}
        <Field label={t("Justification (obligatoire)")}><textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
        {err && <div className="err">{t(err)}</div>}
        <div className="row"><button onClick={submit} disabled={reason.trim().length < 5}><Icon name="send" className="flip" />{t("Soumettre pour validation")}</button><button className="ghost" onClick={() => onClose(false)}>{t("Annuler")}</button></div>
        <p className="small muted">{t("Les pointages bruts ne sont jamais modifiés : la correction est validée par un responsable puis ajoutée à part.")}</p>
      </div>
    </div>
  );
}
