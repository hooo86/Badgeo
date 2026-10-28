import { FormEvent, useState } from "react";
import * as api from "../api";
import { dateFr, ErrorBanner, Field, Pill, useLoad } from "../ui";

export function Activation({ state, onDone }: { state: api.LicenceState; onDone: () => void }) {
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false), [copied, setCopied] = useState(false);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setBusy(true);
    try { await api.activate(String(new FormData(e.currentTarget).get("cle"))); onDone(); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="login"><form className="card" onSubmit={submit} style={{ maxWidth: 480 }}>
      <img src="/logo.svg" alt="Badgeo" height={44} style={{ justifySelf: "start" }} />
      <h1 style={{ fontSize: 22, margin: 0 }}>Activer Badgeo</h1>
      <p className="muted" style={{ margin: 0 }}>Code d'installation de ce poste :</p>
      <button type="button" className="ghost" style={{ fontFamily: "ui-monospace, monospace", fontSize: 22, letterSpacing: ".06em" }}
        onClick={() => navigator.clipboard?.writeText(state.code_installation).then(() => setCopied(true))} title="Copier">{state.code_installation}</button>
      {copied && <span className="small ok" style={{ color: "var(--ok)" }}>Copié</span>}
      <p className="muted small" style={{ margin: 0 }}>Communiquez ce code à l'éditeur : il vous renvoie une clé valable pour ce poste seulement. L'activation se fait sans Internet.</p>
      <Field label="Clé d'activation"><textarea name="cle" rows={4} required placeholder="BADG1-…" style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }} /></Field>
      <button disabled={busy}>Activer</button>{err && <div className="err">{err}</div>}</form></div>
  );
}

export function ChangePassword({ forced, onDone, onCancel }: { forced: boolean; onDone: () => void; onCancel?: () => void }) {
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    if (f.get("n") !== f.get("c")) return setErr("Les deux mots de passe ne sont pas identiques.");
    setBusy(true);
    try { await api.changePassword(String(f.get("a")), String(f.get("n"))); onDone(); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className={forced ? "login" : ""}><form className="card" onSubmit={submit} style={{ maxWidth: 400, display: "grid", gap: 12 }}>
      <h2>{forced ? "Choisissez un nouveau mot de passe" : "Changer mon mot de passe"}</h2>
      {forced && <p className="muted small" style={{ margin: 0 }}>Votre mot de passe est provisoire : il doit être remplacé avant de continuer (10 caractères minimum, pas trop courant).</p>}
      <input name="a" type="password" placeholder="Mot de passe actuel" autoComplete="current-password" required />
      <input name="n" type="password" placeholder="Nouveau mot de passe" autoComplete="new-password" minLength={10} required />
      <input name="c" type="password" placeholder="Confirmer" autoComplete="new-password" required />
      <div className="row"><button disabled={busy}>Enregistrer</button>{onCancel && <button type="button" className="ghost" onClick={onCancel}>Annuler</button>}</div>
      {err && <div className="err">{err}</div>}</form></div>
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
  const usage = (n: number | undefined, max: number | null | undefined) => (max ? `${n ?? 0} / ${max}` : `${n ?? 0} (illimité)`);
  return (
    <>
      <div className="head"><div><div className="eyebrow">Paramètres</div><h1>Licence et compte</h1></div></div>
      <ErrorBanner error={error} />
      {st && !st.requise && <div className="banner">Cette installation n'exige pas de licence (édition serveur).</div>}
      {l && <div className="card" style={{ marginBottom: 16 }}>
        <div className="row"><h2 style={{ margin: 0 }}>{l.client}</h2>{l.essai && <Pill tone="warn">Licence d'essai</Pill>}
          {l.expiree ? <Pill tone="bad">Expirée : lecture seule</Pill> : l.expire_le ? <Pill tone={(l.jours_restants ?? 99) <= 30 ? "warn" : "ok"}>{l.jours_restants} jour(s) restant(s)</Pill> : <Pill tone="ok">Sans limite de durée</Pill>}</div>
        <p className="muted small">N° {l.numero}{l.expire_le && <> · valable jusqu'au {dateFr(l.expire_le)}</>}</p>
        {l.horloge_reculee && <div className="banner bad">La date de cet ordinateur est antérieure à la dernière utilisation : remettez l'horloge à l'heure.</div>}
        <div className="grid kpis" style={{ marginTop: 8 }}>
          <div className="kpi"><div className="label">Employés actifs</div><div className="value" style={{ fontSize: 24, lineHeight: "32px" }}>{usage(st?.usage?.employes, l.max_employes)}</div></div>
          <div className="kpi"><div className="label">Pointeuses</div><div className="value" style={{ fontSize: 24, lineHeight: "32px" }}>{usage(st?.usage?.pointeuses, l.max_pointeuses)}</div></div>
        </div>
        <div className="row" style={{ marginTop: 8 }}>{Object.entries(st!.modules_disponibles).map(([k, v]) => <Pill key={k} tone={l.modules.includes(k) ? "ok" : ""}>{l.modules.includes(k) ? "✓ " : "✗ "}{v}</Pill>)}</div></div>}
      {st && st.requise && <div className="card" style={{ marginBottom: 16 }}><p className="muted small" style={{ margin: 0 }}>Code d'installation de ce poste</p>
        <b style={{ fontFamily: "ui-monospace, monospace", fontSize: 20, userSelect: "all" }}>{st.code_installation}</b></div>}
      {canEdit && st?.requise && <form className="card" onSubmit={replace} style={{ display: "grid", gap: 8, marginBottom: 16 }}>
        <h2>Saisir une nouvelle clé</h2><textarea name="cle" rows={3} required placeholder="BADG1-…" style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }} />
        <div className="row"><button>Enregistrer la clé</button>{ok && <Pill tone="ok">Clé enregistrée</Pill>}</div>{err && <div className="err">{err}</div>}</form>}
      {pwd ? <ChangePassword forced={false} onDone={() => setPwd(false)} onCancel={() => setPwd(false)} /> : <button className="ghost" onClick={() => setPwd(true)}>Changer mon mot de passe</button>}
    </>
  );
}
