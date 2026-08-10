import { motion } from "framer-motion";
import { Umbrella, Calendar, BarChart3 } from "lucide-react";
export default function LeavePage() {
  return (
    <motion.div className="p-6 space-y-5" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <div><h1 className="text-xl font-semibold text-text-primary">Leave Management</h1><p className="text-sm text-text-secondary mt-0.5">Leave records, types, and trends</p></div>
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: Umbrella, title: "Leave Records", desc: "Browse approved leave applications and records" },
          { icon: Calendar, title: "Leave Calendar", desc: "View leave distribution across months" },
          { icon: BarChart3, title: "Leave Analytics", desc: "Breakdown by type, department, and trends" },
        ].map(c => (
          <div key={c.title} className="card-container rounded-card p-5"><c.icon size={28} className="text-warning mb-3" strokeWidth={1.5} /><h3 className="text-sm font-semibold text-text-primary mb-1">{c.title}</h3><p className="text-xs text-text-secondary">{c.desc}</p></div>
        ))}
      </div>
    </motion.div>
  );
}
