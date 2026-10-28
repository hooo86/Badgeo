import { FormEvent, useState } from "react";
import * as api from "../api";
import { t, tk, type Lang } from "../i18n";
import { dateFr, ErrorBanner, Field, Icon, LangSwitch, Logo, Pill, ThemeSwitch, useLoad } from "../ui";

export function Activation({ state, onDone, onLang }: { state: api.LicenceState; onDone: () => void; onLang: (l: Lang) => void }) {
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false), [copied, setCopied] = useState(false);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setBusy(true);
    try { await api.activate(String(new FormData(e.currentTarget).get("cle"))); onDone(); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="login"><div className="corner"><LangSwitch onChange={onLang} /><ThemeSwitch /></div>
      <form className="card" onSubmit={submit} style={{ maxWidth: 480 }}>
        <Logo height={44} />
        <h1 style={{ fontSize: 22, margin: 0 }}>{t("Activer Badgeo")}</h1>
        <p className="muted" style={{ margin: 0 }}>{t("Code d'installation de ce poste :")}</p>
        <button type="button" className="ghost mono" style={{ fontSize: 22, letterSpacing: ".06em" }} dir="ltr"
          onClick={() => navigator.clipboard?.writeText(state.code_installation).then(() => setCopied(true))} title={t("Copier")}>{state.code_installation}<Icon name="content_copy" /></button>
        {copied && <span className="small ok">{t("Copié")}</span>}
        <p className="muted small" style={{ margin: 0 }}>{t("Communiquez ce code à l'éditeur : il vous renvoie une clé valable pour ce poste seulement. L'activation se fait sans Internet.")}</p>
        <Field label={t("Clé d'activation")}><textarea name="cle" rows={4} required placeholder="BADG1-…" dir="ltr" className="mono" style={{ fontSize: 12 }} /></Field>
        <button disabled={busy}><Icon name="verified_user" />{t("Activer")}</button>{err && <div className="err">{t(err)}</div>}</form></div>
  );
}

export function ChangePassword({ forced, onDone, onCancel }: { forced: boolean; onDone: () => void; onCancel?: () => void }) {
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    if (f.get("n") !== f.get("c")) return setErr(t("Les deux mots de passe ne sont pas identiques."));
    setBusy(true);
    try { await api.changePassword(String(f.get("a")), String(f.get("n"))); onDone(); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className={forced ? "login" : ""}><form className="card" onSubmit={submit} style={{ maxWidth: 400, display: "grid", gap: 12 }}>
      <h2><Icon name="lock" />{forced ? t("Choisissez un nouveau mot de passe") : t("Changer mon mot de passe")}</h2>
      {forced && <p className="muted small" style={{ margin: 0 }}>{t("Votre mot de passe est provisoire : il doit être remplacé avant de continuer (10 caractères minimum, pas trop courant).")}</p>}
      <input name="a" type="password" placeholder={t("Mot de passe actuel")} autoComplete="current-password" required />
      <input name="n" type="password" placeholder={t("Nouveau mot de passe")} autoComplete="new-password" minLength={10} required />
      <input name="c" type="password" placeholder={t("Confirmer")} autoComplete="new-password" required />
      <div className="row"><button disabled={busy}>{t("Enregistrer")}</button>{onCancel && <button type="button" className="ghost" onClick={onCancel}>{t("Annuler")}</button>}</div>
      {err && <div className="err">{t(err)}</div>}</form></div>
  );
}

export default function LicencePage({ canEdit }: { canEdit: boolean }) {
  const { data: st, error, reload } = useLoad(api.licence, []);
  const [err, setErr] = useState(""), [ok, setOk] = useState(false), [pwd, setPwd] = useState(false);
  const replace = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try { await api.activate(String(new FormData(e.currentTarget).get("cle"))); setOk(true); setErr(""); reload(); } catch (x) { setErr((x as Error).message); }
  };
  const l = st?.licence;
  const usage = (n: number | undefined, max: number | null | undefined) => (max ? `${n ?? 0} / ${max}` : `${n ?? 0} ${t("(illimité)")}`);
  const MOD: Record<string, string> = { mobile: tk("Application mobile employé"), reports: tk("Rapports et exports"), leaves: tk("Absences et autorisations") };
  return (
    <>
      <div className="head"><div><div className="eyebrow">{t("Paramètres")}</div><h1>{t("Licence et compte")}</h1></div></div>
      <ErrorBanner error={error} />
      {st && !st.requise && <div className="banner"><Icon name="info" />{t("Cette installation n'exige pas de licence (édition serveur).")}</div>}
      {l && <div className="card pad-b">
        <div className="row"><h2 style={{ margin: 0 }}>{l.client}</h2>{l.essai && <Pill tone="warn">{t("Licence d'essai")}</Pill>}
          {l.expiree ? <Pill tone="bad" icon="block">{t("Expirée : lecture seule")}</Pill> : l.expire_le ? <Pill tone={(l.jours_restants ?? 99) <= 30 ? "warn" : "ok"} icon="timelapse">{t("{n} jour(s) restant(s)", { n: l.jours_restants ?? 0 })}</Pill> : <Pill tone="ok">{t("Sans limite de durée")}</Pill>}</div>
        <p className="muted small">N° {l.numero}{l.expire_le && <> · {t("valable jusqu'au {date}", { date: dateFr(l.expire_le) })}</>}</p>
        {l.horloge_reculee && <div className="banner bad"><Icon name="warning" />{t("La date de cet ordinateur est antérieure à la dernière utilisation : remettez l'horloge à l'heure.")}</div>}
        <div className="grid kpis" style={{ marginTop: 8 }}>
          <div className="kpi"><div className="label">{t("Employés actifs")}</div><div className="value mono" style={{ fontSize: 24, lineHeight: "32px" }}>{usage(st?.usage?.employes, l.max_employes)}</div></div>
          <div className="kpi"><div className="label">{t("Pointeuses")}</div><div className="value mono" style={{ fontSize: 24, lineHeight: "32px" }}>{usage(st?.usage?.pointeuses, l.max_pointeuses)}</div></div>
        </div>
        <div className="row" style={{ marginTop: 8 }}>{Object.keys(st!.modules_disponibles).map((k) => <Pill key={k} tone={l.modules.includes(k) ? "ok" : ""} icon={l.modules.includes(k) ? "check_circle" : "block"}>{t(MOD[k] ?? k)}</Pill>)}</div></div>}
      {st && st.requise && <div className="card pad-b"><p className="muted small" style={{ margin: 0 }}>{t("Code d'installation de ce poste")}</p>
        <b className="mono" style={{ fontSize: 20, userSelect: "all" }} dir="ltr">{st.code_installation}</b></div>}
      {canEdit && st?.requise && <form className="card pad-b" onSubmit={replace} style={{ display: "grid", gap: 8 }}>
        <h2><Icon name="vpn_key" className="muted" />{t("Saisir une nouvelle clé")}</h2><textarea name="cle" rows={3} required placeholder="BADG1-…" dir="ltr" className="mono" style={{ fontSize: 12 }} />
        <div className="row"><button>{t("Enregistrer la clé")}</button>{ok && <Pill tone="ok">{t("Clé enregistrée")}</Pill>}</div>{err && <div className="err">{t(err)}</div>}</form>}
      {pwd ? <ChangePassword forced={false} onDone={() => setPwd(false)} onCancel={() => setPwd(false)} /> : <button className="ghost" onClick={() => setPwd(true)}><Icon name="lock" />{t("Changer mon mot de passe")}</button>}
    </>
  );
}
