"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Building2,
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  FileCheck2,
  Home,
  Landmark,
  Percent,
  Plus,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Ticket,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa, translateStatus } from "@/lib/formatters";
import type {
  AnalyticsData,
  DashboardLayoutConfig,
  OnboardingProgressData,
  OperationsCenterData,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import {
  DonutBreakdownChart,
  HorizontalBarChart,
  SalesFunnelChart,
  TrendLineChart,
} from "@/components/ui/AnalyticsCharts";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { StatusText } from "@/components/ui/StatusText";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
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
  lead_conversion_rate?: number;
  active_negotiations?: number;
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
  open_tickets?: number;
  urgent_tickets?: number;
  open_complaints?: number;
  resolved_tickets_period?: number;
  alerts?: DashboardAlert[];
  upcoming_tasks?: DashboardTask[];
  recent_activity?: DashboardActivity[];
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
  const qc = useQueryClient();
  const [periodDays, setPeriodDays] = useState(30);
  const [customizeOpen, setCustomizeOpen] = useState(false);

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
        await apiFetch<DashboardSummary>(`/api/v1/reports/dashboard?period_days=${periodDays}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const canViewAgencyAnalytics = !["CUSTOMER", "SUPPORT_AGENT"].includes(effectiveRole);

  const { data: analytics } = useQuery({
    queryKey: ["dashboard-analytics", activeAgencyId, user?.id, periodDays],
    enabled: !!accessToken && canViewAgencyAnalytics,
    queryFn: async () =>
      (
        await apiFetch<AnalyticsData>(`/api/v1/reports/analytics?period_days=${periodDays}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const layoutQ = useQuery({
    queryKey: ["dashboard-layout", activeAgencyId, user?.id],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<DashboardLayoutConfig>("/api/v1/reports/dashboard-layout", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  useEffect(() => {
    if (layoutQ.data?.default_period_days) {
      setPeriodDays(layoutQ.data.default_period_days);
    }
  }, [layoutQ.data?.default_period_days]);

  const onboardingQ = useQuery({
    queryKey: ["dashboard-onboarding", activeAgencyId, user?.id],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<OnboardingProgressData>("/api/v1/reports/onboarding", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const opsQ = useQuery({
    queryKey: ["dashboard-ops-center", activeAgencyId, user?.id],
    enabled: !!accessToken && canViewAgencyAnalytics && (!!activeAgencyId || effectiveRole === "SUPER_ADMIN"),
    queryFn: async () =>
      (
        await apiFetch<OperationsCenterData>("/api/v1/reports/operations-center", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const layoutMut = useMutation({
    mutationFn: async (widgets: { id: string; title: string; enabled: boolean }[]) =>
      apiFetch<DashboardLayoutConfig>("/api/v1/reports/dashboard-layout", {
        method: "PUT",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ widgets, default_period_days: periodDays }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard-layout"] });
    },
  });

  const onboardingMut = useMutation({
    mutationFn: async (payload: { toggle_step_key?: string; dismissed?: boolean }) =>
      apiFetch<OnboardingProgressData>("/api/v1/reports/onboarding", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard-onboarding"] });
    },
  });

  const widgets = layoutQ.data?.widgets || [];
  const isWidgetEnabled = (id: string) => {
    if (widgets.length === 0) return true;
    const found = widgets.find((w) => w.id === id);
    return found ? found.enabled : true;
  };

  const alerts = summary?.alerts || [];
  const upcomingTasks = summary?.upcoming_tasks || [];
  const recentActivity = summary?.recent_activity || [];
  const onboarding = onboardingQ.data;
  const completedCount = onboarding?.steps.filter((s) => s.completed).length || 0;
  const totalSteps = onboarding?.steps.length || 0;

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
            <Link href="/dashboard/daily-work" className="inline-flex h-8 items-center gap-2 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white transition hover:bg-teal-800">
              <Calendar className="h-4 w-4" /> مرکز کار روزانه
            </Link>
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

            {widgets.length > 0 && (
              <button
                type="button"
                onClick={() => setCustomizeOpen(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" />
                چیدمان ویجت‌ها
              </button>
            )}

            {effectiveRole === "AGENCY_ACCOUNTANT" ? (
              <Link
                href="/dashboard/accounting"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
              >
                <Landmark className="h-4 w-4" />
                تراز آزمایشی و اسناد
              </Link>
            ) : effectiveRole === "SUPPORT_AGENT" ? (
              <div className="flex flex-wrap gap-2">
                <Link
                  href="/dashboard/tickets"
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
                >
                  <Ticket className="h-4 w-4" />
                  صف تیکت‌های پشتیبانی
                </Link>
                <Link
                  href="/dashboard/complaints"
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  رسیدگی به شکایات
                </Link>
              </div>
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
          {/* Onboarding Checklist */}
          {onboarding && !onboarding.dismissed && totalSteps > 0 && (
            <div className="rounded-xl border border-teal-200 bg-white p-5 dark:border-teal-900/60 dark:bg-slate-900">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    چک‌لیست شروع سریع نقش شما ({formatNumberFa(completedCount)} از{" "}
                    {formatNumberFa(totalSteps)})
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => onboardingMut.mutate({ dismissed: true })}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
                >
                  <X className="h-3.5 w-3.5" />
                  بستن راهنما
                </button>
              </div>
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                {onboarding.steps.map((step) => (
                  <div
                    key={step.key}
                    className={`flex items-center justify-between gap-2 rounded-lg border p-3 text-xs ${
                      step.completed
                        ? "border-emerald-200 bg-emerald-50/50 dark:border-emerald-900/60 dark:bg-emerald-950/20"
                        : "border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/50"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => onboardingMut.mutate({ toggle_step_key: step.key })}
                      className="flex items-center gap-2 text-right font-semibold text-slate-800 dark:text-slate-200"
                    >
                      {step.completed ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <Circle className="h-4 w-4 shrink-0 text-slate-400" />
                      )}
                      <span className={step.completed ? "line-through opacity-75" : ""}>
                        {step.title}
                      </span>
                    </button>
                    <Link
                      href={step.href}
                      className="shrink-0 font-semibold text-teal-700 hover:underline dark:text-teal-400"
                    >
                      شروع
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Role Alerts Banner */}
          {isWidgetEnabled("alerts") && alerts.length > 0 && (
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
          {isWidgetEnabled("kpis") &&
            (summary?.role_view === "SUPER_ADMIN" ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard
                  label="آژانس‌های فعال"
                  value={formatNumberFa(summary.active_agencies || 0)}
                  hint={`مجموع: ${formatNumberFa(summary.total_agencies || 0)} | در انتظار: ${formatNumberFa(
                    summary.pending_agencies || 0
                  )}`}
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
                  hint={`ثبت‌شده در ${formatNumberFa(periodDays)} روز اخیر: ${formatNumberFa(
                    summary.period_properties || 0
                  )}`}
                  icon={<Home className="h-5 w-5" />}
                  tone="amber"
                />
                <KpiCard
                  label="حجم کل معاملات پلتفرم"
                  value={<MoneyDisplay amount={summary.total_deal_volume || "0"} />}
                  hint={`معاملات بازه: ${formatNumberFa(summary.period_deals || 0)} از ${formatNumberFa(
                    summary.total_deals || 0
                  )}`}
                  icon={<Landmark className="h-5 w-5" />}
                  tone="emerald"
                />
              </div>
            ) : summary?.role_view === "SUPPORT_AGENT" ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard
                  label="تیکت‌های باز پشتیبانی"
                  value={formatNumberFa(summary.open_tickets || 0)}
                  hint="تیکت‌های منتظر پاسخ و در حال پیگیری"
                  icon={<Ticket className="h-5 w-5" />}
                  tone="teal"
                />
                <KpiCard
                  label="تیکت‌های با اولویت فوری"
                  value={formatNumberFa(summary.urgent_tickets || 0)}
                  hint="نیازمند رسیدگی سریع SLA"
                  icon={<ShieldAlert className="h-5 w-5" />}
                  tone="amber"
                />
                <KpiCard
                  label="شکایات در حال بررسی"
                  value={formatNumberFa(summary.open_complaints || 0)}
                  hint="پرونده‌های باز رسیدگی به شکایات"
                  icon={<AlertTriangle className="h-5 w-5" />}
                />
                <KpiCard
                  label="تیکت‌های حل‌شده در دوره"
                  value={formatNumberFa(summary.resolved_tickets_period || 0)}
                  hint={`عملکرد ${formatNumberFa(periodDays)} روز اخیر`}
                  icon={<CheckCircle2 className="h-5 w-5" />}
                  tone="emerald"
                />
              </div>
            ) : summary?.role_view === "SALES_MANAGER" ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard
                  label="سرنخ‌ها و مشتریان فعال"
                  value={formatNumberFa(summary.total_customers || 0)}
                  hint={`کل سرنخ‌ها: ${formatNumberFa(summary.total_leads || 0)} | نرخ تبدیل: ${formatNumberFa(
                    summary.lead_conversion_rate || 0
                  )}٪`}
                  icon={<TrendingUp className="h-5 w-5" />}
                  tone="teal"
                />
                <KpiCard
                  label="مذاکرات باز و جاری"
                  value={formatNumberFa(summary.active_negotiations || 0)}
                  hint={`بازدیدهای زمان‌بندی‌شده: ${formatNumberFa(summary.scheduled_viewings || 0)}`}
                  icon={<Users className="h-5 w-5" />}
                  tone="amber"
                />
                <KpiCard
                  label="معاملات و قراردادهای فعال"
                  value={formatNumberFa(summary.active_deals || 0)}
                  hint={`معاملات ${formatNumberFa(periodDays)} روزه: ${formatNumberFa(summary.period_deals || 0)}`}
                  icon={<FileCheck2 className="h-5 w-5" />}
                />
                <KpiCard
                  label="سهم کمیسیون آژانس"
                  value={<MoneyDisplay amount={summary.agency_commission_revenue || "0"} />}
                  hint={`فایل‌های فعال: ${formatNumberFa(summary.active_properties || 0)}`}
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
                      فایل‌های تأییدشده را بررسی کرده، درخواست بازدید ثبت کنید یا تیکت پشتیبانی
                      ارسال نمایید.
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
                  hint={`معاملات ${formatNumberFa(periodDays)} روزه: ${formatNumberFa(
                    summary?.period_deals || 0
                  )} | بازدید: ${formatNumberFa(summary?.scheduled_viewings || 0)}`}
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
            ))}

          {/* Operations Center Strip */}
          {opsQ.data && canViewAgencyAnalytics && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  مرکز پایش عملیات روزانه آژانس
                </h3>
                <Link
                  href="/dashboard/appointments"
                  className="text-xs font-semibold text-teal-700 hover:underline dark:text-teal-400"
                >
                  تقویم یکپارچه رویدادها ←
                </Link>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                {[
                  {
                    label: "پیگیری‌های معوق",
                    count: opsQ.data.summary.overdue_tasks_count,
                    href: "/dashboard/crm",
                  },
                  {
                    label: "قراردادهای نزدیک پایان",
                    count: opsQ.data.summary.expiring_contracts_count,
                    href: "/dashboard/contracts",
                  },
                  {
                    label: "چک‌های نزدیک سررسید",
                    count: opsQ.data.summary.due_cheques_count,
                    href: "/dashboard/accounting",
                  },
                  {
                    label: "تیکت‌های باز/فوری",
                    count: opsQ.data.summary.urgent_tickets_count,
                    href: "/dashboard/tickets",
                  },
                  {
                    label: "فایل‌های منتظر تایید",
                    count: opsQ.data.summary.pending_properties_count,
                    href: "/dashboard/properties",
                  },
                ].map((item) => (
                  <Link
                    key={item.label}
                    href={item.href}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 transition-colors hover:border-teal-600 dark:border-slate-800 dark:bg-slate-800/60"
                  >
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">
                      {item.label}
                    </div>
                    <div className="mt-1 tabular-nums text-base font-extrabold text-slate-900 dark:text-slate-100">
                      {formatNumberFa(item.count)}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Charts Row */}
          {analytics && canViewAgencyAnalytics && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {isWidgetEnabled("bi_trend") && analytics.timeline_series && (
                <TrendLineChart
                  title="روند درآمد و هزینه دوره‌ای"
                  subtitle={`تفکیک بازه‌ای در ${formatNumberFa(periodDays)} روز اخیر`}
                  primaryLabel="درآمد ثبت‌شده"
                  secondaryLabel="هزینه عملیاتی"
                  points={analytics.timeline_series.map((t) => ({
                    label: t.label,
                    primary: Number(t.revenue) || 0,
                    secondary: Number(t.expense) || 0,
                  }))}
                />
              )}

              {isWidgetEnabled("funnel") && analytics.sales_funnel && (
                <SalesFunnelChart
                  title="قیف تبدیل فروش و مذاکره"
                  subtitle="نرخ تبدیل سرنخ تا عقد قرارداد و معامله"
                  stages={analytics.sales_funnel}
                />
              )}

              <DonutBreakdownChart
                title="توزیع وضعیت فایل‌های ملکی"
                subtitle="بر اساس وضعیت چرخه حیات ملک در آژانس"
                items={analytics.properties_by_status.map((row, idx) => ({
                  label: translateStatus(row.status),
                  value: row.count,
                  color: CHART_COLORS[idx % CHART_COLORS.length],
                }))}
              />

              {isWidgetEnabled("leaderboard") && (
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
              )}
            </div>
          )}

          {/* Operational Tasks & Recent Activity */}
          {((isWidgetEnabled("upcoming") && upcomingTasks.length > 0) ||
            (isWidgetEnabled("activity") && recentActivity.length > 0)) && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {isWidgetEnabled("upcoming") && (
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
              )}

              {isWidgetEnabled("activity") && (
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
                        <div
                          key={act.id}
                          className="flex items-center justify-between gap-3 py-2.5 text-xs"
                        >
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
              )}
            </div>
          )}
        </>
      )}

      {/* Widget Customizer Drawer */}
      <ModalDrawer
        open={customizeOpen}
        onClose={() => setCustomizeOpen(false)}
        title="شخصی‌سازی ویجت‌های میز کار"
      >
        <div className="space-y-3 text-xs">
          <p className="text-slate-600 dark:text-slate-400">
            نمایش یا مخفی‌سازی ویجت‌های داشبورد را بر اساس نیاز کاری خود تنظیم کنید:
          </p>
          <div className="space-y-2">
            {widgets.map((w) => (
              <label
                key={w.id}
                className="flex cursor-pointer items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5 dark:border-slate-800 dark:bg-slate-800/60"
              >
                <span className="font-semibold text-slate-800 dark:text-slate-200">{w.title}</span>
                <input
                  type="checkbox"
                  checked={w.enabled}
                  onChange={() => {
                    const updated = widgets.map((item) =>
                      item.id === w.id ? { ...item, enabled: !item.enabled } : item
                    );
                    layoutMut.mutate(updated);
                  }}
                  className="h-4 w-4 accent-teal-700"
                />
              </label>
            ))}
          </div>
        </div>
      </ModalDrawer>
    </div>
  );
}
