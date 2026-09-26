import { motion } from "framer-motion";
import { ReactNode } from "react";

const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Parent that staggers its RevealItem children on mount. */
export default function StaggerReveal({ children, className = "" }: { children: ReactNode; className?: string }) {
  if (reduced) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: 0.045 } } }}
    >
      {children}
    </motion.div>
  );
}

/** Child of StaggerReveal — fades in with a small rise. */
export function RevealItem({ children, className = "" }: { children: ReactNode; className?: string }) {
  if (reduced) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { opacity: 0, y: 8 },
        show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: "easeOut" } },
      }}
    >
      {children}
    </motion.div>
  );
}
