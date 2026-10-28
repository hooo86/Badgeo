import { useState } from "react";
import * as api from "../api";
import { t, tk } from "../i18n";
import { dateFr, dateTime, ErrorBanner, Icon, Pill, useLoad } from "../ui";

export default function Corrections({ canReview }: { canReview: boolean }) {
  const [state, setState] = useState("pending");
  const { data, error, reload } = useLoad(() => api.list<api.Correction>("/corrections/", { state }), [state]);
  const [msg, setMsg] = useState("");
  const act = async (id: number, what: "validate" | "reject") => {
    const note = what === "reject" ? prompt(t("Motif du rejet (obligatoire)")) ?? "" : "";
    if (what === "reject" && !note.trim()) return;
    try { await api.post(`/corrections/${id}/${what}/`, { note }); setMsg(""); reload(); } catch (e) { setMsg((e as Error).message); }
  };
  const tone = { pending: "warn", validated: "ok", rejected: "bad" } as const;
  const label = { pending: tk("En attente"), validated: tk("Validée"), rejected: tk("Rejetée") } as const;
  const icon = { pending: "schedule", validated: "task_alt", rejected: "block" } as const;
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Contrôle RH")}</div><h1>{t("Corrections à valider")}</h1></div>
        <select value={state} onChange={(e) => setState(e.target.value)} aria-label={t("Statut")}><option value="pending">{t("En attente")}</option><option value="validated">{t("Validées")}</option><option value="rejected">{t("Rejetées")}</option><option value="">{t("Toutes")}</option></select></div>
      <ErrorBanner error={error || msg} />
      <div className="table-wrap"><table><thead><tr><th>{t("Jour")}</th><th>{t("Demande")}</th><th>{t("Avant")}</th><th>{t("Justification")}</th><th>{t("État")}</th><th></th></tr></thead>
        <tbody>{data?.results.map((c) => (
          <tr key={c.id}><td>{dateFr(c.work_date)}<div className="small muted">{t("Employé")} #{c.employee}</div></td>
            <td>{c.kind === "add_punch" ? t("Ajouter un pointage à {time}", { time: dateTime(c.new_timestamp).slice(-5) }) : t("Statut → {s}", { s: c.new_status })}</td>
            <td className="small">{String(c.initial.status)} · {(c.initial.punch_times as string[] | undefined)?.map((p) => p.slice(11, 16)).join(", ") || t("aucun pointage")}</td>
            <td>{c.reason}{c.review_note && <div className="small muted">{t("Note :")} {c.review_note}</div>}<div className="small muted">{dateTime(c.created_at)}</div></td>
            <td><Pill tone={tone[c.state]} icon={icon[c.state]}>{t(label[c.state])}</Pill></td>
            <td>{c.state === "pending" && canReview && <div className="row"><button className="sm" onClick={() => act(c.id, "validate")}><Icon name="check" />{t("Valider")}</button><button className="sm ghost" onClick={() => act(c.id, "reject")}><Icon name="close" />{t("Rejeter")}</button></div>}</td></tr>))}
          {data && !data.results.length && <tr><td colSpan={6} className="muted">{t("Aucune correction.")}</td></tr>}</tbody></table></div>
      {!canReview && <p className="muted small">{t("La validation est réservée au responsable RH ; l'auteur d'une correction ne peut pas la valider lui-même.")}</p>}
    </>
  );
}
