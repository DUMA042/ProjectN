/** Bridge to the desktop host. Every function is safe to import in a browser. */

import { invoke } from "@tauri-apps/api/core";

export type BackendStatus =
  | { state: "disabled" }
  | { state: "starting" }
  | { state: "ready"; api_port: number; pg_port: number }
  | { state: "failed"; message: string };

export function isDesktopApp(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function getBackendStatus(): Promise<BackendStatus> {
  return invoke<BackendStatus>("backend_status");
}

export function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunk = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunk) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunk));
  }
  return btoa(binary);
}

export async function saveDownload(path: string, bytes: Uint8Array): Promise<void> {
  await invoke("save_download", { path, dataBase64: bytesToBase64(bytes) });
}

export async function closeWindow(): Promise<void> {
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  await getCurrentWindow().close();
}
