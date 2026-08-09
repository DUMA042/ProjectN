import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Clock,
  Umbrella,
  GraduationCap,
  Upload,
  Settings,
  Shield,
  TrendingUp,
  Building2,
  ChevronDown,
  PanelLeftClose,
  PanelLeft,
  Wrench,
} from "lucide-react";
import NavItem from "../ui/NavItem";

interface NavGroup {
  label: string;
  items: {
    icon: React.ReactNode;
    label: string;
    path: string;
  }[];
  collapsed?: boolean;
}

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem("sidebarCollapsed") === "true";
  });
  const [groupCollapsed, setGroupCollapsed] = useState<Record<string, boolean>>({
    Reports: true,
  });

  useEffect(() => {
    localStorage.setItem("sidebarCollapsed", String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  const toggleGroup = (label: string) => {
    if (sidebarCollapsed) return;
    setGroupCollapsed((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const isActive = (path: string) => location.pathname === path;

  const groups: NavGroup[] = [
    {
      label: "Main",
      items: [{ icon: <LayoutDashboard size={20} />, label: "Dashboard", path: "/" }],
    },
    {
      label: "Management",
      items: [
        { icon: <Users size={20} />, label: "Employees", path: "/employees" },
        { icon: <Clock size={20} />, label: "Attendance", path: "/attendance" },
        { icon: <Umbrella size={20} />, label: "Leave", path: "/leave" },
        { icon: <GraduationCap size={20} />, label: "Training", path: "/training" },
      ],
    },
    {
      label: "Operations",
      items: [
        { icon: <Upload size={20} />, label: "Upload", path: "/upload" },
        { icon: <Shield size={20} />, label: "Admin", path: "/admin" },
      ],
    },
    {
      label: "Reports",
      collapsed: true,
      items: [
        { icon: <TrendingUp size={18} />, label: "Trends", path: "/reports/trends" },
        { icon: <Building2 size={18} />, label: "Dept Metrics", path: "/reports/dept" },
      ],
    },
    {
      label: "System",
      collapsed: true,
      items: [
        { icon: <Settings size={18} />, label: "System Settings", path: "/settings" },
        { icon: <Wrench size={18} />, label: "Rules Settings", path: "/rules-settings" },
      ],
    },
  ];

  return (
    <aside
      className={`${
        sidebarCollapsed ? "w-[64px]" : "w-[240px]"
      } flex-shrink-0 bg-surface border-r border-border flex flex-col h-full transition-[width] duration-200`}
    >
      {/* Branding + Toggle */}
      <div className={`px-4 py-4 border-b border-divider flex items-center ${sidebarCollapsed ? "justify-center" : "justify-between"}`}>
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <span className="text-white font-bold text-sm">F</span>
            </div>
            <span className="text-lg font-bold text-text-primary tracking-tight">Flow</span>
          </div>
        )}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="p-1.5 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary transition-colors"
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-4">
        {groups.map((group) => (
          <div key={group.label}>
            {!sidebarCollapsed && (
              <div
                className={`flex items-center justify-between px-2 mb-1 cursor-pointer ${
                  group.collapsed !== undefined ? "hover:bg-nav-hover rounded-btn py-1" : ""
                }`}
                onClick={() => group.collapsed !== undefined && toggleGroup(group.label)}
              >
                <span className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  {group.label}
                </span>
                {group.collapsed !== undefined && (
                  <ChevronDown
                    size={14}
                    className={`text-text-muted transition-transform duration-200 ${
                      groupCollapsed[group.label] ? "" : "rotate-180"
                    }`}
                  />
                )}
              </div>
            )}

            <div
              className={`space-y-0.5 overflow-hidden transition-all duration-200 ${
                group.collapsed !== undefined && groupCollapsed[group.label] && !sidebarCollapsed
                  ? "max-h-0 opacity-0"
                  : "max-h-96 opacity-100"
              }`}
            >
              {group.items.map((item) => (
                <NavItem
                  key={item.path}
                  icon={item.icon}
                  label={sidebarCollapsed ? "" : item.label}
                  active={isActive(item.path)}
                  onClick={() => navigate(item.path)}
                  compact={sidebarCollapsed}
                  tooltip={sidebarCollapsed ? item.label : undefined}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      {!sidebarCollapsed && (
        <div className="px-4 py-3 border-t border-divider">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-info flex items-center justify-center">
              <span className="text-white text-xs font-semibold">A</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">Admin</p>
              <p className="text-xs text-text-secondary">HR Manager</p>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
