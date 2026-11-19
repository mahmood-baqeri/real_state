// Path: frontend/src/components/ui/ThemeToggle.tsx

"use client";

import React from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme-context";
import {
  nextThemePreference,
  THEME_LABELS_FA,
  type ThemePreference,
} from "@/lib/theme-utils";

interface ThemeToggleProps {
  variant?: "segmented" | "compact";
}

const OPTIONS: { value: ThemePreference; label: string; Icon: React.ComponentType<{ className?: string }> }[] = [
  { value: "light", label: "روز", Icon: Sun },
  { value: "dark", label: "شب", Icon: Moon },
  { value: "system", label: "سیستم", Icon: Monitor },
];

export function ThemeToggle({ variant = "segmented" }: ThemeToggleProps) {
  const { preference, resolvedTheme, setPreference } = useTheme();

  if (variant === "compact") {
    const nextPref = nextThemePreference(preference);
    const ActiveIcon =
      preference === "system"
        ? Monitor
        : resolvedTheme === "dark"
        ? Moon
        : Sun;

    return (
      <button
        type="button"
        onClick={() => setPreference(nextPref)}
        title={`حالت نمایش: ${THEME_LABELS_FA[preference]} — کلیک برای تغییر`}
        aria-label={`تغییر تم نمایش (فعلی: ${THEME_LABELS_FA[preference]})`}
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 transition-colors"
      >
        <ActiveIcon className="h-4 w-4" />
      </button>
    );
  }

  return (
    <div
      role="group"
      aria-label="انتخاب تم روشنایی"
      className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5 dark:border-slate-700 dark:bg-slate-800/80"
    >
      {OPTIONS.map(({ value, label, Icon }) => {
        const active = preference === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setPreference(value)}
            aria-pressed={active}
            title={THEME_LABELS_FA[value]}
            className={`inline-flex h-7 items-center gap-1 whitespace-nowrap rounded-md px-2 text-[11px] font-semibold transition-colors ${
              active
                ? "bg-white text-teal-800 shadow-xs dark:bg-slate-900 dark:text-teal-300"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            <span className="hidden xl:inline">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
