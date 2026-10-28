import { useState } from "react";
import * as api from "../api";
import { t, tk } from "../i18n";
import { ErrorBanner, Field, Icon, monthStart, today } from "../ui";

const REPORTS: [string, string, string, string][] = [
  ["daily", tk("État journalier des présences"), tk("Une ligne par employé et par jour"), "today"], ["monthly", tk("État mensuel des présences"), tk("Totaux par employé sur la période"), "calendar_month"],
  ["late", tk("Retards cumulés"), tk("Journées avec retard"), "more_time"], ["absences", tk("Absences et absences justifiées"), tk("Absences, congés, missions, arrêts"), "beach_access"],
  ["early-leave", tk("Départs anticipés"), tk("Sorties avant l'heure prévue"), "logout"], ["hours", tk("Heures de présence"), tk("Présence et travail estimé"), "timelapse"],
  ["overtime", tk("Heures supplémentaires potentielles"), tk("À valider avant paie"), "payments"], ["raw-punches", tk("Pointages bruts par appareil"), tk("Données d'audit non modifiées"), "fingerprint"],
  ["anomalies", tk("Anomalies en attente"), tk("Incomplets, doublons, sans pointage"), "fmd_bad"], ["corrections", tk("Historique des corrections"), tk("Valeur, auteur, motif, validation"), "rule"],
  ["devices", tk("État des pointeuses"), tk("Connexion, dernière synchro, erreurs"), "podcasts"],
];

export default function Reports() {
  const [from, setFrom] = useState(monthStart()), [to, setTo] = useState(today()), [matricule, setMatricule] = useState("");
  const [err, setErr] = useState("");
  const go = (name: string, fmt: string) => api.download(`/reports/${name}/${api.qs({ from, to, matricule, fmt })}`, `badgeo-${name}.${fmt}`).then(() => setErr("")).catch((e) => setErr(e.message));
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Exports")}</div><h1>{t("Rapports")}</h1></div></div>
      <div className="filters"><Field label={t("Du")}><input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
        <Field label={t("Au")}><input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></Field>
        <Field label={t("Matricule")}><input value={matricule} onChange={(e) => setMatricule(e.target.value)} /></Field></div>
      <ErrorBanner error={err} />
      <p className="muted small">{t("Les fichiers exportés (Excel, CSV, PDF) sont rédigés en français.")}</p>
      <div className="grid kpis">{REPORTS.map(([k, title, d, icon]) => (
        <div className="card" key={k}><h2><Icon name={icon} className="muted" />{t(title)}</h2><p className="muted small">{t(d)}</p>
          <div className="row">{["xlsx", "csv", "pdf"].map((f) => <button key={f} className="ghost sm" onClick={() => go(k, f)}><Icon name="download" />{f.toUpperCase()}</button>)}</div></div>))}</div>
    </>
  );
}
