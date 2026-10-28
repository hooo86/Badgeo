export interface Page<T> { count: number; results: T[] }
export interface Device {
  id: number; name: string; vendor: "zkteco" | "unis"; model: string; ip_address: string; port: number;
  serial_number: string; protocol: string; status: "unknown" | "connected" | "disconnected" | "error";
  last_error: string; last_seen_at: string | null; last_sync_at: string | null; last_sync_ok: boolean | null;
  events_total: number; sync_interval_minutes: number;
}
export interface Diagnostic { tcp_reachable: boolean; handshake: boolean; stage: string | null; message: string; info: Record<string, string> }
export interface Day {
  id: number; employee: number; employee_name: string; matricule: string; work_date: string; status: string;
  shift_name: string | null; first_in: string | null; last_out: string | null; punch_times: string[];
  presence_min: number | null; worked_min: number | null; late_min: number; early_leave_min: number;
  overtime_min: number; missing_min: number; anomalies: string[]; justified: boolean | null;
}
export interface Employee {
  id: number; matricule: string; first_name: string; last_name: string; job_title: string; org_unit: number | null;
  org_unit_name: string | null; status: string; hire_date: string | null;
}
export interface Correction {
  id: number; employee: number; work_date: string; kind: string; new_timestamp: string | null; new_status: string;
  reason: string; state: "pending" | "validated" | "rejected"; created_at: string; review_note: string;
  initial: Record<string, unknown>; after: Record<string, unknown> | null;
}
export interface Dashboard {
  date: string; headcount: number; present: number; late: number; absent: number; on_leave: number; incomplete: number;
  anomalies_to_review: number; corrections_pending: number; punches_today: number; presence_rate: number | null;
  devices?: { connected: number; disconnected: number; last_sync_at: string | null }; unmapped_punches_today?: number;
  arrivals: { slot: string; count: number }[]; daily: { date: string; present: number; late: number; expected: number }[];
  by_unit: { unit: string; present: number; expected: number; rate: number | null }[];
  recent: { time: string; employee: string; matricule: string; source: string; device: string | null }[];
}
export interface Me {
  employee: { id: number; matricule: string; first_name: string; last_name: string; job_title: string; org_unit: string | null };
  mobile_punch_enabled: boolean; mobile_punch_allowed_here: boolean; today: Day; server_time: string;
}
export interface Who { username: string; name: string; role: string | null; has_employee: boolean }

let token: string | null = null;
try { token = localStorage.getItem("token"); } catch { /* storage unavailable */ }
export const setToken = (t: string | null) => {
  token = t;
  try { t ? localStorage.setItem("token", t) : localStorage.removeItem("token"); } catch { /* ignore */ }
};
export const isLogged = () => token !== null;

export class ApiError extends Error { constructor(public status: number, msg: string) { super(msg); } }

function readable(body: unknown): string {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    if (typeof b.detail === "string") return b.detail;
    return Object.entries(b).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(" ") : String(v)}`).join(" · ");
  }
  return String(body ?? "Erreur");
}

async function raw(path: string, init: RequestInit = {}): Promise<Response> {
  const isForm = init.body instanceof FormData;
  const r = await fetch(`/api${path}`, {
    ...init,
    headers: { ...(isForm ? {} : { "Content-Type": "application/json" }), ...(token ? { Authorization: `Token ${token}` } : {}) },
  });
  if (r.status === 401) { setToken(null); window.dispatchEvent(new Event("badgeo:logout")); throw new ApiError(401, "Session expirée"); }
  if (!r.ok) throw new ApiError(r.status, readable(await r.json().catch(() => null)));
  return r;
}
const json = async <T,>(path: string, init?: RequestInit) => (await raw(path, init)).json() as Promise<T>;
const body = (b: unknown) => JSON.stringify(b);
export const qs = (p: Record<string, string | number | undefined | null>) => {
  const s = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && s.set(k, String(v)));
  const t = s.toString();
  return t ? `?${t}` : "";
};

export async function login(username: string, password: string) {
  const r = await fetch("/api/auth/token/", { method: "POST", headers: { "Content-Type": "application/json" }, body: body({ username, password }) });
  if (r.status === 429) throw new Error("Trop de tentatives, réessayez dans une minute.");
  if (!r.ok) throw new Error("Identifiants invalides");
  setToken((await r.json()).token);
}
export async function download(path: string, filename: string) {
  const blob = await (await raw(path)).blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

export const whoami = () => json<Who>("/whoami/");
export const dashboard = () => json<Dashboard>("/dashboard/");
export const list = <T,>(path: string, params: Record<string, string | number | undefined | null> = {}) => json<Page<T>>(`${path}${qs(params)}`);
export const create = <T,>(path: string, data: unknown) => json<T>(path, { method: "POST", body: body(data) });
export const remove = (path: string) => raw(path, { method: "DELETE" });
export const post = <T,>(path: string, data: unknown = {}) => json<T>(path, { method: "POST", body: body(data) });
export const upload = <T,>(path: string, file: File) => { const f = new FormData(); f.append("file", file); return json<T>(path, { method: "POST", body: f }); };
export const testDevice = (id: number) => post<Diagnostic>(`/devices/${id}/test_connection/`);
export const me = () => json<Me>("/me/");
export const mePunch = () => post<{ timestamp: string; today: Day }>("/me/punch/");
export const meHistory = (from: string, to: string) =>
  json<{ days: Day[]; totals: { worked_min: number; late_min: number; overtime_min: number; expected_min: number } }>(`/me/history/${qs({ from, to })}`);
export const mePlanning = () => json<{ days: { date: string; holiday: boolean; shift: { name: string; start: string; end: string; crosses_midnight: boolean } | null }[] }>("/me/planning/");
