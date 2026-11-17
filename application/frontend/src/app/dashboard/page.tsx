"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  Calendar,
  FileCheck2,
  Home,
  Landmark,
  Percent,
  Plus,
  Users,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa, translateStatus } from "@/lib/formatters";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { DonutBreakdownChart, HorizontalBarChart } from "@/components/ui/AnalyticsCharts";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

interface DashboardSummary {
  role_view: string;
  agency_name?: string;
  total_agencies?: number;
  active_agencies?: number;
  pending_agencies?: number;
  total_users?: number;
  total_properties?: number;
  total_deals?: number;
  active_subscriptions?: number;
  total_deal_volume?: string;
  active_properties?: number;
  pending_approval_properties?: number;
  total_customers?: number;
  total_leads?: number;
  active_deals?: number;
  agency_commission_revenue?: string;
  agents_count?: number;
  scheduled_viewings?: number;
  my_properties?: number;
  my_customers?: number;
  my_scheduled_viewings?: number;
  my_commission_total?: string;
  my_viewings_count?: number;
}

interface AnalyticsData {
  properties_by_status: { status: string; count: number }[];
  deals_by_status: { status: string; count: number; volume: string }[];
  leads_by_status?: { status: string; count: number }[];
  agent_leaderboard: {
    membership_id: string;
    agent_name: string;
    total_commission: string;
    deals_count: number;
  }[];
}

const CHART_COLORS = ["#0F766E", "#B45309", "#2563EB", "#475569", "#16A34A", "#DC2626"];

