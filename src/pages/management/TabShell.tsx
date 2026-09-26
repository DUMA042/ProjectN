interface TabShellProps {
  title: string;
  note: string;
}

/** Minimal placeholder for tabs not yet built in the rollout. */
export default function TabShell({ title, note }: TabShellProps) {
  return (
    <div className="card-container p-10 text-center">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <p className="mt-1 text-xs text-text-muted max-w-md mx-auto">{note}</p>
    </div>
  );
}
