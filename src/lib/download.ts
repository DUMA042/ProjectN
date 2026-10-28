/** Single place where files are handed to the operating system.
 *
 * Browser builds use a blob URL + anchor download. Desktop builds open the
 * native save dialog and write through the host command (no filesystem plugin).
 * Errors are reported to the app shell so they can be shown as a toast.
 */

import { resolveApiUrl } from "@/lib/api";
import { isDesktopApp, saveDownload } from "@/lib/tauri";

export const DOWNLOAD_ERROR_EVENT = "flow:download-error";

function triggerAnchor(href: string, filename: string): void {
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  link.rel = "noopener";
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function reportDownloadError(error: unknown): void {
  const message =
    error instanceof Error && error.message
      ? error.message
      : "The file could not be saved.";
  console.error("[download]", message);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(DOWNLOAD_ERROR_EVENT, { detail: message }));
  }
}

/** Save in-memory content (CSV exports, report files fetched as blobs). */
export async function saveBlob(blob: Blob, filename: string): Promise<void> {
  if (isDesktopApp()) {
    try {
      const { save } = await import("@tauri-apps/plugin-dialog");
      const path = await save({ defaultPath: filename });
      if (!path) return;
      await saveDownload(path, new Uint8Array(await blob.arrayBuffer()));
    } catch (error) {
      reportDownloadError(error);
    }
    return;
  }

  const url = URL.createObjectURL(blob);
  try {
    triggerAnchor(url, filename);
  } finally {
    // Revoke on the next tick so the download has started.
    setTimeout(() => URL.revokeObjectURL(url), 1_000);
  }
}

/** Save a server-provided file URL (API endpoints that send Content-Disposition). */
export async function saveUrl(url: string, filename: string): Promise<void> {
  if (isDesktopApp()) {
    try {
      const response = await fetch(resolveApiUrl(url));
      if (!response.ok) {
        throw new Error(`The file could not be downloaded (status ${response.status}).`);
      }
      await saveBlob(await response.blob(), filename);
    } catch (error) {
      reportDownloadError(error);
    }
    return;
  }

  triggerAnchor(url, filename);
}
