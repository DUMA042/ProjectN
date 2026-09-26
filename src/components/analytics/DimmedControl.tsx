import { ReactNode } from "react";

interface DimmedControlProps {
  children: ReactNode;
  /** Shown on hover — what the control does and where it applies. */
  reason: string;
  className?: string;
}

/** Wraps a control that does not affect the current view: dims it, blocks
 * interaction, and explains on hover what it does and where to use it. */
export default function DimmedControl({ children, reason, className = "" }: DimmedControlProps) {
  return (
    <span className={`relative inline-flex group/dim ${className}`}>
      <span className="opacity-40 pointer-events-none select-none">{children}</span>
      <span className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full mt-1.5 z-40 hidden group-hover/dim:block whitespace-nowrap bg-text-primary text-white text-[11px] px-2.5 py-1.5 rounded-btn shadow-lg">
        {reason}
      </span>
    </span>
  );
}
