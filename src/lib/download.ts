/** Single place where files are handed to the operating system.
 *
 * Today this uses the browser mechanism (blob URL + anchor download), which is
 * what the web build and the Tauri dev window use. When the app is packaged,
 * this one module is swapped for Tauri's save-dialog + filesystem plugins;
 * no call site needs to change.
 */

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

/** Save in-memory content (CSV exports, report files fetched as blobs). */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  try {
    triggerAnchor(url, filename);
  } finally {
    // Revoke on the next tick so the download has started.
    setTimeout(() => URL.revokeObjectURL(url), 1_000);
  }
}

/** Save a server-provided file URL (API endpoints that send Content-Disposition). */
export function saveUrl(url: string, filename: string): void {
  triggerAnchor(url, filename);
}
