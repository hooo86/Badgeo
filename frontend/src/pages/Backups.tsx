import { FormEvent, useRef, useState } from "react";
import * as api from "../api";
import { t, tk } from "../i18n";
import { dateTime, ErrorBanner, Field, Icon, Pill, useLoad } from "../ui";

const TYPE: Record<string, string> = { manual: tk("Manuelle"), auto: tk("Automatique"), pre_restore: tk("Avant restauration"), imported: tk("Importée") };
const mo = (n: number) => (n > 1e6 ? `${(n / 1e6).toFixed(1)} ${t("Mo")}` : `${Math.max(1, Math.round(n / 1e3))} ${t("Ko")}`);

export default function Backups() {
  const { data, error, reload } = useLoad(() => api.get<api.BackupState>("/backups/"), [], 20000);
  const [msg, setMsg] = useState(""), [info, setInfo] = useState(""), [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setMsg(""); setInfo("");
    try { await fn(); setInfo(ok); reload(); } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  };
  const restore = async (b: api.BackupItem) => {
    const typed = prompt(t("Restaurer « {nom} » ?\n\nToutes les données actuelles seront REMPLACÉES (une sauvegarde de sécurité est faite d'abord ; la licence est conservée).\nVous devrez vous reconnecter.\n\nTapez RESTAURER pour confirmer :", { nom: b.nom }));
    if (typed === null) return;
    setBusy(true); setMsg("");
    try {
      await api.post(`/backups/${b.nom}/restore/`, { confirmation: typed, ...(b.chiffree && !data?.chiffrement ? { phrase_de_passe: prompt(t("Phrase de passe de cette sauvegarde :")) ?? "" } : {}) });
      api.setToken(null); alert(t("Restauration terminée. Reconnectez-vous.")); location.reload();
    } catch (e) { setMsg((e as Error).message); setBusy(false); }
  };
  const saveCfg = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    run(() => api.put("/backups/settings/", { auto: f.get("auto") === "on", hour: Number(f.get("hour")), keep: Number(f.get("keep")), copy_dir: String(f.get("copy_dir") ?? "") }), t("Réglages enregistrés."));
  };
  const cfg = data?.reglages;
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Données")}</div><h1>{t("Sauvegardes")}</h1></div>
        <button disabled={busy} onClick={() => run(() => api.post("/backups/"), t("Sauvegarde créée."))}><Icon name="backup" />{t("Sauvegarder maintenant")}</button></div>
      <ErrorBanner error={error || msg} />{info && <div className="banner"><Icon name="check_circle" />{info}</div>}
      {data && <div className="grid two pad-b" style={{ marginBottom: 16 }}>
        <form className="card" onSubmit={saveCfg} key={JSON.stringify(cfg)} style={{ display: "grid", gap: 10 }}>
          <h2><Icon name="schedule" className="muted" />{t("Sauvegarde automatique")}</h2>
          <label className="row"><input type="checkbox" name="auto" defaultChecked={cfg!.auto} /> {t("Activer (une par jour)")}</label>
          <div className="row"><Field label={t("Heure (0–23)")}><input type="number" name="hour" min={0} max={23} defaultValue={cfg!.hour} style={{ width: 90 }} /></Field>
            <Field label={t("Nombre à conserver")}><input type="number" name="keep" min={1} max={365} defaultValue={cfg!.keep} style={{ width: 110 }} /></Field></div>
          <Field label={t("Copie vers un autre disque / dossier réseau (facultatif)")}><input name="copy_dir" defaultValue={cfg!.copy_dir} placeholder="E:\Sauvegardes-Badgeo" dir="ltr" /></Field>
          <div className="row"><button disabled={busy}>{t("Enregistrer")}</button></div></form>
        <div className="card"><h2><Icon name="shield_person" className="muted" />{t("Protection")}</h2>
          <p><Pill tone={data.chiffrement ? "ok" : "warn"} icon={data.chiffrement ? "lock" : "lock_open"}>{data.chiffrement ? t("Chiffrées (AES)") : t("Non chiffrées")}</Pill></p>
          <p className="muted small">{data.chiffrement ? t("Les fichiers sont chiffrés avec la phrase de passe BADGEO_BACKUP_PASSPHRASE : sans elle, ils sont illisibles. Conservez-la à part.") : t("Définissez BADGEO_BACKUP_PASSPHRASE pour chiffrer les sauvegardes (elles contiennent des données personnelles).")}</p>
          <p className="muted small">{t("Dossier :")} <code dir="ltr">{data.dossier}</code></p>
          <p className="muted small">{t("Les sauvegardes contiennent les données, pas la mémoire des pointeuses (jamais effacée). Pensez à en copier régulièrement hors de ce poste.")}</p></div></div>}
      <div className="card pad-b"><h2><Icon name="upload_file" className="muted" />{t("Importer un fichier .badgeo")}</h2>
        <div className="row"><input type="file" ref={file} accept=".badgeo" />
          <button className="ghost" disabled={busy} onClick={() => { const f = file.current?.files?.[0]; if (!f) return setMsg(t("Choisissez un fichier.")); run(() => api.upload("/backups/upload/", f), t("Fichier importé : il apparaît dans la liste (aucune donnée modifiée).")); }}>{t("Importer")}</button></div></div>
      <div className="table-wrap"><table><thead><tr><th>{t("Date")}</th><th>{t("Type")}</th><th>{t("Par")}</th><th>{t("Taille")}</th><th>{t("Lignes")}</th><th>{t("Protection")}</th><th></th></tr></thead>
        <tbody>{data?.sauvegardes.map((b) => (
          <tr key={b.nom}><td>{dateTime(b.creee_le)}<div className="small muted" dir="ltr">{b.nom}</div>{b.copie && <div className={`small ${b.copie.startsWith("ÉCHEC") ? "err" : "muted"}`}>{t("Copie :")} {b.copie}</div>}</td>
            <td><Pill tone={b.type === "auto" ? "info" : ""}>{t(TYPE[b.type] ?? b.type)}</Pill></td><td>{b.par || "—"}</td><td>{mo(b.taille)}</td><td className="mono">{b.lignes ?? "—"}</td>
            <td>{b.chiffree ? <Pill tone="ok" icon="lock">{t("Chiffrée")}</Pill> : <Pill tone="warn" icon="lock_open">{t("Non chiffrée")}</Pill>}</td>
            <td><div className="row"><button className="sm ghost" onClick={() => api.download(`/backups/${b.nom}/`, b.nom)}><Icon name="download" />{t("Télécharger")}</button>
              <button className="sm" disabled={busy} onClick={() => restore(b)}><Icon name="restore" />{t("Restaurer")}</button>
              <button className="sm danger" disabled={busy} onClick={() => confirm(t("Supprimer {name} ?", { name: b.nom })) && run(() => api.remove(`/backups/${b.nom}/`), t("Sauvegarde supprimée."))}><Icon name="delete" />{t("Supprimer")}</button></div></td></tr>))}
          {data && !data.sauvegardes.length && <tr><td colSpan={7} className="muted">{t("Aucune sauvegarde.")}</td></tr>}</tbody></table></div>
    </>
  );
}
