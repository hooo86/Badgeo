import { useState } from "react";
import * as api from "../api";
import { dateFr, dateTime, ErrorBanner, Pill, useLoad } from "../ui";

export default function Corrections({ canReview }: { canReview: boolean }) {
  const [state, setState] = useState("pending");
  const { data, error, reload } = useLoad(() => api.list<api.Correction>("/corrections/", { state }), [state]);
  const [msg, setMsg] = useState("");
  const act = async (id: number, what: "validate" | "reject") => {
    const note = what === "reject" ? prompt("Motif du rejet (obligatoire)") ?? "" : "";
    if (what === "reject" && !note.trim()) return;
    try { await api.post(`/corrections/${id}/${what}/`, { note }); setMsg(""); reload(); } catch (e) { setMsg((e as Error).message); }
  };
  const tone = { pending: "warn", validated: "ok", rejected: "bad" } as const;
  const label = { pending: "En attente", validated: "Validée", rejected: "Rejetée" } as const;
  return (
    <>
      <div className="head"><div><div className="eyebrow">Contrôle RH</div><h1>Corrections à valider</h1></div>
        <select value={state} onChange={(e) => setState(e.target.value)}><option value="pending">En attente</option><option value="validated">Validées</option><option value="rejected">Rejetées</option><option value="">Toutes</option></select></div>
      <ErrorBanner error={error || msg} />
      <div className="table-wrap"><table><thead><tr><th>Jour</th><th>Demande</th><th>Avant</th><th>Justification</th><th>État</th><th></th></tr></thead>
        <tbody>{data?.results.map((c) => (
          <tr key={c.id}><td>{dateFr(c.work_date)}<div className="small muted">Employé #{c.employee}</div></td>
            <td>{c.kind === "add_punch" ? `Ajouter un pointage à ${dateTime(c.new_timestamp).slice(-5)}` : `Statut → ${c.new_status}`}</td>
            <td className="small">{String(c.initial.status)} · {(c.initial.punch_times as string[] | undefined)?.map((p) => p.slice(11, 16)).join(", ") || "aucun pointage"}</td>
            <td>{c.reason}{c.review_note && <div className="small muted">Note : {c.review_note}</div>}<div className="small muted">{dateTime(c.created_at)}</div></td>
            <td><Pill tone={tone[c.state]}>{label[c.state]}</Pill></td>
            <td>{c.state === "pending" && canReview && <div className="row"><button className="sm" onClick={() => act(c.id, "validate")}>Valider</button><button className="sm ghost" onClick={() => act(c.id, "reject")}>Rejeter</button></div>}</td></tr>))}
          {data && !data.results.length && <tr><td colSpan={6} className="muted">Aucune correction.</td></tr>}</tbody></table></div>
      {!canReview && <p className="muted small">La validation est réservée au responsable RH ; l'auteur d'une correction ne peut pas la valider lui-même.</p>}
    </>
  );
}
