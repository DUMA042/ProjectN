interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}

export default function NavItem({ icon, label, active, onClick }: NavItemProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm transition-all duration-150 ${
        active
          ? "bg-nav-hover text-text-primary font-semibold"
          : "text-text-secondary hover:bg-nav-hover hover:text-text-primary"
      }`}
    >
      <span className={active ? "text-accent" : "text-text-muted"}>{icon}</span>
      <span>{label}</span>
    </button>
  );
}
