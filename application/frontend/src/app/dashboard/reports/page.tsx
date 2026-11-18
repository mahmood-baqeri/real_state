"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, BarChart3, Building2, Handshake } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { translateStatus } from "@/lib/formatters";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { DonutBreakdownChart, HorizontalBarChart } from "@/components/ui/AnalyticsCharts";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

interface AnalyticsResponse {
  properties_by_status: { status: string; count: number }[];
  deals_by_status: { status: string; count: number; volume: string }[];
  leads_by_status?: { status: string; count: number }[];
  negotiations_count?: number;
  agent_leaderboard: {
    membership_id: string;
    agent_name: string;
    total_commission: string;
    deals_count: number;
  }[];
}

interface PriceTrendItem {
  district: string;
  listing_count: number;
  avg_price_per_sqm: string;
}

const COLORS = ["#0F766E", "#0284C7", "#D97706", "#059669", "#E11D48", "#64748B"];

export default function ReportsPage() {
  const { accessToken, activeAgencyId } = useAuth();

  const analyticsQ = useQuery({
    queryKey: ["reports-analytics", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<AnalyticsResponse>("/api/v1/reports/analytics", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const trendsQ = useQuery({
    queryKey: ["district-trends-report"],
    queryFn: async () =>
      (await apiFetch<PriceTrendItem[]>("/api/v1/matching/analytics/price-trends?city=تهران")).data,
  });

  const data = analyticsQ.data;
  const totalProps = (data?.properties_by_status || []).reduce((acc, i) => acc + i.count, 0);
  const totalDeals = (data?.deals_by_status || []).reduce((acc, i) => acc + i.count, 0);
  const totalDealVolume = (data?.deals_by_status || []).reduce(
    (acc, i) => acc + (Number(i.volume) || 0),
    0
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="گزارش‌ها و تحلیل عملکرد"
        subtitle="تحلیل وضعیت فایل‌های ملکی، قیف سرنخ‌ها، حجم معاملات، میانگین قیمت مناطق و رتبه‌بندی مشاوران"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "گزارش‌ها و تحلیل" }]}
      />

      {analyticsQ.isLoading ? (
        <LoadingState />
      ) : analyticsQ.error instanceof Error ? (
        <ErrorState message={analyticsQ.error.message} onRetry={() => analyticsQ.refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="کل املاک ثبت‌شده"
              value={totalProps}
              icon={<Building2 className="h-5 w-5" />}
              tone="teal"
            />
            <KpiCard
              label="کل معاملات"
              value={totalDeals}
              icon={<Handshake className="h-5 w-5" />}
              tone="emerald"
            />
            <KpiCard
              label="حجم مالی کل معاملات"
              value={<MoneyDisplay amount={totalDealVolume} sourceCurrency="IRT" />}
              icon={<BarChart3 className="h-5 w-5" />}
              tone="amber"
            />
            <KpiCard
              label="مذاکرات ثبت‌شده"
              value={data?.negotiations_count ?? 0}
              icon={<Award className="h-5 w-5" />}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <DonutBreakdownChart
              title="ترکیب املاک بر اساس وضعیت"
              subtitle="تفکیک وضعیت فایل‌های ملکی ثبت‌شده"
              items={(data?.properties_by_status || []).map((p, idx) => ({
                label: translateStatus(p.status),
                value: p.count,
                color: COLORS[idx % COLORS.length],
              }))}
            />

            <DonutBreakdownChart
              title="وضعیت سرنخ‌ها (Leads Funnel)"
              subtitle="توزیع سرنخ‌های دریافتی در مراحل پیگیری"
              items={(data?.leads_by_status || []).map((l, idx) => ({
                label: translateStatus(l.status),
                value: l.count,
                color: COLORS[(idx + 1) % COLORS.length],
              }))}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <HorizontalBarChart
              title="حجم معاملات به تفکیک وضعیت"
              subtitle="بر اساس مبلغ کل معاملات (تومان)"
              unitLabel="تومان"
              items={(data?.deals_by_status || []).map((d) => ({
                label: translateStatus(d.status),
                value: Math.round(Number(d.volume) || 0),
                secondary: `${d.count} معامله`,
              }))}
            />

            <HorizontalBarChart
              title="میانگین قیمت هر مترمربع مناطق (تهران)"
              subtitle="محاسبه لحظه‌ای از املاک فعال بازار"
              unitLabel="تومان / متر"
              barColorClass="bg-amber-600"
              items={(trendsQ.data || []).map((t) => ({
                label: t.district,
                value: Number(t.avg_price_per_sqm) || 0,
                secondary: `${t.listing_count} ملک`,
              }))}
            />
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <h3 className="mb-4 text-sm font-bold text-slate-900 dark:text-slate-100">جدول رتبه‌بندی عملکرد مشاوران (بر اساس کمیسیون)</h3>
            {(data?.agent_leaderboard || []).length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">هنوز کمیسیون مشاوران در این آژانس ثبت نشده است.</p>
            ) : (
              <div className="space-y-2.5">
                {data?.agent_leaderboard.map((row, idx) => (
                  <div
                    key={row.membership_id}
                    className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 px-4 py-3 text-sm"
                  >
                    <div className="flex items-center gap-3">
                      <span className="flex h-7 w-7 items-center justify-center rounded-md bg-teal-700 text-xs font-bold text-white tabular-nums">
                        {idx + 1}
                      </span>
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{row.agent_name}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">{row.deals_count} سهم معامله</div>
                      </div>
                    </div>
                    <MoneyDisplay amount={row.total_commission} sourceCurrency="IRT" className="font-bold text-teal-800 dark:text-teal-300" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
