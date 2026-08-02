import { motion } from "framer-motion";
import { BarChart3 } from "lucide-react";
export default function ReportsPage() { return (<motion.div className="flex items-center justify-center h-full" initial={{ opacity: 0 }} animate={{ opacity: 1 }}><div className="text-center"><div className="w-16 h-16 rounded-2xl bg-nav-hover flex items-center justify-center mx-auto mb-4"><BarChart3 size={28} className="text-text-muted" /></div><h2 className="text-lg font-semibold text-text-primary">Analytics & Reports</h2><p className="text-sm text-text-secondary mt-1">Coming soon</p></div></motion.div>); }
