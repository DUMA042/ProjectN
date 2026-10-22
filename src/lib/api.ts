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
