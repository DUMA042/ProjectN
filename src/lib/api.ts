import axios from "axios";

/** Where the API lives.
 *
 * - `VITE_API_BASE_URL` wins when set (any deployment can override).
 * - In development an empty base means "same origin", so Vite's `/api` proxy
 *   forwards to the FastAPI server (see vite.config.ts).
 * - Outside development the UI is served from the desktop asset protocol, so
 *   relative paths would resolve against that protocol and fail. Use the local
 *   service address instead. (Pure function — unit-tested.)
 */
export function resolveApiBase(
  configured: string | undefined,
  isDev: boolean
): string {
  const explicit = (configured || "").trim();
  if (explicit) return explicit.replace(/\/+$/, "");
  if (isDev) return "";
  return "http://127.0.0.1:8001";
}

export const API_BASE = resolveApiBase(
  import.meta.env.VITE_API_BASE_URL,
  Boolean(import.meta.env.DEV)
);

/** Base address for a manager-chosen port (packaged desktop runs). */
export function apiBaseForPort(port: number): string {
  return `http://127.0.0.1:${port}`;
}

/** Configure the client once the desktop host reports its port. */
export function setApiBase(base: string): void {
  api.defaults.baseURL = base;
}

/** Turn an API path (e.g. /api/reports/build/x/download) into a fetchable URL. */
export function resolveApiUrl(url: string): string {
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(url)) return url;
  const base = (api.defaults.baseURL || "").replace(/\/+$/, "");
  if (!base) return url;
  return `${base}/${url.replace(/^\/+/, "")}`;
}

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(`API Error ${error.response.status}:`, error.response.data);
    } else if (error.request) {
      console.error("API No Response:", error.message);
    }
    return Promise.reject(error);
  }
);
