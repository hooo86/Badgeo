import { FormEvent, useRef, useState } from "react";
import * as api from "../api";
import { dateTime, ErrorBanner, Field, Pill, useLoad } from "../ui";

const TYPE: Record<string, string> = { manual: "Manuelle", auto: "Automatique", pre_restore: "Avant restauration", imported: "Importée" };
const mo = (n: number) => (n > 1e6 ? `${(n / 1e6).toFixed(1)} Mo` : `${Math.max(1, Math.round(n / 1e3))} Ko`);

export default function Backups() {
  const { data, error, reload } = useLoad(() => api.get<api.BackupState>("/backups/"), [], 20000);
  const [msg, setMsg] = useState(""), [info, setInfo] = useState(""), [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setMsg(""); setInfo("");
    try { await fn(); setInfo(ok); reload(); } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  };
  const restore = async (b: api.BackupItem) => {
    const t = prompt(`Restaurer « ${b.nom} » ?\\n\\nToutes les données actuelles seront REMPLACÉES (une sauvegarde de sécurité est faite d'abord ; la licence est conservée).\\nVous devrez vous reconnecter.\\n\\nTapez RESTAURER pour confirmer :`);
    if (t === null) return;
    setBusy(true); setMsg("");
    try {
      await api.post(`/backups/${b.nom}/restore/`, { confirmation: t, ...(b.chiffree && !data?.chiffrement ? { phrase_de_passe: prompt("Phrase de passe de cette sauvegarde :") ?? "" } : {}) });
      api.setToken(null); alert("Restauration terminée. Reconnectez-vous."); location.reload();
    } catch (e) { setMsg((e as Error).message); setBusy(false); }
  };
  const saveCfg = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    run(() => api.put("/backups/settings/", { auto: f.get("auto") === "on", hour: Number(f.get("hour")), keep: Number(f.get("keep")), copy_dir: String(f.get("copy_dir") ?? "") }), "Réglages enregistrés.");
  };
  const cfg = data?.reglages;
  return (
    <>
      <div className="head"><div><div className="eyebrow">Données</div><h1>Sauvegardes</h1></div>
        <button disabled={busy} onClick={() => run(() => api.post("/backups/"), "Sauvegarde créée.")}>Sauvegarder maintenant</button></div>
      <ErrorBanner error={error || msg} />{info && <div className="banner">{info}</div>}
      {data && <div className="grid two" style={{ marginBottom: 16 }}>
        <form className="card" onSubmit={saveCfg} key={JSON.stringify(cfg)} style={{ display: "grid", gap: 10 }}>
          <h2>Sauvegarde automatique</h2>
          <label className="row"><input type="checkbox" name="auto" defaultChecked={cfg!.auto} /> Activer (une par jour)</label>
          <div className="row"><Field label="Heure (0–23)"><input type="number" name="hour" min={0} max={23} defaultValue={cfg!.hour} style={{ width: 90 }} /></Field>
            <Field label="Nombre à conserver"><input type="number" name="keep" min={1} max={365} defaultValue={cfg!.keep} style={{ width: 110 }} /></Field></div>
          <Field label="Copie vers un autre disque / dossier réseau (facultatif)"><input name="copy_dir" defaultValue={cfg!.copy_dir} placeholder="ex. E:\Sauvegardes-Badgeo" /></Field>
          <div className="row"><button disabled={busy}>Enregistrer</button></div></form>
        <div className="card"><h2>Protection</h2>
          <p><Pill tone={data.chiffrement ? "ok" : "warn"}>{data.chiffrement ? "Chiffrées (AES)" : "Non chiffrées"}</Pill></p>
          <p className="muted small">{data.chiffrement ? "Les fichiers sont chiffrés avec la phrase de passe BADGEO_BACKUP_PASSPHRASE : sans elle, ils sont illisibles. Conservez-la à part." : "Définissez BADGEO_BACKUP_PASSPHRASE pour chiffrer les sauvegardes (elles contiennent des données personnelles)."}</p>
          <p className="muted small">Dossier : <code>{data.dossier}</code></p>
          <p className="muted small">Les sauvegardes contiennent les données, pas la mémoire des pointeuses (jamais effacée). Pensez à en copier régulièrement hors de ce poste.</p></div></div>}
      <div className="card" style={{ marginBottom: 16 }}><h2>Importer un fichier .badgeo</h2>
        <div className="row"><input type="file" ref={file} accept=".badgeo" />
          <button className="ghost" disabled={busy} onClick={() => { const f = file.current?.files?.[0]; if (!f) return setMsg("Choisissez un fichier."); run(() => api.upload("/backups/upload/", f), "Fichier importé : il apparaît dans la liste (aucune donnée modifiée)."); }}>Importer</button></div></div>
      <div className="table-wrap"><table><thead><tr><th>Date</th><th>Type</th><th>Par</th><th>Taille</th><th>Lignes</th><th>Protection</th><th></th></tr></thead>
        <tbody>{data?.sauvegardes.map((b) => (
          <tr key={b.nom}><td>{dateTime(b.creee_le)}<div className="small muted">{b.nom}</div>{b.copie && <div className={`small ${b.copie.startsWith("ÉCHEC") ? "err" : "muted"}`}>Copie : {b.copie}</div>}</td>
            <td><Pill tone={b.type === "auto" ? "info" : ""}>{TYPE[b.type] ?? b.type}</Pill></td><td>{b.par || "—"}</td><td>{mo(b.taille)}</td><td>{b.lignes ?? "—"}</td>
            <td>{b.chiffree ? <Pill tone="ok">Chiffrée</Pill> : <Pill tone="warn">Non chiffrée</Pill>}</td>
            <td><div className="row"><button className="sm ghost" onClick={() => api.download(`/backups/${b.nom}/`, b.nom)}>Télécharger</button>
              <button className="sm" disabled={busy} onClick={() => restore(b)}>Restaurer</button>
              <button className="sm danger" disabled={busy} onClick={() => confirm(`Supprimer ${b.nom} ?`) && run(() => api.remove(`/backups/${b.nom}/`), "Sauvegarde supprimée.")}>Supprimer</button></div></td></tr>))}
          {data && !data.sauvegardes.length && <tr><td colSpan={7} className="muted">Aucune sauvegarde.</td></tr>}</tbody></table></div>
    </>
  );
}
