import { useRef, useState } from "react";
import * as api from "../api";
import { t, tk } from "../i18n";
import { ErrorBanner, Field, Icon, Pager, Pill, useLoad } from "../ui";

const STATUS = { active: [tk("Actif"), "ok"], suspended: [tk("Suspendu"), "warn"], left: [tk("Sorti"), ""] } as const;

export default function Employees({ canWrite }: { canWrite: boolean }) {
  const [search, setSearch] = useState(""), [status, setStatus] = useState(""), [page, setPage] = useState(1);
  const { data, error, reload } = useLoad(() => api.list<api.Employee>("/employees/", { search, status, page }), [search, status, page]);
  const [msg, setMsg] = useState(""), [report, setReport] = useState<{ created: number; updated: number; errors: { row: number; error: string }[]; dry_run: boolean } | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const doImport = async (dry: boolean) => {
    const f = file.current?.files?.[0];
    if (!f) return setMsg(t("Choisissez un fichier CSV ou XLSX."));
    try { setReport(await api.upload(`/employees/import/${dry ? "?dry_run=1" : ""}`, f)); setMsg(""); if (!dry) reload(); } catch (e) { setMsg((e as Error).message); }
  };
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Ressources humaines")}</div><h1>{t("Personnel")}</h1></div>
        {canWrite && <div className="row"><button className="ghost" onClick={() => api.download("/employees/export/", "personnel.csv")}><Icon name="download" />{t("Exporter CSV")}</button>
          <button className="ghost" onClick={() => api.download("/employees/export/?fmt=xlsx", "personnel.xlsx")}><Icon name="table_view" />{t("Exporter Excel")}</button></div>}</div>
      {canWrite && <div className="card pad-b">
        <h2><Icon name="upload_file" className="muted" />{t("Importer (CSV ou Excel)")}</h2>
        <p className="muted small">{t("Colonnes : matricule, nom, prenom, unite (« Direction > Service »), fonction, date_recrutement, statut, pointeuse, id_pointeuse. L'identifiant de pointeuse n'est jamais supposé égal au matricule.")}</p>
        <div className="row"><input type="file" accept=".csv,.xlsx" ref={file} /><button className="ghost" onClick={() => doImport(true)}>{t("Simuler")}</button><button onClick={() => doImport(false)}><Icon name="upload_file" />{t("Importer")}</button></div>
        {report && <div style={{ marginTop: 8 }}><Pill tone={report.errors.length ? "warn" : "ok"}>{report.dry_run ? t("Simulation : ") : ""}{t("{c} créé(s), {u} mis à jour, {e} erreur(s)", { c: report.created, u: report.updated, e: report.errors.length })}</Pill>
          {report.errors.map((x) => <div key={x.row} className="small err">{t("Ligne {row} : {error}", { row: x.row, error: x.error })}</div>)}</div>}</div>}
      <div className="filters"><Field label={t("Recherche")}><input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder={t("Nom, matricule, fonction")} /></Field>
        <Field label={t("Statut")}><select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">{t("Tous")}</option><option value="active">{t("Actif")}</option><option value="suspended">{t("Suspendu")}</option><option value="left">{t("Sorti")}</option></select></Field></div>
      <ErrorBanner error={error || msg} />
      <div className="table-wrap"><table><thead><tr><th>{t("Matricule")}</th><th>{t("Nom")}</th><th>{t("Unité")}</th><th>{t("Fonction")}</th><th>{t("Recrutement")}</th><th>{t("Statut")}</th></tr></thead>
        <tbody>{data?.results.map((e) => (<tr key={e.id}><td className="mono">{e.matricule}</td><td><b>{e.last_name}</b> {e.first_name}</td><td>{e.org_unit_name ?? "—"}</td><td>{e.job_title || "—"}</td>
          <td>{e.hire_date ?? "—"}</td><td><Pill tone={STATUS[e.status as keyof typeof STATUS]?.[1]}>{t(STATUS[e.status as keyof typeof STATUS]?.[0] ?? e.status)}</Pill></td></tr>))}
          {data && !data.results.length && <tr><td colSpan={6} className="muted">{t("Aucun employé.")}</td></tr>}</tbody></table>
        {data && <Pager page={page} count={data.count} size={50} onPage={setPage} />}</div>
    </>
  );
}
