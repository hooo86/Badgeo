import { useRef, useState } from "react";
import * as api from "../api";
import { ErrorBanner, Field, Pager, Pill, useLoad } from "../ui";

const STATUS = { active: ["Actif", "ok"], suspended: ["Suspendu", "warn"], left: ["Sorti", ""] } as const;

export default function Employees({ canWrite }: { canWrite: boolean }) {
  const [search, setSearch] = useState(""), [status, setStatus] = useState(""), [page, setPage] = useState(1);
  const { data, error, reload } = useLoad(() => api.list<api.Employee>("/employees/", { search, status, page }), [search, status, page]);
  const [msg, setMsg] = useState(""), [report, setReport] = useState<{ created: number; updated: number; errors: { row: number; error: string }[]; dry_run: boolean } | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const doImport = async (dry: boolean) => {
    const f = file.current?.files?.[0];
    if (!f) return setMsg("Choisissez un fichier CSV ou XLSX.");
    try { setReport(await api.upload(`/employees/import/${dry ? "?dry_run=1" : ""}`, f)); setMsg(""); if (!dry) reload(); } catch (e) { setMsg((e as Error).message); }
  };
  return (
    <>
      <div className="head"><div><div className="eyebrow">Ressources humaines</div><h1>Personnel</h1></div>
        {canWrite && <div className="row"><button className="ghost" onClick={() => api.download("/employees/export/", "personnel.csv")}>Exporter CSV</button>
          <button className="ghost" onClick={() => api.download("/employees/export/?fmt=xlsx", "personnel.xlsx")}>Exporter Excel</button></div>}</div>
      {canWrite && <div className="card" style={{ marginBottom: 12 }}>
        <h2>Importer (CSV ou Excel)</h2>
        <p className="muted small">Colonnes : matricule, nom, prenom, unite (« Direction &gt; Service »), fonction, date_recrutement, statut, pointeuse, id_pointeuse. L'identifiant de pointeuse n'est jamais supposé égal au matricule.</p>
        <div className="row"><input type="file" accept=".csv,.xlsx" ref={file} /><button className="ghost" onClick={() => doImport(true)}>Simuler</button><button onClick={() => doImport(false)}>Importer</button></div>
        {report && <div style={{ marginTop: 8 }}><Pill tone={report.errors.length ? "warn" : "ok"}>{report.dry_run ? "Simulation : " : ""}{report.created} créé(s), {report.updated} mis à jour, {report.errors.length} erreur(s)</Pill>
          {report.errors.map((x) => <div key={x.row} className="small err">Ligne {x.row} : {x.error}</div>)}</div>}</div>}
      <div className="filters"><Field label="Recherche"><input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Nom, matricule, fonction" /></Field>
        <Field label="Statut"><select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">Tous</option><option value="active">Actif</option><option value="suspended">Suspendu</option><option value="left">Sorti</option></select></Field></div>
      <ErrorBanner error={error || msg} />
      <div className="table-wrap"><table><thead><tr><th>Matricule</th><th>Nom</th><th>Unité</th><th>Fonction</th><th>Recrutement</th><th>Statut</th></tr></thead>
        <tbody>{data?.results.map((e) => (<tr key={e.id}><td>{e.matricule}</td><td><b>{e.last_name}</b> {e.first_name}</td><td>{e.org_unit_name ?? "—"}</td><td>{e.job_title || "—"}</td>
          <td>{e.hire_date ?? "—"}</td><td><Pill tone={STATUS[e.status as keyof typeof STATUS]?.[1]}>{STATUS[e.status as keyof typeof STATUS]?.[0] ?? e.status}</Pill></td></tr>))}
          {data && !data.results.length && <tr><td colSpan={6} className="muted">Aucun employé.</td></tr>}</tbody></table>
        {data && <Pager page={page} count={data.count} size={50} onPage={setPage} />}</div>
    </>
  );
}
