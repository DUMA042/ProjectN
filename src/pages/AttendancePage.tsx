import { motion } from "framer-motion";
import { Clock, Users, TrendingUp } from "lucide-react";

export default function AttendancePage() {
  return (
    <motion.div className="p-6 space-y-5" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Attendance & Swipes</h1>
        <p className="text-sm text-text-secondary mt-0.5">Card swipe records and attendance analysis</p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: Clock, title: "Card Swipe Records", desc: "View and analyze employee swipe data by day, hour, and location" },
          { icon: Users, title: "Attendance Tracking", desc: "Monitor attendance patterns across departments" },
          { icon: TrendingUp, title: "Analytics", desc: "Trend analysis and workforce attendance reports" },
        ].map((card) => (
          <div key={card.title} className="card-container rounded-card p-5">
            <card.icon size={28} className="text-accent mb-3" strokeWidth={1.5} />
            <h3 className="text-sm font-semibold text-text-primary mb-1">{card.title}</h3>
            <p className="text-xs text-text-secondary">{card.desc}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
