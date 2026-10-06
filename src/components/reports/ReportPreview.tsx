import { Download, FileText } from "lucide-react";
import type { ReportView } from "@/lib/reportBuild";

/** Render the generated report: headings, tables, bold, bullets, charts. */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const parts = text.split(/(\*\*.+?\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") && p.length > 4 ? (
      <strong key={`${keyPrefix}-${i}`}>{p.slice(2, -2)}</strong>
    ) : (
      <span key={`${keyPrefix}-${i}`}>{p}</span>
    )
  );
}

function ReportBody({ view }: { view: ReportView }) {
  const chartByIndex = new Map(
    view.charts.map((c, i) => [i, { ...c, url: c.url.startsWith("http") ? c.url : c.url }])
  );
  const lines = view.markdown.split("\n");
  const out: React.ReactNode[] = [];
  let tableBuf: string[][] = [];
  const flushTable = (key: string) => {
    if (tableBuf.length < 2) {
      tableBuf = [];
      return;
    }
    const [headers, ...rows] = tableBuf;
    out.push(
      <div key={key} className="overflow-x-auto my-2">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              {headers.map((h, j) => (
                <th key={j} className="border border-border bg-accent text-white font-semibold px-2 py-1 text-left">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, ri) => (
              <tr key={ri} className="even:bg-nav-hover/40">
                {headers.map((_, j) => (
                  <td key={j} className="border border-border px-2 py-1 text-text-primary">
                    {r[j] || ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    tableBuf = [];
  };
  lines.forEach((line, i) => {
    const t = line.trimEnd();
    const chartM = t.match(/^!\[(.*?)\]\(build-chart:(\d+)\)$/);
    if (/^\s*\|.*\|\s*$/.test(t)) {
      const cells = t.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      if (cells.length && cells.every((c) => /^:?-{2,}:?$/.test(c))) return; // separator
      tableBuf.push(cells);
      return;
    }
    flushTable(`t-${i}`);
    if (chartM) {
      const chart = chartByIndex.get(Number(chartM[2]));
      if (chart) {
        out.push(
          <figure key={`c-${i}`} className="my-3">
            <img src={chart.url} alt={chart.title} className="w-full rounded-btn border border-border" />
            <figcaption className="text-[11px] text-text-muted mt-1">{chart.title}</figcaption>
          </figure>
        );
      }
      return;
    }
    if (t.startsWith("## ")) {
      out.push(<h3 key={`h-${i}`} className="text-base font-semibold text-accent mt-4 mb-1">{renderInline(t.slice(3), `h-${i}`)}</h3>);
    } else if (t.startsWith("### ")) {
      out.push(<h4 key={`h-${i}`} className="text-sm font-semibold text-text-primary mt-3 mb-1">{renderInline(t.slice(4), `h-${i}`)}</h4>);
    } else if (t.startsWith("- ")) {
      out.push(<li key={`l-${i}`} className="text-xs text-text-primary ml-5 list-disc">{renderInline(t.slice(2), `l-${i}`)}</li>);
    } else if (t) {
      out.push(<p key={`p-${i}`} className="text-xs text-text-primary my-1.5 leading-relaxed">{renderInline(t, `p-${i}`)}</p>);
    }
  });
  flushTable("t-end");
  return <>{out}</>;
}

export default function ReportPreview({ view }: { view: ReportView }) {
  return (
    <div className="card-container overflow-hidden">
      <div className="px-4 pt-3 pb-2 flex items-center gap-2 flex-wrap">
        <FileText size={13} className="text-text-muted" />
        <h2 className="text-xs font-semibold text-text-primary">HR Report</h2>
        <a
          href={view.download_url}
          download
          className="ml-auto px-3 py-1.5 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity inline-flex items-center gap-1.5"
        >
          <Download size={13} /> Download Word
        </a>
      </div>
      <div className="px-4 pb-4 max-h-[60vh] overflow-y-auto">
        <ReportBody view={view} />
      </div>
    </div>
  );
}
