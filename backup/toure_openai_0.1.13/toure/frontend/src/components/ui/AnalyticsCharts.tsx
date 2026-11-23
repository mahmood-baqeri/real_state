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

export interface TrendPoint {
  label: string;
  primary: number;
  secondary?: number;
}

export function TrendLineChart({
  title,
  subtitle,
  points,
  primaryLabel = "روند اصلی",
  secondaryLabel,
  valueFormatter = (v: number) => formatNumberFa(Math.round(v)),
}: {
  title: string;
  subtitle?: string;
  points: TrendPoint[];
  primaryLabel?: string;
  secondaryLabel?: string;
  valueFormatter?: (v: number) => string;
}) {
  const width = 560;
  const height = 210;
  const padX = 28;
  const padTop = 20;
  const padBottom = 34;
  const plotW = width - padX * 2;
  const plotH = height - padTop - padBottom;

  const allVals = points.flatMap((p) =>
    typeof p.secondary === "number" ? [p.primary, p.secondary] : [p.primary]
  );
  const maxVal = Math.max(1, ...allVals);
  const minVal = Math.min(0, ...allVals);
  const span = Math.max(1, maxVal - minVal);

  const getCoords = (idx: number, val: number) => {
    const x =
      points.length <= 1
        ? padX + plotW / 2
        : padX + (idx / (points.length - 1)) * plotW;
    const y = padTop + plotH - ((val - minVal) / span) * plotH;
    return { x, y };
  };

  const primaryCoords = points.map((p, i) => getCoords(i, p.primary));
  const primaryLine = primaryCoords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");
  const primaryArea =
    primaryCoords.length > 0
      ? `${primaryLine} L ${primaryCoords[primaryCoords.length - 1].x.toFixed(1)} ${(
          padTop + plotH
        ).toFixed(1)} L ${primaryCoords[0].x.toFixed(1)} ${(padTop + plotH).toFixed(1)} Z`
      : "";

  const hasSecondary = Boolean(secondaryLabel) && points.some((p) => typeof p.secondary === "number");
  const secondaryCoords = hasSecondary
    ? points.map((p, i) => getCoords(i, p.secondary ?? 0))
    : [];
  const secondaryLine = secondaryCoords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
            <span className="h-2.5 w-2.5 rounded-sm bg-teal-600 dark:bg-teal-400" />
            {primaryLabel}
          </span>
          {hasSecondary && secondaryLabel && (
            <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
              <span className="h-2.5 w-2.5 rounded-sm bg-amber-600 dark:bg-amber-400" />
              {secondaryLabel}
            </span>
          )}
        </div>
      </div>

      {points.length === 0 ? (
        <p className="py-10 text-center text-xs text-slate-500 dark:text-slate-400">
          داده‌ای برای رسم نمودار روند ثبت نشده است.
        </p>
      ) : (
        <div className="space-y-3">
          <svg viewBox={`0 0 ${width} ${height}`} className="h-52 w-full overflow-visible">
            {[0, 0.25, 0.5, 0.75, 1].map((t, i) => {
              const y = padTop + plotH * (1 - t);
              return (
                <line
                  key={i}
                  x1={padX}
                  x2={width - padX}
                  y1={y}
                  y2={y}
                  stroke="currentColor"
                  strokeDasharray="3 3"
                  className="text-slate-200 dark:text-slate-800"
                />
              );
            })}

            {primaryArea && (
              <path
                d={primaryArea}
                fill="currentColor"
                className="text-teal-500/12 dark:text-teal-400/15"
              />
            )}
            {primaryLine && (
              <path
                d={primaryLine}
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-teal-700 dark:text-teal-400"
              />
            )}
            {secondaryLine && (
              <path
                d={secondaryLine}
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeDasharray="5 4"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-amber-600 dark:text-amber-400"
              />
            )}

            {primaryCoords.map((c, idx) => (
              <g key={idx}>
                <circle
                  cx={c.x}
                  cy={c.y}
                  r="4"
                  className="fill-white stroke-teal-700 dark:fill-slate-900 dark:stroke-teal-400"
                  strokeWidth="2"
                />
                <text
                  x={c.x}
                  y={height - 10}
                  textAnchor="middle"
                  className="fill-slate-500 text-[11px] dark:fill-slate-400"
                >
                  {points[idx].label}
                </text>
              </g>
            ))}

            {secondaryCoords.map((c, idx) => (
              <circle
                key={`sec-${idx}`}
                cx={c.x}
                cy={c.y}
                r="3.5"
                className="fill-white stroke-amber-600 dark:fill-slate-900 dark:stroke-amber-400"
                strokeWidth="2"
              />
            ))}
          </svg>

          <div className="grid grid-cols-2 gap-2 border-t border-slate-100 pt-3 text-xs dark:border-slate-800 sm:grid-cols-3 lg:grid-cols-6">
            {points.map((p, idx) => (
              <div
                key={idx}
                className="rounded-lg bg-slate-50 px-2.5 py-2 dark:bg-slate-800/60"
              >
                <div className="text-[11px] text-slate-500 dark:text-slate-400">{p.label}</div>
                <div className="mt-0.5 tabular-nums font-bold text-slate-900 dark:text-slate-100">
                  {valueFormatter(p.primary)}
                </div>
                {typeof p.secondary === "number" && (
                  <div className="tabular-nums text-[11px] text-amber-700 dark:text-amber-400">
                    {valueFormatter(p.secondary)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function SalesFunnelChart({
  title,
  subtitle,
  stages,
}: {
  title: string;
  subtitle?: string;
  stages: { stage: string; count: number }[];
}) {
  const top = Math.max(1, stages[0]?.count || 1);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {stages.length === 0 ? (
        <p className="py-6 text-center text-xs text-slate-500 dark:text-slate-400">
          داده‌ای برای قیف فروش ثبت نشده است.
        </p>
      ) : (
        <div className="space-y-3">
          {stages.map((item, idx) => {
            const pctFromTop = Math.max(8, Math.round((item.count / top) * 100));
            const prev = idx > 0 ? stages[idx - 1].count : item.count;
            const conv = prev > 0 ? Math.round((item.count / prev) * 100) : 0;
            return (
              <div key={item.stage} className="space-y-1.5">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {formatNumberFa(idx + 1)}. {item.stage}
                  </span>
                  <span className="tabular-nums text-slate-600 dark:text-slate-400">
                    <strong className="font-bold text-slate-900 dark:text-slate-100">
                      {formatNumberFa(item.count)}
                    </strong>{" "}
                    مورد
                    {idx > 0 && ` · تبدیل ${formatNumberFa(conv)}٪`}
                  </span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-md bg-slate-100 dark:bg-slate-800">
                  <div
                    className="h-full rounded-md bg-teal-700 transition-all duration-300 dark:bg-teal-500"
                    style={{ width: `${Math.min(100, pctFromTop)}%` }}
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

export function ActivityHeatmapGrid({
  title,
  subtitle,
  rows,
}: {
  title: string;
  subtitle?: string;
  rows: { day: string; slots: { slot: string; count: number }[] }[];
}) {
  const maxVal = Math.max(
    1,
    ...rows.flatMap((r) => r.slots.map((s) => s.count))
  );
  const slotLabels = rows[0]?.slots.map((s) => s.slot) || ["صبح", "ظهر", "عصر"];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {rows.length === 0 ? (
        <p className="py-6 text-center text-xs text-slate-500 dark:text-slate-400">
          داده‌ای برای نقشه حرارتی بازدیدها وجود ندارد.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-right text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <th className="py-2 pl-3 font-medium">روز هفته</th>
                {slotLabels.map((s) => (
                  <th key={s} className="px-2 py-2 text-center font-medium">
                    {s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {rows.map((r) => (
                <tr key={r.day}>
                  <td className="py-2 pl-3 font-medium text-slate-800 dark:text-slate-200">
                    {r.day}
                  </td>
                  {r.slots.map((s) => {
                    const ratio = s.count / maxVal;
                    const cellTone =
                      s.count === 0
                        ? "bg-slate-100 text-slate-500 dark:bg-slate-800/70 dark:text-slate-400"
                        : ratio >= 0.7
                        ? "bg-teal-700 text-white dark:bg-teal-500 dark:text-slate-950"
                        : ratio >= 0.35
                        ? "bg-teal-500/80 text-white dark:bg-teal-700 dark:text-teal-50"
                        : "bg-teal-100 text-teal-900 dark:bg-teal-950 dark:text-teal-300";
                    return (
                      <td key={s.slot} className="px-1.5 py-1.5 text-center">
                        <div
                          className={`mx-auto flex h-8 items-center justify-center rounded-md font-semibold tabular-nums ${cellTone}`}
                        >
                          {formatNumberFa(s.count)}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
