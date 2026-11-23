"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, BarChart3, Building2, Handshake, TrendingUp } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa, translateStatus } from "@/lib/formatters";
import type { AnalyticsData, BranchItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import {
  ActivityHeatmapGrid,
  DonutBreakdownChart,
  HorizontalBarChart,
  SalesFunnelChart,
  TrendLineChart,
} from "@/components/ui/AnalyticsCharts";
import { ImportExportDialog } from "@/components/ui/ImportExportDialog";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

interface AgencyMemberOption {
  id: string;
  full_name: string;
  role_code: string;
}

interface PriceTrendItem {
  district: string;
  listing_count: number;
  avg_price_per_sqm: string;
}

const COLORS = ["#0F766E", "#0284C7", "#D97706", "#059669", "#E11D48", "#64748B"];

export default function ReportsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const [periodDays, setPeriodDays] = useState(30);
  const [branchId, setBranchId] = useState("");
  const [agentId, setAgentId] = useState("");

  const branchesQ = useQuery({
    queryKey: ["reports-branches", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<BranchItem[]>(`/api/v1/agencies/${activeAgencyId}/branches`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const membersQ = useQuery({
    queryKey: ["reports-members", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<AgencyMemberOption[]>(`/api/v1/agencies/${activeAgencyId}/members`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const analyticsQ = useQuery({
    queryKey: ["reports-analytics", activeAgencyId, periodDays, branchId, agentId],
    enabled: !!accessToken,
    queryFn: async () => {
      const p = new URLSearchParams({ period_days: String(periodDays) });
      if (branchId) p.set("branch_id", branchId);
      if (agentId) p.set("agent_membership_id", agentId);
      return (
        await apiFetch<AnalyticsData>(`/api/v1/reports/analytics?${p.toString()}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const trendsQ = useQuery({
    queryKey: ["district-trends-report"],
    queryFn: async () =>
      (
        await apiFetch<PriceTrendItem[]>(
          "/api/v1/matching/analytics/price-trends?city=تهران"
        )
      ).data,
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
        title="گزارش‌ها و هوش تجاری (BI)"
        subtitle="تحلیل چندبعدی فایل‌ها، قیف فروش، مقایسه دوره، نقشه حرارتی بازدید و رتبه‌بندی شعب و مشاوران"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "گزارش‌ها و تحلیل" }]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ImportExportDialog module="properties" moduleLabel="املاک" />
            <ImportExportDialog module="accounting" moduleLabel="حسابداری" />
          </div>
        }
      />

      {/* BI Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5 dark:border-slate-700 dark:bg-slate-950">
          {[7, 30, 90, 365].map((days) => (
            <button
              key={days}
              type="button"
              onClick={() => setPeriodDays(days)}
              className={`h-8 rounded-md px-3 text-xs font-semibold transition-colors ${
                periodDays === days
                  ? "bg-teal-700 text-white"
                  : "text-slate-600 dark:text-slate-300"
              }`}
            >
              {formatNumberFa(days)} روز
            </button>
          ))}
        </div>

        {(branchesQ.data || []).length > 0 && (
          <select
            value={branchId}
            onChange={(e) => setBranchId(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="">همه شعب</option>
            {branchesQ.data?.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        )}

        {(membersQ.data || []).length > 0 && (
          <select
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="">همه مشاوران</option>
            {membersQ.data?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.full_name}
              </option>
            ))}
          </select>
        )}
      </div>

      {analyticsQ.isLoading ? (
        <LoadingState />
      ) : analyticsQ.error instanceof Error ? (
        <ErrorState message={analyticsQ.error.message} onRetry={() => analyticsQ.refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="کل املاک فیلترشده"
              value={formatNumberFa(totalProps)}
              icon={<Building2 className="h-5 w-5" />}
              tone="teal"
            />
            <KpiCard
              label="معاملات دوره"
              value={formatNumberFa(totalDeals)}
              hint={
                data?.period_comparison
                  ? `دوره قبل: ${formatNumberFa(data.period_comparison.previous_deals_count)} معامله`
                  : undefined
              }
              icon={<Handshake className="h-5 w-5" />}
              tone="emerald"
            />
            <KpiCard
              label="حجم مالی معاملات"
              value={<MoneyDisplay amount={totalDealVolume} sourceCurrency="IRT" />}
              hint={
                data?.period_comparison
                  ? `دوره قبل: ${formatNumberFa(Number(data.period_comparison.previous_volume) || 0)} تومان`
                  : undefined
              }
              icon={<BarChart3 className="h-5 w-5" />}
              tone="amber"
            />
            <KpiCard
              label="مذاکرات ثبت‌شده"
              value={formatNumberFa(data?.negotiations_count ?? 0)}
              icon={<Award className="h-5 w-5" />}
            />
          </div>

          {data?.period_comparison && (
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white px-5 py-3.5 text-xs dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-200">
                <TrendingUp className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                مقایسه دوره جاری ({formatNumberFa(periodDays)} روز) با دوره مشابه قبل:
              </div>
              <div className="flex flex-wrap items-center gap-6 tabular-nums">
                <div>
                  <span className="text-slate-500 dark:text-slate-400">حجم دوره جاری: </span>
                  <MoneyDisplay
                    amount={data.period_comparison.current_volume}
                    className="font-bold text-teal-800 dark:text-teal-300"
                  />
                </div>
                <div>
                  <span className="text-slate-500 dark:text-slate-400">حجم دوره قبل: </span>
                  <MoneyDisplay
                    amount={data.period_comparison.previous_volume}
                    className="font-semibold text-slate-700 dark:text-slate-300"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <TrendLineChart
              title="روند حجم معاملات و درآمدهای دوره"
              subtitle={`مقایسه درآمد و هزینه ثبت‌شده در ${formatNumberFa(periodDays)} روز اخیر`}
              primaryLabel="حجم معاملات"
              secondaryLabel="درآمد کمیسیون"
              points={(data?.timeline_series || []).map((t) => ({
                label: t.label,
                primary: Number(t.deal_volume) || 0,
                secondary: Number(t.revenue) || 0,
              }))}
            />

            <SalesFunnelChart
              title="قیف فروش ۱۲مرحله‌ای (Funnel)"
              subtitle="تبدیل سرنخ تا بازدید، مذاکره و عقد قرارداد"
              stages={data?.sales_funnel || []}
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
              title="وضعیت سرنخ‌ها (Leads)"
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
              title="تفکیک املاک بر اساس محله"
              subtitle="تعداد فایل‌ها و میانگین قیمت هر مترمربع در محله‌ها"
              unitLabel="فایل"
              items={(data?.district_breakdown || []).map((d) => ({
                label: d.district,
                value: d.count,
                secondary: `متری ${formatNumberFa(Number(d.avg_price_per_sqm) || 0)} تومان`,
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
                secondary: `${formatNumberFa(t.listing_count)} ملک`,
              }))}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ActivityHeatmapGrid
              title="نقشه حرارتی زمان بازدیدها (Heatmap)"
              subtitle="توزیع بازدیدها بر اساس روز هفته و بازه زمانی"
              rows={data?.activity_heatmap || []}
            />

            <HorizontalBarChart
              title="مقایسه شعب آژانس"
              subtitle="مقایسه تعداد فایل‌ها و مشاوران فعال هر شعبه"
              unitLabel="فایل"
              items={(data?.branch_comparison || []).map((b) => ({
                label: b.branch_name,
                value: b.properties_count,
                secondary: `${formatNumberFa(b.members_count)} عضو فعال`,
              }))}
            />
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <h3 className="mb-4 text-sm font-bold text-slate-900 dark:text-slate-100">
              جدول رتبه‌بندی عملکرد مشاوران (بر اساس کمیسیون)
            </h3>
            {(data?.agent_leaderboard || []).length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                هنوز کمیسیون مشاوران در این آژانس ثبت نشده است.
              </p>
            ) : (
              <div className="space-y-2.5">
                {data?.agent_leaderboard.map((row, idx) => (
                  <div
                    key={row.membership_id}
                    className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 px-4 py-3 text-sm"
                  >
                    <div className="flex items-center gap-3">
                      <span className="flex h-7 w-7 items-center justify-center rounded-md bg-teal-700 text-xs font-bold text-white tabular-nums">
                        {formatNumberFa(idx + 1)}
                      </span>
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          {row.agent_name}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          {formatNumberFa(row.deals_count)} سهم معامله
                        </div>
                      </div>
                    </div>
                    <MoneyDisplay
                      amount={row.total_commission}
                      sourceCurrency="IRT"
                      className="font-bold text-teal-800 dark:text-teal-300"
                    />
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
