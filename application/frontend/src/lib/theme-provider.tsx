"use client";

import React, {
     createContext,
     useCallback,
     useContext,
     useEffect,
     useMemo,
     useState,
} from "react";

export type ThemeMode = "light" | "dark" | "system";
const STORAGE_KEY = "bonyan-theme";

interface ThemeContextValue {
     mode: ThemeMode;
     resolvedTheme: "light" | "dark";
     setMode: (mode: ThemeMode) => void;
     toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemTheme(): "light" | "dark" {
     if (typeof window === "undefined") return "light";
     return window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
}

function resolveTheme(mode: ThemeMode): "light" | "dark" {
     return mode === "system" ? getSystemTheme() : mode;
}

function applyTheme(resolved: "light" | "dark") {
     if (typeof document === "undefined") return;
     const root = document.documentElement;
     root.classList.toggle("dark", resolved === "dark");
     root.style.colorScheme = resolved;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
     const [mode, setModeState] = useState<ThemeMode>("system");
     const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");

     useEffect(() => {
          const stored =
               (localStorage.getItem(STORAGE_KEY) as ThemeMode | null) ?? "system";
          setModeState(stored);
          const resolved = resolveTheme(stored);
          setResolvedTheme(resolved);
          applyTheme(resolved);
     }, []);

     useEffect(() => {
          if (mode !== "system") return;
          const mql = window.matchMedia("(prefers-color-scheme: dark)");
          const handler = () => {
               const resolved = getSystemTheme();
               setResolvedTheme(resolved);
               applyTheme(resolved);
          };
          mql.addEventListener("change", handler);
          return () => mql.removeEventListener("change", handler);
     }, [mode]);

     useEffect(() => {
          const onStorage = (e: StorageEvent) => {
               if (e.key !== STORAGE_KEY) return;
               const next = (e.newValue as ThemeMode | null) ?? "system";
               setModeState(next);
               const resolved = resolveTheme(next);
               setResolvedTheme(resolved);
               applyTheme(resolved);
          };
          window.addEventListener("storage", onStorage);
          return () => window.removeEventListener("storage", onStorage);
     }, []);

     const setMode = useCallback((next: ThemeMode) => {
          setModeState(next);
          localStorage.setItem(STORAGE_KEY, next);
          const resolved = resolveTheme(next);
          setResolvedTheme(resolved);
          applyTheme(resolved);
     }, []);

     const toggle = useCallback(() => {
          setMode(resolvedTheme === "dark" ? "light" : "dark");
     }, [resolvedTheme, setMode]);

     const value = useMemo<ThemeContextValue>(
          () => ({ mode, resolvedTheme, setMode, toggle }),
          [mode, resolvedTheme, setMode, toggle]
     );

     return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
     const ctx = useContext(ThemeContext);
     if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
     return ctx;
}

/** Inline script — runs before paint to prevent theme flash. */
export const THEME_INIT_SCRIPT = `
(function(){
  try {
    var stored = localStorage.getItem("${STORAGE_KEY}");
    var mode = stored || "system";
    var isDark = mode === "dark" || (mode === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
    var root = document.documentElement;
    root.classList.toggle("dark", isDark);
    root.style.colorScheme = isDark ? "dark" : "light";
  } catch (e) {}
})();
`;