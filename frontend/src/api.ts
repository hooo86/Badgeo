export interface Device {
  id: number; name: string; vendor: "zkteco" | "unis"; model: string; ip_address: string; port: number;
  serial_number: string; protocol: string; status: "unknown" | "connected" | "disconnected" | "error";
  last_error: string; last_seen_at: string | null; last_sync_at: string | null; last_sync_ok: boolean | null;
  events_total: number; sync_interval_minutes: number;
}
export interface Diagnostic {
  tcp_reachable: boolean; handshake: boolean; stage: string | null; message: string; info: Record<string, string>;
}

let token = localStorage.getItem("token");

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Token ${token}` } : {}) },
  });
  if (r.status === 401) { token = null; localStorage.removeItem("token"); throw new Error("401"); }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(JSON.stringify(body));
  return body as T;
}

export const login = async (username: string, password: string) => {
  const r = await fetch("/api/auth/token/", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }) });
  if (!r.ok) throw new Error("Identifiants invalides");
  token = (await r.json()).token as string;
  localStorage.setItem("token", token);
};
export const isLogged = () => token !== null;
export const listDevices = async () => (await call<{ results: Device[] }>("/devices/")).results;
export const createDevice = (d: Partial<Device> & { comm_key?: number }) =>
  call<Device>("/devices/", { method: "POST", body: JSON.stringify(d) });
export const deleteDevice = (id: number) => call<unknown>(`/devices/${id}/`, { method: "DELETE" });
export const testDevice = (id: number) => call<Diagnostic>(`/devices/${id}/test_connection/`, { method: "POST" });
export const syncDevice = (id: number) => call<unknown>(`/devices/${id}/sync/`, { method: "POST" });
