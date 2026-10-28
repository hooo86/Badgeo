import * as api from "../api";
import { ErrorBanner, Pill, time, useLoad } from "../ui";

function Area({ data }: { data: api.Dashboard["arrivals"] }) {
  if (data.length < 2) return <p className="muted">Pas encore d'arrivées enregistrées aujourd'hui.</p>;
  const W = 640, H = 180, max = Math.max(...data.map((d) => d.count), 1);
  const pts = data.map((d, i) => [(i / (data.length - 1)) * W, H - 24 - (d.count / max) * (H - 44)] as const);
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const peak = data.reduce((a, b) => (b.count > a.count ? b : a));
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Courbe d'affluence des arrivées">
      <defs><linearGradient id="ar" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#2563eb" stopOpacity=".3" /><stop offset="1" stopColor="#2563eb" stopOpacity="0" /></linearGradient></defs>
      <path d={`${line} L${W},${H - 24} L0,${H - 24} Z`} fill="url(#ar)" /><path d={line} fill="none" stroke="#2563eb" strokeWidth="2.5" />
      {data.map((d, i) => (i % Math.ceil(data.length / 8) === 0 ? <text key={d.slot} x={pts[i][0]} y={H - 6} fontSize="11" fill="#737686" textAnchor={i === 0 ? "start" : i >= data.length - 2 ? "end" : "middle"}>{d.slot}</text> : null))}
      <text x={W} y="12" fontSize="11" fill="#004ac6" textAnchor="end" fontWeight="700">Pic : {peak.slot} ({peak.count})</text>
    </svg>
  );
}

function Bars({ data }: { data: api.Dashboard["daily"] }) {
  const max = Math.max(...data.map((d) => d.expected), 1), W = 640, H = 150, bw = W / Math.max(data.length, 1);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Présents par jour">
      {data.map((d, i) => {
        const hp = (d.present / max) * (H - 30), he = (d.expected / max) * (H - 30);
        return (
          <g key={d.date}>
            <rect x={i * bw + 4} y={H - 20 - he} width={bw - 8} height={he} rx="4" fill="#e0e3e5" />
            <rect x={i * bw + 4} y={H - 20 - hp} width={bw - 8} height={hp} rx="4" fill="#2563eb" />
            <text x={i * bw + bw / 2} y={H - 6} fontSize="10" fill="#737686" textAnchor="middle">{d.date.slice(8)}</text>
          </g>
        );
      })}
    </svg>
  );
}

export default function Dashboard() {
  const { data: d, error } = useLoad(api.dashboard, [], 30000);
  if (!d) return <><h1>Tableau de bord</h1><ErrorBanner error={error} /><p className="muted">Chargement…</p></>;
  const kpi = (label: string, value: string | number, sub?: string, tone = "") => (
    <div className="card kpi"><div className="label">{label}</div><div className="value">{value}</div>{sub && <div className={`small ${tone}`}>{sub}</div>}</div>
  );
  return (
    <>
      <div className="head"><div><div className="eyebrow">Supervision RH</div><h1>Pointages en direct</h1></div>
        <span className="muted small">Données du {new Date(d.date).toLocaleDateString("fr-FR", { dateStyle: "full" })} · actualisé toutes les 30 s</span></div>
      <ErrorBanner error={error} />
      <div className="grid kpis">
        {kpi("Effectif actif", d.headcount, d.presence_rate != null ? `Taux de présence ${d.presence_rate}%` : "Aucun horaire aujourd'hui")}
        {kpi("Présents aujourd'hui", d.present, `${d.late} en retard`)}
        {kpi("Absents / congés", d.absent, `${d.on_leave} absences justifiées`)}
        {kpi("Pointages incomplets", d.incomplete, `${d.anomalies_to_review} anomalie(s) à traiter`, d.anomalies_to_review ? "err" : "")}
        {kpi("Pointages reçus", d.punches_today, d.unmapped_punches_today ? `${d.unmapped_punches_today} non rattaché(s)` : undefined, "err")}
        {d.devices && kpi("Pointeuses", `${d.devices.connected} / ${d.devices.connected + d.devices.disconnected}`, d.devices.last_sync_at ? `Synchro ${time(d.devices.last_sync_at)}` : "Jamais synchronisé", d.devices.disconnected ? "err" : "")}
        {kpi("Corrections en attente", d.corrections_pending)}
      </div>
      <div className="grid two" style={{ marginTop: 16 }}>
        <div className="card"><h2>Courbe d'affluence des arrivées</h2><Area data={d.arrivals} /></div>
        <div className="card"><h2>Présence par direction</h2>
          {d.by_unit.length === 0 && <p className="muted">Aucune donnée.</p>}
          {d.by_unit.map((u) => (
            <div key={u.unit} style={{ marginBottom: 10 }}><div className="row"><b>{u.unit}</b><span className="right small">{u.present}/{u.expected} · {u.rate ?? "—"}%</span></div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${u.rate ?? 0}%` }} /></div></div>))}
        </div>
      </div>
      <div className="grid two" style={{ marginTop: 16 }}>
        <div className="card"><h2>14 derniers jours : présents / attendus</h2><Bars data={d.daily} /></div>
        <div className="card"><h2>Derniers badgeages</h2>
          {d.recent.length === 0 && <p className="muted">Aucun pointage.</p>}
          {d.recent.map((r, i) => (
            <div key={i} className="row" style={{ padding: "6px 0", borderTop: i ? "1px solid var(--surface-container)" : 0 }}>
              <div><b>{r.employee}</b><div className="small muted">#{r.matricule} · {r.device ?? r.source}</div></div>
              <Pill tone="info">{time(r.time)}</Pill></div>))}
        </div>
      </div>
    </>
  );
}
