import { useLocation } from "react-router-dom";
import { Bell } from "lucide-react";

export default function Header() {
  const location = useLocation();
  
  const getBreadcrumb = () => {
    const parts = location.pathname.split("/").filter(Boolean);
    if (parts.length === 0) return "Dashboard";
    return parts.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(" / ");
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <header className="h-[64px] flex-shrink-0 bg-surface border-b border-border px-6 flex items-center justify-between">
      <div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-muted">{getBreadcrumb()}</span>
        </div>
        <h1 className="text-base font-semibold text-text-primary">
          {getGreeting()}, Admin <span className="ml-1">👋</span>
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <button className="w-9 h-9 rounded-btn border border-border flex items-center justify-center text-text-muted hover:bg-nav-hover hover:text-text-secondary transition-colors">
          <Bell size={18} />
        </button>
      </div>
    </header>
  );
}
