import { useState } from "react";
import * as api from "../api";
import { ErrorBanner, Field, monthStart, today } from "../ui";

const REPORTS: [string, string, string][] = [
  ["daily", "État journalier des présences", "Une ligne par employé et par jour"], ["monthly", "État mensuel des présences", "Totaux par employé sur la période"],
  ["late", "Retards cumulés", "Journées avec retard"], ["absences", "Absences et absences justifiées", "Absences, congés, missions, arrêts"],
  ["early-leave", "Départs anticipés", "Sorties avant l'heure prévue"], ["hours", "Heures de présence", "Présence et travail estimé"],
  ["overtime", "Heures supplémentaires potentielles", "À valider avant paie"], ["raw-punches", "Pointages bruts par appareil", "Données d'audit non modifiées"],
  ["anomalies", "Anomalies en attente", "Incomplets, doublons, sans pointage"], ["corrections", "Historique des corrections", "Valeur, auteur, motif, validation"],
  ["devices", "État des pointeuses", "Connexion, dernière synchro, erreurs"],
];

export default function Reports() {
  const [from, setFrom] = useState(monthStart()), [to, setTo] = useState(today()), [matricule, setMatricule] = useState("");
  const [err, setErr] = useState("");
  const go = (name: string, fmt: string) => api.download(`/reports/${name}/${api.qs({ from, to, matricule, fmt })}`, `badgeo-${name}.${fmt}`).then(() => setErr("")).catch((e) => setErr(e.message));
  return (
    <>
      <div className="head"><div><div className="eyebrow">Exports</div><h1>Rapports</h1></div></div>
      <div className="filters"><Field label="Du"><input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
        <Field label="Au"><input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></Field>
        <Field label="Matricule"><input value={matricule} onChange={(e) => setMatricule(e.target.value)} /></Field></div>
      <ErrorBanner error={err} />
      <div className="grid kpis">{REPORTS.map(([k, t, d]) => (
        <div className="card" key={k}><h2>{t}</h2><p className="muted small">{d}</p>
          <div className="row">{["xlsx", "csv", "pdf"].map((f) => <button key={f} className="ghost sm" onClick={() => go(k, f)}>{f.toUpperCase()}</button>)}</div></div>))}</div>
    </>
  );
}
