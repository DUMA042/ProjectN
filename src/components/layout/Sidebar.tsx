import { useState } from "react";
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
  BarChart3,
  TrendingUp,
  Building2,
  ChevronDown,
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
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({
    Reports: true,
  });

  const toggleGroup = (label: string) => {
    setCollapsed((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const isActive = (path: string) => location.pathname === path;
  const isGroupActive = (group: NavGroup) =>
    group.items.some((item) => location.pathname.startsWith(item.path));

  const groups: NavGroup[] = [
    {
      label: "Main",
      items: [
        { icon: <LayoutDashboard size={20} />, label: "Dashboard", path: "/" },
      ],
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
      items: [
        { icon: <Settings size={20} />, label: "Settings", path: "/settings" },
      ],
    },
  ];

  return (
    <aside className="w-[240px] flex-shrink-0 bg-surface border-r border-border flex flex-col h-full">
      {/* Branding */}
      <div className="px-5 py-5 border-b border-divider">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
            <span className="text-white font-bold text-sm">F</span>
          </div>
          <span className="text-lg font-bold text-text-primary tracking-tight">
            Flow
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-4">
        {groups.map((group) => (
          <div key={group.label}>
            {/* Group header */}
            <div
              className={`flex items-center justify-between px-2 mb-1 cursor-pointer ${
                group.collapsed !== undefined
                  ? "hover:bg-nav-hover rounded-btn py-1"
                  : ""
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
                    collapsed[group.label] ? "" : "rotate-180"
                  }`}
                />
              )}
            </div>

            {/* Group items */}
            <div
              className={`space-y-0.5 overflow-hidden transition-all duration-200 ${
                group.collapsed !== undefined && collapsed[group.label]
                  ? "max-h-0 opacity-0"
                  : "max-h-96 opacity-100"
              }`}
            >
              {group.items.map((item) => (
                <NavItem
                  key={item.path}
                  icon={item.icon}
                  label={item.label}
                  active={isActive(item.path)}
                  onClick={() => navigate(item.path)}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
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
    </aside>
  );
}
