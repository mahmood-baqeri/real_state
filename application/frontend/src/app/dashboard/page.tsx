// Path: frontend/src/app/dashboard/page.tsx

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  FileCheck2,
  Home,
  Landmark,
  Percent,
  Plus,
  ShieldAlert,
  Ticket,
  Users,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa, translateStatus } from "@/lib/formatters";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { DonutBreakdownChart, HorizontalBarChart } from "@/components/ui/AnalyticsCharts";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { StatusText } from "@/components/ui/StatusText";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

interface DashboardAlert {
  level: "warning" | "danger" | "info";
  title: string;
  count: number;
  href: string;
}

interface DashboardTask {
  id: string;
  title: string;
  due_at: string;
  status: string;
  href: string;
}

interface DashboardActivity {
  id: string;
  action: string;
  resource_type: string;
  actor_name: string;
  created_at: string;
}

interface DashboardSummary {
  role_view: string;
  period_days?: number;
  agency_name?: string;
  branch_name?: string | null;
  total_agencies?: number;
  active_agencies?: number;
  pending_agencies?: number;
  total_users?: number;
  total_properties?: number;
  period_properties?: number;
  total_deals?: number;
  period_deals?: number;
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
  treasury_total?: string;
  held_receivable_cheques_total?: string;
  posted_journal_entries?: number;
  payroll_runs_count?: number;
  my_properties?: number;
  my_customers?: number;
  my_leads?: number;
  my_scheduled_viewings?: number;
  my_commission_total?: string;
  my_viewings_count?: number;
  published_properties_count?: number;
  alerts?: DashboardAlert[];
  upcoming_tasks?: DashboardTask[];
  recent_activity?: DashboardActivity[];
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

const PERIOD_OPTIONS = [
  { days: 7, label: "۷ روز اخیر" },
  { days: 30, label: "۳۰ روز اخیر" },
  { days: 90, label: "۳ ماه اخیر" },
  { days: 365, label: "۱ سال اخیر" },
];

export default function DashboardOverviewPage() {
  const { user, accessToken, activeAgencyId, effectiveRole } = useAuth();
  const [periodDays, setPeriodDays] = useState(30);

  const {
    data: summary,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["dashboard-summary", activeAgencyId, user?.id, periodDays],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<DashboardSummary>(
          `/api/v1/reports/dashboard?period_days=${periodDays}`,
          {
            token: accessToken,
            agencyId: activeAgencyId,
          }
        )
      ).data,
  });

  const { data: analytics } = useQuery({
    queryKey: ["dashboard-analytics", activeAgencyId, user?.id, periodDays],
    enabled: !!accessToken && effectiveRole !== "CUSTOMER",
    queryFn: async () =>
      (
        await apiFetch<AnalyticsData>(
          `/api/v1/reports/analytics?period_days=${periodDays}`,
          {
            token: accessToken,
            agencyId: activeAgencyId,
          }
        )
      ).data,
  });

  const alerts = summary?.alerts || [];
  const upcomingTasks = summary?.upcoming_tasks || [];
  const recentActivity = summary?.recent_activity || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={`خوش آمدید، ${user?.full_name || ""}`}
        subtitle={
          summary?.agency_name
            ? `میز کار اختصاصی — ${summary.agency_name}${summary.branch_name ? ` (${summary.branch_name})` : ""}`
            : "نمای کلی پلتفرم یکپارچه مدیریت املاک بنیان ملک"
        }
        breadcrumbs={[{ label: "میز کار" }]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {/* Period Filter */}
            <div className="inline-flex items-center rounded-lg border border-slate-200 bg-white p-0.5 dark:border-slate-700 dark:bg-slate-900">
              {PERIOD_OPTIONS.map((p) => (
                <button
                  key={p.days}
                  type="button"
                  onClick={() => setPeriodDays(p.days)}
                  className={`h-7 whitespace-nowrap rounded-md px-2.5 text-[11px] font-semibold transition-colors ${
                    periodDays === p.days
                      ? "bg-teal-700 text-white dark:bg-teal-600"
                      : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {effectiveRole === "AGENCY_ACCOUNTANT" ? (
              <Link
                href="/dashboard/accounting"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
              >
                <Landmark className="h-4 w-4" />
                تراز آزمایشی و اسناد
              </Link>
            ) : effectiveRole !== "CUSTOMER" ? (
              <div className="flex flex-wrap gap-2">
                <Link
                  href="/dashboard/properties/new"
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
                >
                  <Plus className="h-4 w-4" />
                  ثبت ملک جدید
                </Link>
                <Link
                  href="/dashboard/crm"
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  پایپ‌لاین CRM
                </Link>
              </div>
            ) : (
              <Link
                href="/search"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
              >
                جستجوی املاک
              </Link>
            )}
          </div>
        }
      />

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState
          message={error instanceof Error ? error.message : "خطا در دریافت آمار داشبورد"}
          onRetry={() => refetch()}
        />
      ) : (
        <>
          {/* Role Alerts Banner */}
          {alerts.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {alerts.map((al, i) => {
                const cls =
                  al.level === "danger"
                    ? "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900/70 dark:bg-rose-950/30 dark:text-rose-200"
                    : al.level === "warning"
                    ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-200"
                    : "border-teal-200 bg-teal-50 text-teal-900 dark:border-teal-900/70 dark:bg-teal-950/30 dark:text-teal-200";
                return (
                  <Link
                    key={i}
                    href={al.href}
                    className={`flex items-center justify-between rounded-xl border p-3.5 transition-opacity hover:opacity-90 ${cls}`}
                  >
                    <div className="flex items-center gap-2.5 text-xs font-semibold">
                      {al.level === "danger" ? (
                        <ShieldAlert className="h-4 w-4 shrink-0" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                      )}
                      <span>{al.title}</span>
                    </div>
                    <span className="tabular-nums rounded-md bg-white/80 px-2 py-0.5 text-xs font-bold text-slate-900 dark:bg-slate-900/80 dark:text-slate-100">
                      {formatNumberFa(al.count)} مورد
                    </span>
                  </Link>
                );
              })}
            </div>
          )}

          {/* Role-Specific KPI Cards */}
          {summary?.role_view === "SUPER_ADMIN" ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <KpiCard
                label="آژانس‌های فعال"
                value={formatNumberFa(summary.active_agencies || 0)}
                hint={`مجموع: ${formatNumberFa(summary.total_agencies || 0)} | در انتظار: ${formatNumberFa(summary.pending_agencies || 0)}`}
                icon={<Building2 className="h-5 w-5" />}
                tone="teal"
              />
              <KpiCard
                label="کاربران و اشتراک‌های فعال"
                value={formatNumberFa(summary.total_users || 0)}
                hint={`اشتراک‌های فعال: ${formatNumberFa(summary.active_subscriptions || 0)}`}
                icon={<Users className="h-5 w-5" />}
              />
              <KpiCard
                label="فایل‌های املاک کل پلتفرم"
                value={formatNumberFa(summary.total_properties || 0)}
                hint={`ثبت‌شده در ${formatNumberFa(periodDays)} روز اخیر: ${formatNumberFa(summary.period_properties || 0)}`}
                icon={<Home className="h-5 w-5" />}
                tone="amber"
              />
              <KpiCard
                label="حجم کل معاملات پلتفرم"
                value={<MoneyDisplay amount={summary.total_deal_volume || "0"} />}
                hint={`معاملات بازه: ${formatNumberFa(summary.period_deals || 0)} از ${formatNumberFa(summary.total_deals || 0)}`}
                icon={<Landmark className="h-5 w-5" />}
                tone="emerald"
              />
            </div>
          ) : summary?.role_view === "AGENCY_ACCOUNTANT" ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <KpiCard
                label="مجموع نقدینگی بانک و صندوق"
                value={<MoneyDisplay amount={summary.treasury_total || "0"} />}
                hint="تجمیع حساب‌های بانکی و صندوق‌های فعال"
                icon={<Landmark className="h-5 w-5" />}
                tone="teal"
              />
              <KpiCard
                label="چک‌های دریافتنی در جریان"
                value={<MoneyDisplay amount={summary.held_receivable_cheques_total || "0"} />}
                hint="جمع اسناد چک دریافتنی نزد صندوق"
                icon={<FileCheck2 className="h-5 w-5" />}
                tone="amber"
              />
              <KpiCard
                label="اسناد حسابداری قطعی"
                value={formatNumberFa(summary.posted_journal_entries || 0)}
                hint={`دوره‌های حقوق و دستمزد: ${formatNumberFa(summary.payroll_runs_count || 0)}`}
                icon={<CheckCircle2 className="h-5 w-5" />}
              />
              <KpiCard
                label="سهم کمیسیون آژانس"
                value={<MoneyDisplay amount={summary.agency_commission_revenue || "0"} />}
                hint={`معاملات فعال: ${formatNumberFa(summary.active_deals || 0)}`}
                icon={<Percent className="h-5 w-5" />}
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
              <div className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    دسترسی سریع متقاضی ({formatNumberFa(summary.published_properties_count || 0)} ملک
                    فعال)
                  </h3>
                  <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                    فایل‌های تأییدشده را بررسی کرده، درخواست بازدید ثبت کنید یا تیکت پشتیبانی ارسال
                    نمایید.
                  </p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link
                    href="/search"
                    className="inline-flex h-9 items-center rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
                  >
                    جستجوی املاک پورتال
                  </Link>
                  <Link
                    href="/dashboard/appointments"
                    className="inline-flex h-9 items-center rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  >
                    بازدیدهای من
                  </Link>
                  <Link
                    href="/requests/new"
                    className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  >
                    <Ticket className="h-3.5 w-3.5" />
                    ثبت درخواست
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
                label="مشتریان و سرنخ‌های من"
                value={formatNumberFa(summary.my_customers || 0)}
                hint={`سرنخ‌های پیگیری: ${formatNumberFa(summary.my_leads || 0)}`}
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
                hint={`معاملات ${formatNumberFa(periodDays)} روزه: ${formatNumberFa(summary?.period_deals || 0)} | بازدید: ${formatNumberFa(summary?.scheduled_viewings || 0)}`}
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

          {/* Charts Row */}
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

          {/* Operational Tasks & Recent Activity */}
          {(upcomingTasks.length > 0 || recentActivity.length > 0) && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                    <Clock className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    کارها و بازدیدهای در پیش
                  </h3>
                  <Link
                    href="/dashboard/appointments"
                    className="text-xs font-semibold text-teal-700 hover:underline dark:text-teal-400"
                  >
                    مشاهده همه
                  </Link>
                </div>
                {upcomingTasks.length === 0 ? (
                  <p className="py-6 text-center text-xs text-slate-500 dark:text-slate-400">
                    برنامه زمان‌بندی فعالی ثبت نشده است.
                  </p>
                ) : (
                  <div className="space-y-2.5">
                    {upcomingTasks.map((t) => (
                      <Link
                        key={t.id}
                        href={t.href}
                        className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs transition-colors hover:border-teal-600 dark:border-slate-800 dark:bg-slate-800/60"
                      >
                        <div className="min-w-0">
                          <div className="truncate font-semibold text-slate-900 dark:text-slate-100">
                            {t.title}
                          </div>
                          <DateDisplay
                            value={t.due_at}
                            className="mt-0.5 block text-[11px] text-slate-500 dark:text-slate-400"
                          />
                        </div>
                        <StatusText status={t.status} />
                      </Link>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                    <Activity className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    آخرین رخدادهای ممیزی و عملیات
                  </h3>
                  <Link
                    href="/dashboard/audit"
                    className="text-xs font-semibold text-teal-700 hover:underline dark:text-teal-400"
                  >
                    گزارش کامل
                  </Link>
                </div>
                {recentActivity.length === 0 ? (
                  <p className="py-6 text-center text-xs text-slate-500 dark:text-slate-400">
                    رخداد جدیدی برای نمایش وجود ندارد.
                  </p>
                ) : (
                  <div className="divide-y divide-slate-100 dark:divide-slate-800">
                    {recentActivity.map((act) => (
                      <div key={act.id} className="flex items-center justify-between gap-3 py-2.5 text-xs">
                        <div className="min-w-0">
                          <span className="font-mono font-semibold text-teal-800 dark:text-teal-300">
                            {act.action}
                          </span>{" "}
                          <span className="text-slate-600 dark:text-slate-400">
                            ({act.resource_type}) — {act.actor_name}
                          </span>
                        </div>
                        <DateDisplay
                          value={act.created_at}
                          className="shrink-0 text-[11px] text-slate-500 dark:text-slate-400"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
