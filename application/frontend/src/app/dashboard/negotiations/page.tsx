"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  Columns3,
  ExternalLink,
  History,
  Plus,
  Table2,
  TrendingDown,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type {
  CustomerItem,
  NegotiationAnalytics,
  NegotiationItem,
  PropertyItem,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { KpiCard } from "@/components/ui/KpiCard";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";
import { formatNumberFa, translateStatus } from "@/lib/formatters";

const KANBAN_LANES: { id: string; title: string; statuses: string[] }[] = [
  {
    id: "init",
    title: "شروع و انتظار پیشنهاد",
    statuses: ["CREATED", "AWAITING_BUYER_OFFER", "OPEN"],
  },
  {
    id: "offers",
    title: "پیشنهاد خریدار / مالک",
    statuses: ["BUYER_OFFERED", "AWAITING_OWNER_RESPONSE", "OWNER_COUNTERED", "COUNTER_OFFERED"],
  },
  {
    id: "bargain",
    title: "چانه‌زنی و توافق اولیه",
    statuses: ["BARGAINING", "PRE_AGREEMENT", "AWAITING_FINAL_APPROVAL"],
  },
  {
    id: "won",
    title: "توافق قطعی / قرارداد",
    statuses: ["ACCEPTED"],
  },
  {
    id: "closed",
    title: "متوقف / رد / لغو",
    statuses: ["PAUSED", "REJECTED", "CANCELLED", "WITHDRAWN", "EXPIRED"],
  },
];

export default function NegotiationsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [viewMode, setViewMode] = useState<"table" | "kanban" | "analytics">("table");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [offersTarget, setOffersTarget] = useState<NegotiationItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    property_id: "",
    customer_id: "",
    owner_customer_id: "",
    deal_type_id: "SALE",
    asking_price: "",
    initial_price: "36500000000",
    offered_by: "BUYER",
    next_action: "تماس اولیه و انتقال پیشنهاد به مالک",
    next_followup_at: "",
    notes: "",
  });

  const [offerForm, setOfferForm] = useState({
    offered_by: "SELLER",
    proposed_price: "37500000000",
    discount_amount: "0",
    notes: "",
  });

  const negsQ = useQuery({
    queryKey: ["negotiations", activeAgencyId, overdueOnly],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () => {
      const qs = overdueOnly ? "?overdue_only=true&page_size=100" : "?page_size=100";
      return (
        await apiFetch<NegotiationItem[]>(`/api/v1/negotiations${qs}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const analyticsQ = useQuery({
    queryKey: ["negotiations-analytics", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<NegotiationAnalytics>("/api/v1/negotiations/analytics", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const propsQ = useQuery({
    queryKey: ["props-neg", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<PropertyItem[]>("/api/v1/properties?page_size=50", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const custQ = useQuery({
    queryKey: ["custs-neg", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<CustomerItem[]>("/api/v1/customers?page_size=50", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/negotiations", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          property_id: form.property_id,
          customer_id: form.customer_id,
          owner_customer_id: form.owner_customer_id || null,
          deal_type_id: form.deal_type_id,
          asking_price: form.asking_price || null,
          initial_price: form.initial_price || null,
          offered_by: form.offered_by,
          next_action: form.next_action,
          next_followup_at: form.next_followup_at
            ? new Date(form.next_followup_at).toISOString()
            : null,
          notes: form.notes,
        }),
      }),
    onSuccess: () => {
      setCreateOpen(false);
      setErrMsg(null);
      setNotice("پرونده مذاکره ۱۲ مرحله‌ای و پیشنهاد اولیه ثبت شد.");
      qc.invalidateQueries({ queryKey: ["negotiations"] });
      qc.invalidateQueries({ queryKey: ["negotiations-analytics"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const addOfferMut = useMutation({
    mutationFn: async () => {
      if (!offersTarget) return;
      return apiFetch(`/api/v1/negotiations/${offersTarget.id}/offers`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(offerForm),
      });
    },
    onSuccess: () => {
      setOffersTarget(null);
      setNotice("نسخه پیشنهاد متقابل جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["negotiations"] });
      qc.invalidateQueries({ queryKey: ["negotiations-analytics"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const respondMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/negotiations/${id}/respond`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setNotice("مرحله مذاکره با موفقیت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["negotiations"] });
      qc.invalidateQueries({ queryKey: ["negotiations-analytics"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const negotiations = useMemo(() => negsQ.data || [], [negsQ.data]);
  const analytics = analyticsQ.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="مرکز مدیریت مذاکرات و پیشنهادهای قیمتی"
        subtitle="گردش‌کار ۱۲ مرحله‌ای مذاکره، تاریخچه نسخه‌های پیشنهاد، پیگیری‌های سررسیدشده و تبدیل یک‌کلیکی به قرارداد"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "مذاکرات" }]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 text-xs dark:border-slate-800 dark:bg-slate-900">
              <button
                type="button"
                onClick={() => setViewMode("table")}
                className={`inline-flex h-8 items-center gap-1 rounded-md px-2.5 font-semibold ${
                  viewMode === "table"
                    ? "bg-teal-700 text-white"
                    : "text-slate-600 dark:text-slate-300"
                }`}
              >
                <Table2 className="h-3.5 w-3.5" />
                جدول
              </button>
              <button
                type="button"
                onClick={() => setViewMode("kanban")}
                className={`inline-flex h-8 items-center gap-1 rounded-md px-2.5 font-semibold ${
                  viewMode === "kanban"
                    ? "bg-teal-700 text-white"
                    : "text-slate-600 dark:text-slate-300"
                }`}
              >
                <Columns3 className="h-3.5 w-3.5" />
                کانبن مراحل
              </button>
              <button
                type="button"
                onClick={() => setViewMode("analytics")}
                className={`inline-flex h-8 items-center gap-1 rounded-md px-2.5 font-semibold ${
                  viewMode === "analytics"
                    ? "bg-teal-700 text-white"
                    : "text-slate-600 dark:text-slate-300"
                }`}
              >
                <BarChart3 className="h-3.5 w-3.5" />
                گزارش تحلیلی
              </button>
            </div>

            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Plus className="h-4 w-4" />
              شروع مذاکره جدید
            </button>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {/* Analytics KPI Strip */}
      {analytics && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KpiCard
            label="کل مذاکرات / پرونده‌های فعال"
            value={`${formatNumberFa(analytics.total_count)} / ${formatNumberFa(analytics.active_count)}`}
          />
          <KpiCard
            label="نرخ موفقیت مذاکرات"
            value={`${formatNumberFa(analytics.win_rate_percent)}٪`}
            hint={`${formatNumberFa(analytics.won_count)} توافق نهایی`}
          />
          <KpiCard
            label="میانگین تخفیف از قیمت پایه"
            value={`${formatNumberFa(analytics.avg_discount_percent)}٪`}
            icon={<TrendingDown className="h-4 w-4" />}
            hint={`میانگین ${formatNumberFa(analytics.avg_offers_per_negotiation)} پیشنهاد`}
          />
          <KpiCard
            label="پیگیری‌های معوقه"
            value={formatNumberFa(analytics.overdue_followups_count)}
            icon={<AlertTriangle className="h-4 w-4 text-amber-600" />}
            hint={`میانگین مدت: ${formatNumberFa(analytics.avg_duration_days)} روز`}
          />
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <label className="inline-flex cursor-pointer items-center gap-2 font-semibold text-slate-700 dark:text-slate-300">
          <input
            type="checkbox"
            checked={overdueOnly}
            onChange={(e) => setOverdueOnly(e.target.checked)}
            className="h-4 w-4 accent-amber-600"
          />
          فقط نمایش مذاکرات با پیگیری معوقه (Overdue)
        </label>
      </div>

      {viewMode === "table" && (
        <DataTable
          rows={negotiations}
          rowKey={(n) => n.id}
          isLoading={negsQ.isLoading}
          error={negsQ.error instanceof Error ? negsQ.error.message : null}
          searchPlaceholder="جستجو در ملک، کد فایل یا نام مشتری..."
          columns={[
            {
              key: "prop",
              header: "ملک و مالک",
              render: (n) => (
                <div>
                  <Link
                    href={`/dashboard/negotiations/${n.id}`}
                    className="font-bold text-slate-900 hover:text-teal-700 dark:text-slate-100 dark:hover:text-teal-400"
                  >
                    {n.property_title}
                  </Link>
                  <div className="font-mono text-[11px] text-slate-400">
                    {n.property_code} {n.owner_name ? `· مالک: ${n.owner_name}` : ""}
                  </div>
                </div>
              ),
            },
            {
              key: "cust",
              header: "خریدار / متقاضی",
              render: (n) => (
                <div>
                  <div className="font-medium">{n.customer_name}</div>
                  {n.next_action && (
                    <div
                      className={`text-[11px] ${
                        n.is_followup_overdue
                          ? "font-bold text-rose-600 dark:text-rose-400"
                          : "text-slate-500 dark:text-slate-400"
                      }`}
                    >
                      {n.is_followup_overdue ? "پیگیری معوقه: " : "اقدام بعدی: "}
                      {n.next_action}
                    </div>
                  )}
                </div>
              ),
            },
            {
              key: "latest",
              header: "آخرین پیشنهاد و فاصله قیمت",
              render: (n) => {
                const last = n.offers[n.offers.length - 1];
                const priceToDisplay = n.agreed_price || last?.proposed_price || n.latest_proposed_price;
                return priceToDisplay && Number(priceToDisplay) > 0 ? (
                  <div>
                    <MoneyDisplay
                      amount={priceToDisplay}
                      sourceCurrency={last?.currency || "IRT"}
                      className="text-xs font-bold"
                    />
                    <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 tabular-nums">
                      {last && <span>نسخه {last.version_number}</span>}
                      {n.price_delta_percent !== undefined && n.price_delta_percent !== 0 && (
                        <span className="font-mono text-amber-700 dark:text-amber-400">
                          ({n.price_delta_percent > 0 ? "+" : ""}
                          {n.price_delta_percent}%)
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  "—"
                );
              },
            },
            {
              key: "status",
              header: "مرحله",
              render: (n) => (
                <div className="space-y-1">
                  <StatusText status={n.status} />
                  {n.converted_contract_number && (
                    <div className="font-mono text-[10px] font-bold text-emerald-700 dark:text-emerald-400">
                      قرارداد: {n.converted_contract_number}
                    </div>
                  )}
                </div>
              ),
            },
            {
              key: "act",
              header: "عملیات",
              render: (n) => (
                <div className="flex flex-wrap gap-1.5">
                  <Link
                    href={`/dashboard/negotiations/${n.id}`}
                    className="inline-flex h-7 items-center gap-1 rounded bg-teal-700 px-2.5 text-xs font-semibold text-white hover:bg-teal-800"
                  >
                    <ExternalLink className="h-3 w-3" />
                    میز کار پرونده
                  </Link>
                  <button
                    type="button"
                    onClick={() => setOffersTarget(n)}
                    className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 bg-white px-2 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                  >
                    <History className="h-3.5 w-3.5" />
                    پیشنهادها ({n.offers.length})
                  </button>
                </div>
              ),
            },
          ]}
        />
      )}

      {viewMode === "kanban" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          {KANBAN_LANES.map((lane) => {
            const laneItems = negotiations.filter((n) => lane.statuses.includes(n.status));
            return (
              <div
                key={lane.id}
                className="flex flex-col rounded-xl border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-slate-900/50"
              >
                <div className="mb-3 flex items-center justify-between border-b border-slate-200 pb-2 dark:border-slate-800">
                  <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
                    {lane.title}
                  </h3>
                  <span className="rounded bg-white px-2 py-0.5 font-mono text-[11px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    {formatNumberFa(laneItems.length)}
                  </span>
                </div>
                <div className="space-y-2.5">
                  {laneItems.length === 0 ? (
                    <div className="py-6 text-center text-[11px] text-slate-400">
                      پرونده‌ای در این ستون نیست
                    </div>
                  ) : (
                    laneItems.map((n) => (
                      <div
                        key={n.id}
                        className="rounded-lg border border-slate-200 bg-white p-3 text-xs shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-2"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <Link
                            href={`/dashboard/negotiations/${n.id}`}
                            className="font-bold text-slate-900 hover:text-teal-700 dark:text-slate-100"
                          >
                            {n.property_title}
                          </Link>
                          {n.is_followup_overdue && (
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-600" />
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          خریدار: {n.customer_name}
                        </div>
                        {Number(n.latest_proposed_price || 0) > 0 && (
                          <MoneyDisplay
                            amount={n.agreed_price || n.latest_proposed_price || "0"}
                            sourceCurrency="IRT"
                            className="font-bold text-teal-700 dark:text-teal-300"
                          />
                        )}
                        <div className="flex items-center justify-between pt-1">
                          <StatusText status={n.status} />
                          <Link
                            href={`/dashboard/negotiations/${n.id}`}
                            className="text-[11px] font-semibold text-teal-700 hover:underline dark:text-teal-400"
                          >
                            باز کردن
                          </Link>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {viewMode === "analytics" && analytics && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              توزیع پرونده‌ها در مراحل ۱۲ گانه مذاکره
            </h3>
            <div className="space-y-2.5">
              {analytics.stage_breakdown.map((sb) => {
                const pct = analytics.total_count
                  ? Math.round((sb.count / analytics.total_count) * 100)
                  : 0;
                return (
                  <div key={sb.status} className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        {translateStatus(sb.status)}
                      </span>
                      <span className="font-mono font-bold tabular-nums">
                        {formatNumberFa(sb.count)} ({formatNumberFa(pct)}٪)
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded bg-slate-100 dark:bg-slate-800">
                      <div className="h-full bg-teal-600" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              شاخص‌های بهره‌وری و علل عدم توافق
            </h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/50">
                <div className="text-slate-500">میانگین طول دوره مذاکره</div>
                <div className="mt-1 text-base font-bold tabular-nums">
                  {formatNumberFa(analytics.avg_duration_days)} روز
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/50">
                <div className="text-slate-500">میانگین رفت‌وبرگشت پیشنهاد</div>
                <div className="mt-1 text-base font-bold tabular-nums">
                  {formatNumberFa(analytics.avg_offers_per_negotiation)} نسخه
                </div>
              </div>
            </div>
            <div className="border-t border-slate-100 pt-3 dark:border-slate-800">
              <div className="mb-2 text-xs font-bold text-slate-700 dark:text-slate-300">
                دلایل ثبت‌شده رد یا لغو مذاکرات:
              </div>
              {analytics.failure_reasons.length === 0 ? (
                <p className="text-xs text-slate-500">مورد ناموفقی با دلیل ثبت نشده است.</p>
              ) : (
                <ul className="space-y-1.5 text-xs">
                  {analytics.failure_reasons.map((fr) => (
                    <li
                      key={fr.reason}
                      className="flex justify-between rounded bg-rose-50/70 px-3 py-1.5 text-rose-900 dark:bg-rose-950/40 dark:text-rose-200"
                    >
                      <span>{fr.reason}</span>
                      <span className="font-mono font-bold">{formatNumberFa(fr.count)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create Negotiation Modal */}
      <ModalDrawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="شروع پرونده مذاکره جدید"
        widthClass="max-w-xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={form.property_id}
            onChange={(e) => {
              const propId = e.target.value;
              const matched = (propsQ.data || []).find((p) => p.id === propId);
              setForm({
                ...form,
                property_id: propId,
                asking_price: matched ? matched.total_price : form.asking_price,
                deal_type_id: matched?.deal_type?.code || form.deal_type_id,
              });
            }}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب ملک...</option>
            {(propsQ.data || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.property_code} — {p.title}
              </option>
            ))}
          </select>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <select
              required
              value={form.customer_id}
              onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="">انتخاب خریدار / مستأجر...</option>
              {(custQ.data || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name}
                </option>
              ))}
            </select>
            <select
              value={form.owner_customer_id}
              onChange={(e) => setForm({ ...form, owner_customer_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="">مالک (تشخیص خودکار از ملک یا انتخاب)</option>
              {(custQ.data || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              type="number"
              placeholder="قیمت پایه ملک (Asking Price)"
              value={form.asking_price}
              onChange={(e) => setForm({ ...form, asking_price: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
            />
            <input
              type="number"
              placeholder="قیمت پیشنهادی اولیه"
              value={form.initial_price}
              onChange={(e) => setForm({ ...form, initial_price: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              placeholder="اقدام بعدی (مثلاً تماس با مالک)"
              value={form.next_action}
              onChange={(e) => setForm({ ...form, next_action: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
            <input
              type="datetime-local"
              value={form.next_followup_at}
              onChange={(e) => setForm({ ...form, next_followup_at: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
          </div>

          <textarea
            rows={2}
            placeholder="یادداشت و شرایط پرداخت پیشنهادی..."
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 p-3 text-sm"
          />

          <button
            type="submit"
            disabled={createMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {createMut.isPending ? "در حال ثبت..." : "ثبت پرونده مذاکره"}
          </button>
        </form>
      </ModalDrawer>

      {/* Quick Offers Modal */}
      <ModalDrawer
        open={!!offersTarget}
        onClose={() => setOffersTarget(null)}
        title={`تاریخچه پیشنهادها — ${offersTarget?.property_title || ""}`}
      >
        <div className="space-y-4">
          <div className="divide-y divide-slate-200 dark:divide-slate-800 rounded-lg border border-slate-200 dark:border-slate-800">
            {(offersTarget?.offers || []).map((o) => (
              <div key={o.id} className="flex items-center justify-between p-3 text-xs">
                <div>
                  <div className="font-bold text-slate-900 dark:text-slate-100">
                    نسخه {o.version_number} — طرف پیشنهاد: {o.offered_by}
                  </div>
                  <div className="text-slate-500 dark:text-slate-400">
                    <DateDisplay value={o.created_at} withTime />
                  </div>
                </div>
                <div className="text-left">
                  <MoneyDisplay
                    amount={o.proposed_price}
                    sourceCurrency={o.currency}
                    className="font-bold text-slate-900 dark:text-slate-100"
                  />
                  <div className="mt-1">
                    <StatusText status={o.status} />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              addOfferMut.mutate();
            }}
            className="space-y-3 border-t border-slate-200 dark:border-slate-800 pt-4"
          >
            <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
              ثبت پیشنهاد متقابل جدید
            </div>
            <div className="grid grid-cols-2 gap-3">
              <select
                value={offerForm.offered_by}
                onChange={(e) => setOfferForm({ ...offerForm, offered_by: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
              >
                <option value="BUYER">خریدار</option>
                <option value="SELLER">مالک / فروشنده</option>
              </select>
              <input
                type="number"
                value={offerForm.proposed_price}
                onChange={(e) => setOfferForm({ ...offerForm, proposed_price: e.target.value })}
                placeholder="مبلغ پیشنهادی"
                className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
              />
            </div>
            <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
              ثبت نسخه پیشنهاد متقابل
            </button>
          </form>

          {offersTarget &&
            ["OPEN", "COUNTER_OFFERED", "BUYER_OFFERED", "OWNER_COUNTERED", "BARGAINING", "PRE_AGREEMENT"].includes(
              offersTarget.status
            ) && (
              <div className="flex gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    respondMut.mutate({ id: offersTarget.id, status: "ACCEPTED" });
                    setOffersTarget(null);
                  }}
                  className="h-9 flex-1 rounded-lg bg-emerald-700 text-xs font-semibold text-white"
                >
                  توافق نهایی (ACCEPTED)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    respondMut.mutate({ id: offersTarget.id, status: "REJECTED" });
                    setOffersTarget(null);
                  }}
                  className="h-9 flex-1 rounded-lg border border-rose-200 bg-rose-50 text-xs font-semibold text-rose-700"
                >
                  رد مذاکره
                </button>
              </div>
            )}
        </div>
      </ModalDrawer>
    </div>
  );
}
