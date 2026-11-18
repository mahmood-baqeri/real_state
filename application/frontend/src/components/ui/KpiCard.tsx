import React from "react";

interface KpiCardProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
  icon?: React.ReactNode;
  tone?: "default" | "teal" | "amber" | "emerald" | "rose";
}

export function KpiCard({ label, value, hint, icon, tone = "default" }: KpiCardProps) {
  const iconTone =
    tone === "teal"
      ? "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-950/60 dark:text-teal-300 dark:border-teal-800/80"
      : tone === "amber"
      ? "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/80"
      : tone === "emerald"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/80"
      : tone === "rose"
      ? "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/80"
      : "bg-slate-50 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";

  return (
    <div className="min-w-0 rounded-xl border border-slate-200 bg-white p-5 transition-colors hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
        {icon && (
          <div
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${iconTone}`}
          >
            {icon}
          </div>
        )}
      </div>
      <div className="mt-2.5 min-w-0 tabular-nums text-lg font-bold leading-snug tracking-tight text-slate-900 dark:text-slate-100 sm:text-xl">
        {value}
      </div>
      {hint && <p className="mt-2 truncate text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  );
}
