import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { X, Clock, Umbrella, GraduationCap } from "lucide-react";
import { api } from "@/lib/api";

interface EmployeeDetail {
  id_no: string;
  full_name: string;
  sex: string;
  department: string;
  rank: string;
  grade_level: string;
  status: string;
  employment_type: string;
  geographical_zone: string;
  date_of_last_deployment: string | null;
  phone_number: string | null;
  remark: string | null;
  card_swipes: { swipe_id: number; swipe_time: string; location: string }[];
  leave_records: { record_id: number; leave_type_name: string; start_date: string; end_date: string }[];
  training_records: { training_id: number; venue: string; consultant: string; start_date: string; end_date: string; title: string | null }[];
}

function useEmployeeDetail(idNo: string | null) {
  return useQuery({
    queryKey: ["employee-detail", idNo],
    queryFn: () => api.get(`/api/employees/${idNo}/detail`).then((r) => r.data as EmployeeDetail),
    enabled: !!idNo,
  });
}

interface EmployeeDetailDrawerProps {
  employeeId: string | null;
  onClose: () => void;
}

export default function EmployeeDetailDrawer({ employeeId, onClose }: EmployeeDetailDrawerProps) {
  const { data: detail, isLoading } = useEmployeeDetail(employeeId);

  return (
    <AnimatePresence>
      {employeeId && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/20 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed right-0 top-0 h-full w-[480px] max-w-[90vw] bg-surface border-l border-border z-50 flex flex-col"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-divider flex-shrink-0">
              <h3 className="text-sm font-semibold text-text-primary">Employee Detail</h3>
              <button onClick={onClose} className="p-1.5 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary">
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5">
              {isLoading ? (
                <div className="space-y-3 animate-pulse">
                  {[...Array(8)].map((_, i) => (
                    <div key={i} className="h-5 bg-nav-hover rounded" />
                  ))}
                </div>
              ) : detail ? (
                <div className="space-y-5">
                  <div>
                    <h4 className="text-base font-semibold text-text-primary">{detail.full_name}</h4>
                    <p className="text-sm text-text-secondary">{detail.id_no}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {[
                      ["Department", detail.department],
                      ["Rank", detail.rank],
                      ["Grade Level", detail.grade_level],
                      ["Status", detail.status],
                      ["Employment Type", detail.employment_type],
                      ["Sex", detail.sex],
                      ["Geo Zone", detail.geographical_zone],
                      ["Phone", detail.phone_number || "—"],
                      ["Last Deployment", detail.date_of_last_deployment || "—"],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="text-xs text-text-muted">{label}</p>
                        <p className="text-text-primary font-medium">{value}</p>
                      </div>
                    ))}
                  </div>

                  {detail.remark && (
                    <div>
                      <p className="text-xs text-text-muted mb-1">Remark</p>
                      <p className="text-sm text-text-secondary bg-nav-hover rounded-input p-2">{detail.remark}</p>
                    </div>
                  )}

                  {detail.card_swipes.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Clock size={14} className="text-accent" />
                        <p className="text-xs font-semibold text-text-secondary uppercase">Recent Swipes</p>
                      </div>
                      <div className="space-y-1">
                        {detail.card_swipes.slice(0, 10).map((s) => (
                          <div key={s.swipe_id} className="flex justify-between text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                            <span className="text-text-secondary">{s.location}</span>
                            <span className="text-text-primary font-mono">
                              {s.swipe_time ? new Date(s.swipe_time).toLocaleString("en-GB") : "—"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {detail.leave_records.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Umbrella size={14} className="text-warning" />
                        <p className="text-xs font-semibold text-text-secondary uppercase">Recent Leave</p>
                      </div>
                      <div className="space-y-1">
                        {detail.leave_records.slice(0, 10).map((l) => (
                          <div key={l.record_id} className="flex justify-between text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                            <span className="text-text-secondary">{l.leave_type_name}</span>
                            <span className="text-text-primary font-mono">{l.start_date} – {l.end_date}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {detail.training_records.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <GraduationCap size={14} className="text-info" />
                        <p className="text-xs font-semibold text-text-secondary uppercase">Recent Training</p>
                      </div>
                      <div className="space-y-1">
                        {detail.training_records.slice(0, 10).map((t) => (
                          <div key={t.training_id} className="text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                            <p className="text-text-primary font-medium">{t.title || "Training"}</p>
                            <p className="text-text-muted">{t.venue} · {t.consultant} · {t.start_date}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-text-muted">Employee not found</p>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