export default function DashboardOverviewPage() {
  const { user, accessToken, activeAgencyId, effectiveRole } = useAuth();

  const {
    data: summary,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["dashboard-summary", activeAgencyId, user?.id],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<DashboardSummary>("/api/v1/reports/dashboard", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const { data: analytics } = useQuery({
    queryKey: ["dashboard-analytics", activeAgencyId, user?.id],
    enabled: !!accessToken && effectiveRole !== "CUSTOMER",
    queryFn: async () =>
      (
        await apiFetch<AnalyticsData>("/api/v1/reports/analytics", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={`خوش آمدید، ${user?.full_name || ""}`}
        subtitle={
          summary?.agency_name
            ? `نمای مدیریتی و عملیاتی — ${summary.agency_name}`
            : "نمای کلی پلتفرم یکپارچه مدیریت املاک بنیان ملک"
        }
        breadcrumbs={[{ label: "میز کار" }]}
        actions={
          effectiveRole !== "CUSTOMER" && effectiveRole !== "AGENCY_ACCOUNTANT" ? (
            <div className="flex flex-wrap gap-2">
              <Link
                href="/dashboard/properties/new"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <Plus className="h-4 w-4" />
                ثبت ملک جدید
              </Link>
              <Link
                href="/dashboard/crm"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
              >
                پایپ‌لاین CRM
              </Link>
            </div>
          ) : null
        }
      />

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState
          message={error instanceof Error ? error.message : "خطا در دریافت آمار داشبورد"}
          onRetry={() => refetch()}
        />
      ) : summary?.role_view === "SUPER_ADMIN" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="آژانس‌های فعال"
            value={formatNumberFa(summary.active_agencies || 0)}
            hint={`مجموع آژانس‌ها: ${formatNumberFa(summary.total_agencies || 0)}`}
            icon={<Building2 className="h-5 w-5" />}
            tone="teal"
          />
          <KpiCard
            label="کل کاربران فعال"
            value={formatNumberFa(summary.total_users || 0)}
            hint={`اشتراک‌های فعال: ${formatNumberFa(summary.active_subscriptions || 0)}`}
            icon={<Users className="h-5 w-5" />}
          />
          <KpiCard
            label="فایل‌های املاک ثبت‌شده"
            value={formatNumberFa(summary.total_properties || 0)}
            hint={`تعداد کل معاملات: ${formatNumberFa(summary.total_deals || 0)}`}
            icon={<Home className="h-5 w-5" />}
            tone="amber"
          />
          <KpiCard
            label="حجم کل معاملات پلتفرم"
            value={<MoneyDisplay amount={summary.total_deal_volume || "0"} />}
            hint="ارزش تجمیعی معاملات ثبت‌شده"
            icon={<Landmark className="h-5 w-5" />}
            tone="emerald"
          />
        </div>
      ) : summary?.role_view === "CUSTOMER" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <KpiCard
            label="درخواست‌های بازدید من"
            value={formatNumberFa(summary.my_viewings_count || 0)}
            hint="وضعیت زمان‌بندی بازدید از املاک"
            icon={<Calendar className="h-5 w-5" />}
            tone="teal"
          />
          <div className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5">
            <div>
              <h3 className="text-sm font-bold text-slate-900">جستجوی فایل‌های جدید</h3>
              <p className="mt-1 text-xs text-slate-600">
                فایل‌های تأییدشده را در پورتال عمومی بررسی کرده و درخواست بازدید حضوری ثبت کنید.
              </p>
            </div>
            <div className="mt-4 flex gap-2">
              <Link
                href="/"
                className="inline-flex h-9 items-center rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800"
              >
                مشاهده املاک پورتال
              </Link>
              <Link
                href="/dashboard/appointments"
                className="inline-flex h-9 items-center rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-slate-800 hover:bg-slate-50"
              >
                بازدیدهای من
              </Link>
            </div>
          </div>
        </div>
      ) : summary?.role_view === "AGENT" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="فایل‌های تحت مسئولیت من"
            value={formatNumberFa(summary.my_properties || 0)}
            icon={<Home className="h-5 w-5" />}
            tone="teal"
          />
          <KpiCard
            label="مشتریان فعال من"
            value={formatNumberFa(summary.my_customers || 0)}
            icon={<Users className="h-5 w-5" />}
          />
          <KpiCard
            label="بازدیدهای پیش‌رو"
            value={formatNumberFa(summary.my_scheduled_viewings || 0)}
            icon={<Calendar className="h-5 w-5" />}
            tone="amber"
          />
          <KpiCard
            label="مجموع سهم کمیسیون من"
            value={<MoneyDisplay amount={summary.my_commission_total || "0"} />}
            icon={<Percent className="h-5 w-5" />}
            tone="emerald"
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="فایل‌های منتشرشده"
            value={formatNumberFa(summary?.active_properties || 0)}
            hint={`در انتظار تأیید: ${formatNumberFa(summary?.pending_approval_properties || 0)}`}
            icon={<Home className="h-5 w-5" />}
            tone="teal"
          />
          <KpiCard
            label="مشتریان و سرنخ‌ها"
            value={formatNumberFa(summary?.total_customers || 0)}
            hint={`سرنخ‌ها (Leads): ${formatNumberFa(summary?.total_leads || 0)}`}
            icon={<Users className="h-5 w-5" />}
          />
          <KpiCard
            label="معاملات و بازدیدهای فعال"
            value={formatNumberFa(summary?.active_deals || 0)}
            hint={`بازدیدهای برنامه‌ریزی‌شده: ${formatNumberFa(summary?.scheduled_viewings || 0)}`}
            icon={<FileCheck2 className="h-5 w-5" />}
            tone="amber"
          />
          <KpiCard
            label="سهم کمیسیون آژانس"
            value={<MoneyDisplay amount={summary?.agency_commission_revenue || "0"} />}
            hint={`تعداد اعضای فعال: ${formatNumberFa(summary?.agents_count || 0)}`}
            icon={<Landmark className="h-5 w-5" />}
            tone="emerald"
          />
        </div>
      )}

      {analytics && effectiveRole !== "CUSTOMER" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <DonutBreakdownChart
            title="توزیع وضعیت فایل‌های ملکی"
            subtitle="بر اساس وضعیت چرخه حیات ملک در آژانس"
            items={analytics.properties_by_status.map((row, idx) => ({
              label: translateStatus(row.status),
              value: row.count,
              color: CHART_COLORS[idx % CHART_COLORS.length],
            }))}
          />
          <HorizontalBarChart
            title="عملکرد کمیسیون مشاوران"
            subtitle="رتبه‌بندی مشاوران بر اساس سهم کمیسیون محاسبه‌شده"
            items={analytics.agent_leaderboard.map((a) => ({
              label: a.agent_name,
              value: Number(a.total_commission || 0),
              secondary: `${formatNumberFa(a.deals_count)} معامله`,
            }))}
            unitLabel="تومان"
          />
        </div>
      )}
    </div>
  );
}
