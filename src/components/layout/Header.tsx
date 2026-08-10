import { useLocation } from "react-router-dom";
import { Bell, Calendar, RefreshCw } from "lucide-react";
import { useState, useEffect } from "react";

export default function Header() {
  const location = useLocation();
  const [lastUpdate, setLastUpdate] = useState("");

  useEffect(() => {
    const now = new Date();
    setLastUpdate(now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }));
  }, [location]);

  const getBreadcrumb = () => {
    const path = location.pathname;
    if (path === "/") return "Overview / Dashboard";
    if (path === "/employees") return "Management / Employees";
    if (path === "/attendance") return "Management / Attendance";
    if (path === "/leave") return "Management / Leave";
    if (path === "/training") return "Management / Training";
    if (path === "/upload") return "Operations / Upload";
    if (path === "/admin") return "Operations / Admin";
    if (path === "/reports") return "Analytics / Reports";
    if (path === "/settings") return "System / Settings";
    if (path === "/rules-settings") return "System / Rules Settings";
    return path.replace("/", "").charAt(0).toUpperCase() + path.slice(2);
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <header className="h-[56px] flex-shrink-0 bg-surface border-b border-divider px-6 flex items-center justify-between">
      <div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">{getBreadcrumb()}</span>
        </div>
        <h1 className="text-sm font-semibold text-text-primary leading-5">
          {getGreeting()}, Admin <span className="ml-1">👋</span>
        </h1>
      </div>

      <div className="flex items-center gap-3 text-xs text-text-muted">
        <RefreshCw size={12} />
        <span>Updated {lastUpdate}</span>
        <div className="w-px h-4 bg-divider" />
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-btn border border-border text-text-secondary hover:bg-nav-hover transition-colors text-xs">
          <Calendar size={14} />
          <span>Today</span>
        </button>
        <button className="w-8 h-8 rounded-btn border border-border flex items-center justify-center text-text-muted hover:bg-nav-hover hover:text-text-secondary transition-colors">
          <Bell size={16} />
        </button>
      </div>
    </header>
  );
}
