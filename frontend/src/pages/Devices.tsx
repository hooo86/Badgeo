import { FormEvent, useState } from "react";
import * as api from "../api";
import { dateTime, ErrorBanner, Field, Pill, useLoad } from "../ui";

const TONE = { unknown: "", connected: "ok", disconnected: "warn", error: "bad" } as const;
const LABEL = { unknown: "Inconnu", connected: "Connecté", disconnected: "Déconnecté", error: "Erreur" } as const;

export default function Devices({ canWrite }: { canWrite: boolean }) {
  const { data, error, reload } = useLoad(() => api.list<api.Device>("/devices/"), [], 15000);
  const [diag, setDiag] = useState<Record<number, api.Diagnostic>>({});
  const [msg, setMsg] = useState("");
  const run = (p: Promise<unknown>, ok = "") => p.then(() => { setMsg(ok); reload(); }).catch((e) => setMsg(e.message));

  const add = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget), form = e.currentTarget;
    await run(api.create("/devices/", {
      name: f.get("name"), vendor: f.get("vendor"), model: f.get("model"), ip_address: f.get("ip"), port: Number(f.get("port")),
      ...(f.get("key") ? { comm_key: Number(f.get("key")) } : {}),
    }).then(() => form.reset()));
  };
  return (
    <>
      <div className="head"><div><div className="eyebrow">Terminaux</div><h1>Pointeuses</h1></div></div>
      <div className="banner">Une connexion n'est considérée fonctionnelle qu'après un test réussi sur l'appareil réel (bouton « Tester »).</div>
      {canWrite && <form className="card filters" onSubmit={add}>
        <Field label="Nom"><input name="name" required /></Field>
        <Field label="Fabricant"><select name="vendor"><option value="zkteco">ZKTeco</option><option value="unis">UNIS</option></select></Field>
        <Field label="Modèle exact"><input name="model" /></Field>
        <Field label="Adresse IP"><input name="ip" required /></Field>
        <Field label="Port"><input name="port" type="number" defaultValue={4370} required style={{ width: 90 }} /></Field>
        <Field label="Clé de communication"><input name="key" type="number" min={0} style={{ width: 150 }} /></Field>
        <button>Ajouter</button></form>}
      <ErrorBanner error={error || msg} />
      <div className="table-wrap"><table><thead><tr><th>Appareil</th><th>Adresse</th><th>État</th><th>Dernier contact</th><th>Dernière synchro</th><th>Événements</th><th></th></tr></thead>
        <tbody>{data?.results.map((d) => { const g = diag[d.id]; return (
          <tr key={d.id}><td><b>{d.name}</b><div className="small muted">{d.vendor.toUpperCase()} {d.model}{d.serial_number && ` · S/N ${d.serial_number}`}</div></td>
            <td>{d.ip_address}:{d.port}</td>
            <td><Pill tone={TONE[d.status]}>{LABEL[d.status]}</Pill>{d.last_error && <div className="small err">{d.last_error}</div>}
              {g && <div className="small">Réseau : {g.tcp_reachable ? "joignable" : "injoignable"} · Protocole : {g.handshake ? "ok" : `échec (${g.stage ?? "?"})`}{g.message && <div className="err">{g.message}</div>}</div>}</td>
            <td>{dateTime(d.last_seen_at)}</td><td>{dateTime(d.last_sync_at)}{d.last_sync_ok === false && <div className="small err">dernière synchro en échec</div>}</td><td>{d.events_total}</td>
            <td><div className="row">{canWrite && <>
              <button className="sm" onClick={() => api.testDevice(d.id).then((r) => { setDiag({ ...diag, [d.id]: r }); reload(); }).catch((e) => setMsg(e.message))}>Tester</button>
              <button className="sm ghost" onClick={() => run(api.post(`/devices/${d.id}/sync/`), "Synchronisation en file d'attente")}>Synchroniser</button>
              <button className="sm danger" onClick={() => confirm(`Supprimer ${d.name} ?`) && run(api.remove(`/devices/${d.id}/`))}>Supprimer</button></>}</div></td></tr>); })}
          {data && !data.results.length && <tr><td colSpan={7} className="muted">Aucune pointeuse enregistrée.</td></tr>}</tbody></table></div>
    </>
  );
}
