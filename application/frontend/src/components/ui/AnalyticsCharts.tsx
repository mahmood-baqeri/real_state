"use client";

import React from "react";
import { formatNumberFa } from "@/lib/formatters";

export interface ChartDatum {
  label: string;
  value: number;
  secondary?: string;
}

export function HorizontalBarChart({
  title,
  subtitle,
  items,
  unitLabel = "",
  barColorClass = "bg-teal-700 dark:bg-teal-500",
}: {
  title: string;
  subtitle?: string;
  items: ChartDatum[];
  unitLabel?: string;
  barColorClass?: string;
}) {
  const maxVal = Math.max(1, ...items.map((i) => i.value));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {items.length === 0 ? (
        <p className="py-6 text-center text-xs text-slate-500 dark:text-slate-400">
          داده‌ای برای نمایش وجود ندارد.
        </p>
      ) : (
        <div className="space-y-3.5">
          {items.map((item, idx) => {
            const pct = Math.max(4, Math.round((item.value / maxVal) * 100));
            return (
              <div key={idx} className="space-y-1.5">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {item.label}
                  </span>
                  <span className="tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                    {formatNumberFa(item.value)} {unitLabel}
                    {item.secondary ? ` (${item.secondary})` : ""}
                  </span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded bg-slate-100 dark:bg-slate-800">
                  <div
                    className={`h-full rounded ${barColorClass} transition-all duration-300`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function DonutBreakdownChart({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle?: string;
  items: { label: string; value: number; color: string }[];
}) {
  const total = items.reduce((acc, i) => acc + i.value, 0);
  const radius = 52;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {total === 0 ? (
        <p className="py-6 text-center text-xs text-slate-500 dark:text-slate-400">
          داده‌ای برای نمایش وجود ندارد.
        </p>
      ) : (
        <div className="flex flex-col items-center gap-6 sm:flex-row">
          <div className="relative h-36 w-36 shrink-0">
            <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
              <circle
                cx="70"
                cy="70"
                r={radius}
                fill="none"
                stroke="var(--border-hairline)"
                strokeWidth="16"
              />
              {items.map((item, i) => {
                const dash = (item.value / total) * circumference;
                const seg = (
                  <circle
                    key={i}
                    cx="70"
                    cy="70"
                    r={radius}
                    fill="none"
                    stroke={item.color}
                    strokeWidth="16"
                    strokeDasharray={`${dash} ${circumference - dash}`}
                    strokeDashoffset={-offset}
                  />
                );
                offset += dash;
                return seg;
              })}
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="tabular-nums text-lg font-bold text-slate-900 dark:text-slate-100">
                {formatNumberFa(total)}
              </span>
              <span className="text-[11px] text-slate-500 dark:text-slate-400">مجموع</span>
            </div>
          </div>

          <div className="w-full flex-1 space-y-2.5">
            {items.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-sm"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    {item.label}
                  </span>
                </div>
                <span className="tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                  {formatNumberFa(item.value)} (
                  {formatNumberFa(Math.round((item.value / total) * 100))}٪)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
