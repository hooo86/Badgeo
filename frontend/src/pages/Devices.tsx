import { FormEvent, useState } from "react";
import * as api from "../api";
import { t, tk } from "../i18n";
import { dateTime, ErrorBanner, Field, Icon, Pill, useLoad } from "../ui";

const TONE = { unknown: "", connected: "ok", disconnected: "warn", error: "bad" } as const;
const LABEL = { unknown: tk("Inconnu"), connected: tk("Connecté"), disconnected: tk("Déconnecté"), error: tk("Erreur") } as const;
const ICON = { unknown: "help", connected: "podcasts", disconnected: "sync_problem", error: "error" } as const;

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
      <div className="head"><div><div className="eyebrow">{t("Terminaux")}</div><h1>{t("Pointeuses")}</h1></div></div>
      <div className="banner"><Icon name="info" />{t("Une connexion n'est considérée fonctionnelle qu'après un test réussi sur l'appareil réel (bouton « Tester »).")}</div>
      {canWrite && <form className="card filters pad-b" onSubmit={add}>
        <Field label={t("Nom")}><input name="name" required /></Field>
        <Field label={t("Fabricant")}><select name="vendor"><option value="zkteco">ZKTeco</option><option value="unis">UNIS</option></select></Field>
        <Field label={t("Modèle exact")}><input name="model" /></Field>
        <Field label={t("Adresse IP")}><input name="ip" required dir="ltr" /></Field>
        <Field label={t("Port")}><input name="port" type="number" defaultValue={4370} required style={{ width: 90 }} /></Field>
        <Field label={t("Clé de communication")}><input name="key" type="number" min={0} style={{ width: 150 }} /></Field>
        <button><Icon name="add" />{t("Ajouter")}</button></form>}
      <ErrorBanner error={error || msg} />
      <div className="table-wrap"><table><thead><tr><th>{t("Appareil")}</th><th>{t("Adresse")}</th><th>{t("État")}</th><th>{t("Dernier contact")}</th><th>{t("Dernière synchro")}</th><th>{t("Événements")}</th><th></th></tr></thead>
        <tbody>{data?.results.map((d) => { const g = diag[d.id]; return (
          <tr key={d.id}><td><b>{d.name}</b><div className="small muted">{d.vendor.toUpperCase()} {d.model}{d.serial_number && ` · S/N ${d.serial_number}`}</div></td>
            <td className="mono" dir="ltr">{d.ip_address}:{d.port}</td>
            <td><Pill tone={TONE[d.status]} icon={ICON[d.status]}>{t(LABEL[d.status])}</Pill>{d.last_error && <div className="small err">{d.last_error}</div>}
              {g && <div className="small">{t("Réseau :")} {g.tcp_reachable ? t("joignable") : t("injoignable")} · {t("Protocole :")} {g.handshake ? t("ok") : t("échec ({stage})", { stage: g.stage ?? "?" })}{g.message && <div className="err">{g.message}</div>}</div>}</td>
            <td>{dateTime(d.last_seen_at)}</td><td>{dateTime(d.last_sync_at)}{d.last_sync_ok === false && <div className="small err">{t("dernière synchro en échec")}</div>}</td><td className="mono">{d.events_total}</td>
            <td><div className="row">{canWrite && <>
              <button className="sm" onClick={() => api.testDevice(d.id).then((r) => { setDiag({ ...diag, [d.id]: r }); reload(); }).catch((e) => setMsg(e.message))}><Icon name="network_check" />{t("Tester")}</button>
              <button className="sm ghost" onClick={() => run(api.post(`/devices/${d.id}/sync/`), t("Synchronisation en file d'attente"))}><Icon name="sync" />{t("Synchroniser")}</button>
              <button className="sm danger" onClick={() => confirm(t("Supprimer {name} ?", { name: d.name })) && run(api.remove(`/devices/${d.id}/`))}><Icon name="delete" />{t("Supprimer")}</button></>}</div></td></tr>); })}
          {data && !data.results.length && <tr><td colSpan={7} className="muted">{t("Aucune pointeuse enregistrée.")}</td></tr>}</tbody></table></div>
    </>
  );
}
