"use client";

import React from "react";
import { BarChart3, Box, Compass, Layers, MousePointerClick, Smartphone, Users } from "lucide-react";
import { formatNumberFa } from "@/lib/formatters";
import type { TourAnalyticsSummary } from "@/lib/types";

interface TourAnalyticsPanelProps {
  analytics: TourAnalyticsSummary;
}

const DEVICE_LABELS_FA: Record<string, string> = {
  desktop: "رایانه رومیزی (Desktop)",
  mobile: "گوشی هوشمند (Mobile)",
  tablet: "تبلت",
  unknown: "نامشخص",
};

export function TourAnalyticsPanel({ analytics }: TourAnalyticsPanelProps) {
  const maxSceneVisits = Math.max(
    1,
    ...(analytics.popular_scenes || []).map((s) => s.visits)
  );
  const totalDevices = Math.max(
    1,
    (analytics.device_breakdown || []).reduce((acc, d) => acc + d.count, 0)
  );

  return (
    <div className="space-y-6">
      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        <div className="rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>بازدید کل تور</span>
            <Compass className="h-3.5 w-3.5 text-slate-400" />
          </div>
          <div className="mt-1.5 text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100">
            {formatNumberFa(analytics.total_views)}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>بازدیدکننده یکتا</span>
            <Users className="h-3.5 w-3.5 text-slate-400" />
          </div>
          <div className="mt-1.5 text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100">
            {formatNumberFa(analytics.unique_visitors)}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <div className="text-[11px] text-slate-500">نرخ تکمیل تور</div>
          <div className="mt-1.5 text-lg font-bold tabular-nums text-teal-700 dark:text-teal-400">
            {formatNumberFa(analytics.completion_rate_percent)}٪
          </div>
          <div className="mt-0.5 text-[10px] tabular-nums text-slate-400">
            {formatNumberFa(analytics.completed_sessions)} از {formatNumberFa(analytics.total_sessions)} نشست
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <div className="text-[11px] text-slate-500">میانگین ماندگاری</div>
          <div className="mt-1.5 text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100">
            {formatNumberFa(analytics.avg_duration_seconds)} <span className="text-xs font-normal">ثانیه</span>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>کلیک نقاط تعاملی</span>
            <MousePointerClick className="h-3.5 w-3.5 text-amber-600" />
          </div>
          <div className="mt-1.5 text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100">
            {formatNumberFa(analytics.hotspot_clicks)}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>نمایش سه‌بعدی Dollhouse</span>
            <Box className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
          </div>
          <div className="mt-1.5 text-lg font-bold tabular-nums text-teal-700 dark:text-teal-400">
            {formatNumberFa(analytics.dollhouse_opens)}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>باز شدن نقشه پلان</span>
            <Layers className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div className="mt-1.5 text-lg font-bold tabular-nums text-indigo-700 dark:text-indigo-400">
            {formatNumberFa(analytics.floorplan_opens)}
          </div>
        </div>
      </div>

      {/* Breakdowns */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Popular Scenes */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
          <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
            <BarChart3 className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            پربازدیدترین اتاق‌ها و فضاها
          </h3>
          {(analytics.popular_scenes || []).length === 0 ? (
            <p className="py-4 text-xs text-slate-500">
              هنوز ترافیک تفکیک‌شده‌ای برای اتاق‌ها ثبت نشده است.
            </p>
          ) : (
            <div className="space-y-3">
              {analytics.popular_scenes.map((ps) => {
                const pct = Math.round((ps.visits / maxSceneVisits) * 100);
                return (
                  <div key={ps.scene_id} className="space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-800 dark:text-slate-200">{ps.title}</span>
                      <span className="font-bold tabular-nums text-slate-900 dark:text-slate-100">
                        {formatNumberFa(ps.visits)} بازدید
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-full rounded-full bg-teal-700 dark:bg-teal-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Device Breakdown */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
          <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
            <Smartphone className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            تفکیک بازدید بر اساس نوع دستگاه
          </h3>
          {(analytics.device_breakdown || []).length === 0 ? (
            <p className="py-4 text-xs text-slate-500">
              هنوز داده‌ای درباره نوع دستگاه بازدیدکنندگان ثبت نشده است.
            </p>
          ) : (
            <div className="space-y-3">
              {analytics.device_breakdown.map((d) => {
                const pct = Math.round((d.count / totalDevices) * 100);
                return (
                  <div key={d.device_type} className="space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {DEVICE_LABELS_FA[d.device_type] || d.device_type}
                      </span>
                      <span className="font-bold tabular-nums text-slate-900 dark:text-slate-100">
                        {formatNumberFa(d.count)} ({formatNumberFa(pct)}٪)
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-full rounded-full bg-amber-600 dark:bg-amber-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
