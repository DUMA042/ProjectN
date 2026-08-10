import { motion } from "framer-motion";
import { GraduationCap, Building2, Users } from "lucide-react";
export default function TrainingPage() {
  return (
    <motion.div className="p-6 space-y-5" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <div><h1 className="text-xl font-semibold text-text-primary">Training & Seminars</h1><p className="text-sm text-text-secondary mt-0.5">Employee training records and distribution</p></div>
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: GraduationCap, title: "Training Records", desc: "View training history by employee" },
          { icon: Building2, title: "Venues", desc: "Training distribution by venue and consultant" },
          { icon: Users, title: "Participants", desc: "Staff participation and training coverage" },
        ].map(c => (
          <div key={c.title} className="card-container rounded-card p-5"><c.icon size={28} className="text-info mb-3" strokeWidth={1.5} /><h3 className="text-sm font-semibold text-text-primary mb-1">{c.title}</h3><p className="text-xs text-text-secondary">{c.desc}</p></div>
        ))}
      </div>
    </motion.div>
  );
}
