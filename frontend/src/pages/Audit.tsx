import { useState } from "react";
import * as api from "../api";
import { t } from "../i18n";
import { dateTime, ErrorBanner, Icon, Pager, useLoad } from "../ui";

interface Row { id: number; created_at: string; user: number | null; action: string; object_type: string; object_id: string; detail: unknown; ip: string | null }

export default function Audit() {
  const [page, setPage] = useState(1), [action, setAction] = useState("");
  const { data, error } = useLoad(() => api.list<Row>("/audit-logs/", { page, action }), [page, action]);
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Traçabilité")}</div><h1>{t("Journaux d'audit")}</h1></div>
        <label className="row"><Icon name="filter_list" className="muted" /><input placeholder={t("Action (ex: login_failed)")} value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} dir="ltr" /></label></div>
      <ErrorBanner error={error} />
      <div className="table-wrap"><table><thead><tr><th>{t("Date")}</th><th>{t("Utilisateur")}</th><th>{t("Action")}</th><th>{t("Objet")}</th><th>{t("Détail")}</th><th>IP</th></tr></thead>
        <tbody>{data?.results.map((r) => (<tr key={r.id}><td>{dateTime(r.created_at)}</td><td>{r.user ?? "—"}</td><td><b>{r.action}</b></td><td dir="ltr">{r.object_type} {r.object_id}</td>
          <td className="small mono" dir="ltr">{r.detail ? JSON.stringify(r.detail) : ""}</td><td className="mono">{r.ip}</td></tr>))}</tbody></table>
        {data && <Pager page={page} count={data.count} size={50} onPage={setPage} />}</div>
    </>
  );
}
