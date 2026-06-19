// Theme management: LIGHT is the default. Initial theme follows the OS
// preference (prefers-color-scheme), but an explicit user choice is persisted
// in localStorage and always wins. The active theme is reflected on
// document.documentElement.dataset.theme, which every CSS token set keys off.

import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

const KEY = "drawback-theme";

/** Read the persisted explicit choice, if any. */
function stored(): Theme | null {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null;
  }
}

/** The theme to use on first paint: explicit choice → OS pref → light. */
export function initialTheme(): Theme {
  const s = stored();
  if (s) return s;
  try {
    if (window.matchMedia?.("(prefers-color-scheme: dark)").matches) return "dark";
  } catch {
    /* default below */
  }
  return "light";
}

/** Apply a theme to the document root. */
export function applyTheme(t: Theme): void {
  document.documentElement.dataset.theme = t;
}

/**
 * Theme state hook. Persists explicit toggles; if the user has NOT made an
 * explicit choice, it live-follows the OS preference.
 */
export function useTheme(): { theme: Theme; toggle: () => void; setTheme: (t: Theme) => void } {
  const [theme, setThemeState] = useState<Theme>(() => initialTheme());

  // keep <html data-theme> in sync
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // follow OS changes only while no explicit choice is stored
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return;
    const onChange = (e: MediaQueryListEvent) => {
      if (!stored()) setThemeState(e.matches ? "dark" : "light");
    };
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, []);

  function setTheme(t: Theme) {
    try {
      localStorage.setItem(KEY, t);
    } catch {
      /* non-persistent is fine */
    }
    setThemeState(t);
  }

  return { theme, toggle: () => setTheme(theme === "dark" ? "light" : "dark"), setTheme };
}
