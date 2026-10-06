interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
  compact?: boolean;
  tooltip?: string;
  /** Notification count circle (e.g. unprocessed inbox files). Hidden when 0/undefined. */
  badge?: number;
}

function Badge({ count }: { count: number }) {
  if (!count || count <= 0) return null;
  const text = count > 99 ? "99+" : String(count);
  return (
    <span
      className="min-w-[20px] h-5 px-1 rounded-full bg-danger text-white text-[11px] font-bold flex items-center justify-center tabular-nums"
      aria-label={`${count} unprocessed`}
    >
      {text}
    </span>
  );
}

export default function NavItem({ icon, label, active, onClick, compact, tooltip, badge }: NavItemProps) {
  return (
    <button
      onClick={onClick}
      title={tooltip || label}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm transition-all duration-150 border-l-[3px] ${
        compact ? "justify-center px-2 border-l-transparent" : ""
      } ${
        active
          ? "bg-nav-active-bg text-accent font-semibold border-l-accent"
          : "text-text-secondary hover:bg-nav-hover hover:text-text-primary border-l-transparent"
      }`}
    >
      {compact ? (
        <span className={`relative ${active ? "text-accent" : "text-text-muted"}`}>
          {icon}
          {badge != null && badge > 0 && (
            <span className="absolute -top-1.5 -right-2">
              <Badge count={badge} />
            </span>
          )}
        </span>
      ) : (
        <>
          <span className={active ? "text-accent" : "text-text-muted"}>{icon}</span>
          <span className="flex-1 text-left">{label}</span>
          {badge != null && badge > 0 && <Badge count={badge} />}
        </>
      )}
    </button>
  );
}
