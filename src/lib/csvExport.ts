function escapeCSVCell(value: unknown): string {
  const str = value == null ? "" : String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

function sanitizeFilename(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
}

export function exportToCSV(
  data: Record<string, any>[],
  chartName: string,
  dateRange?: { startDate?: string; endDate?: string }
): void {
  if (!data.length) return;

  const headers = Object.keys(data[0]);
  const rows = data.map((row) =>
    headers.map((h) => escapeCSVCell(row[h])).join(",")
  );

  const csv = headers.join(",") + "\r\n" + rows.join("\r\n");

  const start = dateRange?.startDate || "unknown";
  const end = dateRange?.endDate || "unknown";
  const filename = `${sanitizeFilename(chartName)}_${start}_to_${end}.csv`;

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
