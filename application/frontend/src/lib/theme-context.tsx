"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  isThemePreference,
  resolveTheme,
  THEME_STORAGE_KEY,
  type ResolvedTheme,
  type ThemePreference,
} from "./theme-utils";

interface ThemeContextValue {
  preference: ThemePreference;
  resolvedTheme: ResolvedTheme;
  setPreference: (next: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyDocumentTheme(resolved: ResolvedTheme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (resolved === "dark") {
    root.classList.add("dark");
    root.style.colorScheme = "dark";
  } else {
    root.classList.remove("dark");
    root.style.colorScheme = "light";
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>("system");
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemPrefersDark(mq.matches);

    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      if (isThemePreference(saved)) {
        setPreferenceState(saved);
        applyDocumentTheme(resolveTheme(saved, mq.matches));
      } else {
        applyDocumentTheme(resolveTheme("system", mq.matches));
      }
    } catch {
      applyDocumentTheme(resolveTheme("system", mq.matches));
    }

    const onChange = (e: MediaQueryListEvent) => {
      setSystemPrefersDark(e.matches);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const resolvedTheme = useMemo(
    () => resolveTheme(preference, systemPrefersDark),
    [preference, systemPrefersDark]
  );

  useEffect(() => {
    applyDocumentTheme(resolvedTheme);
  }, [resolvedTheme]);

  const setPreference = useCallback(
    (next: ThemePreference) => {
      setPreferenceState(next);
      try {
        localStorage.setItem(THEME_STORAGE_KEY, next);
      } catch {
        // ignore storage quota errors
      }
      applyDocumentTheme(resolveTheme(next, systemPrefersDark));
    },
    [systemPrefersDark]
  );

  const value = useMemo(
    () => ({ preference, resolvedTheme, setPreference }),
    [preference, resolvedTheme, setPreference]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
