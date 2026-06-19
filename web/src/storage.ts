// Tiny typed localStorage-backed state hook for view preferences (page size,
// density, saved views). Safe in private-mode / SSR (falls back to in-memory).

import { useEffect, useState } from "react";

export function useStored<T>(key: string, initial: T): [T, (v: T | ((p: T) => T)) => void] {
  const [val, setVal] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw == null ? initial : (JSON.parse(raw) as T);
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(val));
    } catch {
      /* ignore */
    }
  }, [key, val]);

  return [val, setVal];
}
