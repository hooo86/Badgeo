import { FormEvent, useEffect, useState } from "react";
import * as api from "./api";

const LABEL = { unknown: "Inconnu", connected: "Connecté", disconnected: "Déconnecté", error: "Erreur" } as const;
const fmt = (d: string | null) => (d ? new Date(d).toLocaleString("fr-FR") : "—");

function Login({ onDone }: { onDone: () => void }) {
  const [err, setErr] = useState("");
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try { await api.login(String(f.get("u")), String(f.get("p"))); onDone(); }
    catch (x) { setErr((x as Error).message); }
  };
  return (
    <form className="card narrow" onSubmit={submit}>
      <img src="/logo.svg" alt="Badgeo" height={40} />
      <h1>Connexion</h1>
      <input name="u" placeholder="Utilisateur" required />
      <input name="p" type="password" placeholder="Mot de passe" required />
      <button>Se connecter</button>{err && <p className="err">{err}</p>}
    </form>
  );
}

function Devices() {
  const [items, setItems] = useState<api.Device[]>([]);
  const [diag, setDiag] = useState<Record<number, api.Diagnostic>>({});
  const [msg, setMsg] = useState("");
  const load = () => api.listDevices().then(setItems).catch((e) => setMsg(String(e.message)));
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);

  const add = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await api.createDevice({ name: String(f.get("name")), vendor: f.get("vendor") as "zkteco" | "unis",
        model: String(f.get("model")), ip_address: String(f.get("ip")), port: Number(f.get("port")),
        comm_key: Number(f.get("key") || 0) });
      e.currentTarget.reset(); setMsg(""); load();
    } catch (x) { setMsg((x as Error).message); }
  };
  const test = async (id: number) => { setDiag({ ...diag, [id]: await api.testDevice(id) }); load(); };

  return (
    <main>
      <img src="/logo.svg" alt="Badgeo" height={40} />
      <h1>Pointeuses</h1>
      <form className="card grid" onSubmit={add}>
        <input name="name" placeholder="Nom" required />
        <select name="vendor"><option value="zkteco">ZKTeco</option><option value="unis">UNIS</option></select>
        <input name="model" placeholder="Modèle exact" />
        <input name="ip" placeholder="Adresse IP" required />
        <input name="port" type="number" defaultValue={4370} required />
        <input name="key" type="number" placeholder="Clé de communication" />
        <button>Ajouter</button>
      </form>
      {msg && <p className="err">{msg}</p>}
      <div className="table-wrap"><table>
        <thead><tr><th>Nom</th><th>Fabricant / modèle</th><th>Adresse</th><th>État</th><th>Dernier contact</th>
          <th>Dernière synchro</th><th>Événements</th><th></th></tr></thead>
        <tbody>{items.map((d) => (
          <tr key={d.id}>
            <td>{d.name}</td><td>{d.vendor.toUpperCase()} {d.model}</td><td>{d.ip_address}:{d.port}</td>
            <td><span className={`pill ${d.status}`}>{LABEL[d.status]}</span>
              {d.last_error && <div className="err small">{d.last_error}</div>}
              {diag[d.id] && <div className="small">TCP : {diag[d.id].tcp_reachable ? "ok" : "échec"} · Protocole : {diag[d.id].handshake ? "ok" : `échec (${diag[d.id].stage ?? "?"})`}</div>}</td>
            <td>{fmt(d.last_seen_at)}</td><td>{fmt(d.last_sync_at)}</td><td>{d.events_total}</td>
            <td className="actions">
              <button onClick={() => test(d.id)}>Tester</button>
              <button onClick={() => api.syncDevice(d.id).then(() => setMsg("Synchronisation en file"))}>Synchroniser</button>
              <button className="danger" onClick={() => confirm(`Supprimer ${d.name} ?`) && api.deleteDevice(d.id).then(load)}>Supprimer</button>
            </td>
          </tr>))}
        </tbody></table></div>
    </main>
  );
}

export default function App() {
  const [ok, setOk] = useState(api.isLogged());
  return ok ? <Devices /> : <Login onDone={() => setOk(true)} />;
}
