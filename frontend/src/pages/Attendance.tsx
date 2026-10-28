import { useState } from "react";
import * as api from "../api";
import { ANOMALY, ErrorBanner, Field, hm, monthStart, Pager, StatusPill, time, today, useLoad, dateFr } from "../ui";

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
  const flagged = (d: api.Day) => d.status === "incomplete" || d.anomalies.length > 0;

  return (
    <>
      <div className="head"><div><div className="eyebrow">Gestion du temps</div><h1>{onlyAnomalies ? "Anomalies et corrections" : "Pointages et feuilles de temps"}</h1></div>
        <div className="row"><button className="ghost" onClick={() => api.download(`/reports/daily/?from=${from}&to=${to}&fmt=xlsx`, "presences.xlsx")}>Excel</button>
          <button className="ghost" onClick={() => api.download(`/reports/daily/?from=${from}&to=${to}&fmt=pdf`, "presences.pdf")}>PDF</button></div></div>
      <div className="filters">
        <Field label="Du"><input type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(1); }} /></Field>
        <Field label="Au"><input type="date" value={to} onChange={(e) => { setTo(e.target.value); setPage(1); }} /></Field>
        <Field label="Statut"><select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">Tous</option><option value="incomplete,no_punch">À examiner (incomplet / sans pointage)</option>
          <option value="present">Présent</option><option value="absent">Absent</option><option value="leave,sick,mission,permission">Absences justifiées</option></select></Field>
        <Field label="Recherche"><input placeholder="Nom ou matricule" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></Field>
      </div>
      <ErrorBanner error={error} />
      <div className="table-wrap"><table>
        <thead><tr><th className="sort" onClick={() => sort("work_date")}>Date</th><th className="sort" onClick={() => sort("employee__last_name")}>Collaborateur</th>
          <th>Horaire</th><th>Pointages</th><th className="sort" onClick={() => sort("late_min")}>Retard</th><th>Travail</th><th className="sort" onClick={() => sort("overtime_min")}>HS pot.</th><th>Statut</th><th></th></tr></thead>
        <tbody>{data?.results.map((d) => (
          <tr key={d.id} className={flagged(d) ? "flag" : ""}>
            <td>{dateFr(d.work_date)}</td>
            <td><b>{d.employee_name}</b><div className="small muted">#{d.matricule}</div></td>
            <td>{d.shift_name ?? "—"}</td>
            <td><div className="punches">{d.punch_times.length ? d.punch_times.map((p, i) => <span key={i}>{p.slice(11, 16)}</span>) : "—"}</div>
              {d.anomalies.map((a) => <div key={a} className="small err">{ANOMALY[a] ?? a}</div>)}</td>
            <td>{d.late_min ? `${d.late_min} min` : "—"}</td><td>{hm(d.worked_min)}</td><td>{d.overtime_min ? hm(d.overtime_min) : "—"}</td>
            <td><StatusPill status={d.status} /></td>
            <td>{["incomplete", "no_punch", "absent"].includes(d.status) && <button className="sm" onClick={() => setFix(d)}>Corriger</button>}</td>
          </tr>))}
          {data && !data.results.length && <tr><td colSpan={9} className="muted">Aucune journée sur cette période.</td></tr>}</tbody></table>
        {data && <Pager page={page} count={data.count} size={SIZE} onPage={setPage} />}</div>
      {fix && <CorrectionDialog day={fix} onClose={(ok) => { setFix(null); if (ok) reload(); }} />}
    </>
  );
}

export function CorrectionDialog({ day, onClose }: { day: api.Day; onClose: (done: boolean) => void }) {
  const [kind, setKind] = useState("add_punch"), [t, setT] = useState("17:00"), [status, setStatus] = useState("absent");
  const [reason, setReason] = useState(""), [err, setErr] = useState("");
  const submit = async () => {
    try {
      await api.create("/corrections/", {
        employee: day.employee, work_date: day.work_date, kind, reason,
        ...(kind === "add_punch" ? { new_timestamp: `${day.work_date}T${t}:00` /* naive: interpreted in the company timezone by the server */ } : { new_status: status }),
      });
      onClose(true);
    } catch (e) { setErr((e as Error).message); }
  };
  return (
    <div style={{ position: "fixed", inset: 0, background: "#0008", display: "grid", placeItems: "center", padding: 16, zIndex: 10 }} role="dialog" aria-modal="true">
      <div className="card" style={{ width: "100%", maxWidth: 440, display: "grid", gap: 12 }}>
        <h2>Proposer une correction</h2>
        <div className="muted">{day.employee_name} · {dateFr(day.work_date)} · pointages actuels : {day.punch_times.map((p) => p.slice(11, 16)).join(", ") || "aucun"}</div>
        <Field label="Type"><select value={kind} onChange={(e) => setKind(e.target.value)}><option value="add_punch">Ajouter un pointage manquant</option><option value="set_status">Forcer le statut de la journée</option></select></Field>
        {kind === "add_punch" ? <Field label="Heure"><input type="time" value={t} onChange={(e) => setT(e.target.value)} /></Field>
          : <Field label="Statut"><select value={status} onChange={(e) => setStatus(e.target.value)}>{["present", "absent", "leave", "sick", "mission", "permission", "rest", "holiday"].map((s) => <option key={s} value={s}>{s}</option>)}</select></Field>}
        <Field label="Justification (obligatoire)"><textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
        {err && <div className="err">{err}</div>}
        <div className="row"><button onClick={submit} disabled={reason.trim().length < 5}>Soumettre pour validation</button><button className="ghost" onClick={() => onClose(false)}>Annuler</button></div>
        <p className="small muted">Les pointages bruts ne sont jamais modifiés : la correction est validée par un responsable puis ajoutée à part.</p>
      </div>
    </div>
  );
}
