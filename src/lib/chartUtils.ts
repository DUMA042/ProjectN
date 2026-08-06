import { useState, useCallback } from "react";

export function useClickableLegend(initial: string[] = []) {
  const [hidden, setHidden] = useState<string[]>(initial);

  const toggle = useCallback((key: string) => {
    setHidden((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  }, []);

  const isHidden = useCallback((key: string) => hidden.includes(key), [hidden]);

  return { hidden, toggle, isHidden };
}
