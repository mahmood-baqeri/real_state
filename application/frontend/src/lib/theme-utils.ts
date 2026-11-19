// Path: frontend/src/lib/theme-utils.ts

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "bonyan-theme";

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

export function resolveTheme(
  preference: ThemePreference,
  systemPrefersDark: boolean
): ResolvedTheme {
  if (preference === "dark") return "dark";
  if (preference === "light") return "light";
  return systemPrefersDark ? "dark" : "light";
}

export function nextThemePreference(current: ThemePreference): ThemePreference {
  if (current === "light") return "dark";
  if (current === "dark") return "system";
  return "light";
}

export const THEME_LABELS_FA: Record<ThemePreference, string> = {
  light: "روز (روشن)",
  dark: "شب (تیره)",
  system: "خودکار (سیستم)",
};
