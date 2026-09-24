import { ArrowUp, ArrowDown } from "lucide-react";

export interface Kpi {
  label: string;
  value: string | number;
  sub?: string;
  delta?: number | null; // percentage-point / count change vs previous period
}

function DeltaChip({ delta }: { delta: number }) {
  const positive = delta >= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
        positive ? "bg-badge-green-bg text-badge-green-text" : "bg-badge-red-bg text-badge-red-text"
      }`}
    >
      {positive ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
      {Math.abs(delta)}
    </span>
  );
}

export default function KpiStrip({ items, loading }: { items: Kpi[]; loading?: boolean }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {items.map((k) => (
        <div key={k.label} className="card-container p-4">
          {loading ? (
            <>
              <div className="h-3 w-20 bg-nav-hover rounded mb-2" />
              <div className="h-6 w-16 bg-nav-hover rounded" />
            </>
          ) : (
            <>
              <p className="text-xs text-text-secondary">{k.label}</p>
              <div className="flex items-center gap-2 mt-1">
                <p className="text-xl font-bold text-text-primary">{k.value}</p>
                {k.delta != null && <DeltaChip delta={k.delta} />}
              </div>
              {k.sub && <p className="text-[11px] text-text-muted mt-0.5">{k.sub}</p>}
            </>
          )}
        </div>
      ))}
    </div>
  );
}
