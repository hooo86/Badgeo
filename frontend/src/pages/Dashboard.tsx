import * as api from "../api";
import { t, tk } from "../i18n";
import { dateLong, ErrorBanner, Icon, Pill, time, useLoad } from "../ui";

function Area({ data }: { data: api.Dashboard["arrivals"] }) {
  if (data.length < 2) return <p className="muted">{t("Pas encore d'arrivées enregistrées aujourd'hui.")}</p>;
  const W = 640, H = 180, max = Math.max(...data.map((d) => d.count), 1);
  const pts = data.map((d, i) => [(i / (data.length - 1)) * W, H - 24 - (d.count / max) * (H - 44)] as const);
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const peak = data.reduce((a, b) => (b.count > a.count ? b : a));
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("Courbe d'affluence des arrivées")}>
      <defs><linearGradient id="ar" x1="0" x2="0" y1="0" y2="1"><stop offset="0" style={{ stopColor: "var(--chart-fill)", stopOpacity: 0.3 }} /><stop offset="1" style={{ stopColor: "var(--chart-fill)", stopOpacity: 0 }} /></linearGradient></defs>
      <path d={`${line} L${W},${H - 24} L0,${H - 24} Z`} fill="url(#ar)" /><path d={line} fill="none" strokeWidth="2.5" style={{ stroke: "var(--chart-line)" }} />
      {data.map((d, i) => (i % Math.ceil(data.length / 8) === 0 ? <text key={d.slot} x={pts[i][0]} y={H - 6} fontSize="11" textAnchor={i === 0 ? "start" : i >= data.length - 2 ? "end" : "middle"}>{d.slot}</text> : null))}
      <text x={W} y="12" fontSize="11" textAnchor="end" fontWeight="700" style={{ fill: "var(--accent)" }}>{t("Pic : {slot} ({n})", { slot: peak.slot, n: peak.count })}</text>
    </svg>
  );
}

function Bars({ data }: { data: api.Dashboard["daily"] }) {
  const max = Math.max(...data.map((d) => d.expected), 1), W = 640, H = 150, bw = W / Math.max(data.length, 1);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("Présents par jour")}>
      {data.map((d, i) => {
        const hp = (d.present / max) * (H - 30), he = (d.expected / max) * (H - 30);
        return (
          <g key={d.date}>
            <rect x={i * bw + 4} y={H - 20 - he} width={bw - 8} height={he} rx="4" style={{ fill: "var(--chart-bar-bg)" }} />
            <rect x={i * bw + 4} y={H - 20 - hp} width={bw - 8} height={hp} rx="4" style={{ fill: "var(--chart-bar)" }} />
            <text x={i * bw + bw / 2} y={H - 6} fontSize="10" textAnchor="middle">{d.date.slice(8)}</text>
          </g>
        );
      })}
    </svg>
  );
}

export default function Dashboard() {
  const { data: d, error } = useLoad(api.dashboard, [], 30000);
  if (!d) return <><h1>{t("Tableau de bord")}</h1><ErrorBanner error={error} /><p className="muted">{t("Chargement…")}</p></>;
  const kpi = (icon: string, label: string, value: string | number, sub?: string, bad = false) => (
    <div className={`card kpi${bad ? " alert" : ""}`}>
      <div className="top"><span className="label">{t(label)}</span><span className="chip"><Icon name={icon} /></span></div>
      <div className="value mono">{value}</div>{sub && <div className={`small ${bad ? "err" : "muted"}`}>{sub}</div>}
    </div>
  );
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Supervision RH")}</div><h1>{t("Pointages en direct")}</h1></div>
        <span className="muted small row"><Icon name="sync" />{t("Données du {date} · actualisé toutes les 30 s", { date: dateLong(d.date) })}</span></div>
      <ErrorBanner error={error} />
      <div className="grid kpis">
        {kpi("groups", tk("Effectif actif"), d.headcount, d.presence_rate != null ? t("Taux de présence {n}%", { n: d.presence_rate }) : t("Aucun horaire aujourd'hui"))}
        {kpi("domain", tk("Présents aujourd'hui"), d.present, t("{n} en retard", { n: d.late }))}
        {kpi("beach_access", tk("Absents / congés"), d.absent, t("{n} absences justifiées", { n: d.on_leave }))}
        {kpi("fmd_bad", tk("Pointages incomplets"), d.incomplete, t("{n} anomalie(s) à traiter", { n: d.anomalies_to_review }), d.anomalies_to_review > 0)}
        {kpi("touch_app", tk("Pointages reçus"), d.punches_today, d.unmapped_punches_today ? t("{n} non rattaché(s)", { n: d.unmapped_punches_today }) : undefined, !!d.unmapped_punches_today)}
        {d.devices && kpi("podcasts", tk("Pointeuses"), `${d.devices.connected} / ${d.devices.connected + d.devices.disconnected}`, d.devices.last_sync_at ? t("Synchro {time}", { time: time(d.devices.last_sync_at) }) : t("Jamais synchronisé"), d.devices.disconnected > 0)}
        {kpi("rule", tk("Corrections en attente"), d.corrections_pending)}
      </div>
      <div className="grid two" style={{ marginTop: 16 }}>
        <div className="card"><h2><Icon name="monitoring" className="muted" />{t("Courbe d'affluence des arrivées")}</h2><Area data={d.arrivals} /></div>
        <div className="card"><h2><Icon name="business" className="muted" />{t("Présence par direction")}</h2>
          {d.by_unit.length === 0 && <p className="muted">{t("Aucune donnée.")}</p>}
          {d.by_unit.map((u) => (
            <div key={u.unit} style={{ marginBottom: 10 }}><div className="row"><b>{u.unit}</b><span className="end small mono">{u.present}/{u.expected} · {u.rate ?? "—"}%</span></div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${u.rate ?? 0}%` }} /></div></div>))}
        </div>
      </div>
      <div className="grid two" style={{ marginTop: 16 }}>
        <div className="card"><h2><Icon name="trending_up" className="muted" />{t("14 derniers jours : présents / attendus")}</h2><Bars data={d.daily} /></div>
        <div className="card"><h2><Icon name="touch_app" className="muted" />{t("Derniers badgeages")}</h2>
          {d.recent.length === 0 && <p className="muted">{t("Aucun pointage.")}</p>}
          {d.recent.map((r, i) => (
            <div key={i} className="row" style={{ padding: "6px 0", borderTop: i ? "1px solid var(--outline-variant)" : 0 }}>
              <div><b>{r.employee}</b><div className="small muted"><bdi dir="ltr">#{r.matricule}</bdi> · {r.device ?? r.source}</div></div>
              <span className="end"><Pill tone="info" icon="login">{time(r.time)}</Pill></span></div>))}
        </div>
      </div>
    </>
  );
}
