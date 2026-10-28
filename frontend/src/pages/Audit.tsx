import { useState } from "react";
import * as api from "../api";
import { dateTime, ErrorBanner, Pager, useLoad } from "../ui";

interface Row { id: number; created_at: string; user: number | null; action: string; object_type: string; object_id: string; detail: unknown; ip: string | null }

export default function Audit() {
  const [page, setPage] = useState(1), [action, setAction] = useState("");
  const { data, error } = useLoad(() => api.list<Row>("/audit-logs/", { page, action }), [page, action]);
  return (
    <>
      <div className="head"><div><div className="eyebrow">Traçabilité</div><h1>Journaux d'audit</h1></div>
        <input placeholder="Action (ex: login_failed)" value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} /></div>
      <ErrorBanner error={error} />
      <div className="table-wrap"><table><thead><tr><th>Date</th><th>Utilisateur</th><th>Action</th><th>Objet</th><th>Détail</th><th>IP</th></tr></thead>
        <tbody>{data?.results.map((r) => (<tr key={r.id}><td>{dateTime(r.created_at)}</td><td>{r.user ?? "—"}</td><td><b>{r.action}</b></td><td>{r.object_type} {r.object_id}</td>
          <td className="small">{r.detail ? JSON.stringify(r.detail) : ""}</td><td>{r.ip}</td></tr>))}</tbody></table>
        {data && <Pager page={page} count={data.count} size={50} onPage={setPage} />}</div>
    </>
  );
}
