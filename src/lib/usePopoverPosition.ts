import { useCallback, useEffect, useRef, useState } from "react";

export function usePopoverPosition(
  triggerRef: React.RefObject<HTMLElement>,
  popoverRef: React.RefObject<HTMLElement>,
  open: boolean
): boolean {
  // Placement side is decided once per open and held: later scrolls only
  // follow the trigger, never flip above↔below mid-interaction.
  const sideRef = useRef<"above" | "below" | null>(null);
  const [positioned, setPositioned] = useState(false);

  const position = useCallback(() => {
    const trigger = triggerRef.current;
    const pop = popoverRef.current;
    if (!trigger || !pop) return;

    const btn = trigger.getBoundingClientRect();
    const pw = pop.offsetWidth || 260;
    const ph = pop.offsetHeight || 320;
    const pad = 8;
    const vh70 = window.innerHeight * 0.7;

    // Horizontal: align to trigger left, clamp to viewport
    let left = btn.left;
    left = Math.max(pad, Math.min(left, window.innerWidth - pw - pad));
    pop.style.left = `${left}px`;
    pop.style.right = "auto";

    // Vertical: upward if not enough space below (locked per open)
    const spaceBelow = window.innerHeight - btn.bottom;
    if (!sideRef.current) {
      sideRef.current = spaceBelow < ph + pad ? "above" : "below";
      setPositioned(true);
    }
    if (sideRef.current === "above") {
      pop.style.top = "auto";
      pop.style.bottom = `${window.innerHeight - btn.top + 4}px`;
      pop.style.maxHeight = `${Math.min(vh70, btn.top - 16)}px`;
      pop.style.overflowY = "auto";
    } else {
      pop.style.top = `${btn.bottom + 4}px`;
      pop.style.bottom = "auto";
      pop.style.maxHeight = `${Math.min(vh70, window.innerHeight - btn.bottom - 16)}px`;
      pop.style.overflowY = "auto";
    }
  }, [triggerRef, popoverRef]);

  useEffect(() => {
    if (!open) return;
    sideRef.current = null;
    setPositioned(false);
    const id = requestAnimationFrame(position);
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    return () => {
      cancelAnimationFrame(id);
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
    };
  }, [open, position]);

  return positioned;
}
