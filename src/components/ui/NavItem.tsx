interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
  compact?: boolean;
  tooltip?: string;
}

export default function NavItem({ icon, label, active, onClick, compact, tooltip }: NavItemProps) {
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
      <span className={active ? "text-accent" : "text-text-muted"}>{icon}</span>
      {!compact && <span>{label}</span>}
    </button>
  );
}
