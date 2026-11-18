"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CreditCard, ShieldCheck } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CurrencyCode } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";
import { formatNumberFa } from "@/lib/formatters";

interface PlanItem {
  id: string;
  code: string;
  name_fa: string;
  name_en: string;
  currency: CurrencyCode;
  monthly_price: string;
  annual_price: string;
  max_agents: number;
  max_properties: number;
  max_branches: number;
  features: Record<string, unknown>;
}

interface CurrentSubItem {
  id: string;
  agency_id: string;
  agency_name: string;
  plan_code: string;
  plan_name_fa: string;
  billing_cycle: string;
  starts_at: string;
  expires_at: string;
  status: string;
}

interface TransactionItem {
  id: string;
  agency_name: string;
  provider_key: string;
  authority: string;
  reference_id: string;
  currency: CurrencyCode;
  amount: string;
  status: string;
  created_at: string;
}

interface CheckoutResult {
  transaction_id: string;
  authority: string;
  redirect_url: string;
  amount: string;
  currency: CurrencyCode;
  subscription_id: string;
}

export default function SubscriptionsPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [billingCycle, setBillingCycle] = useState<"MONTHLY" | "ANNUAL">("MONTHLY");
  const [pendingCheckout, setPendingCheckout] = useState<CheckoutResult | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const plansQ = useQuery({
    queryKey: ["subscription-plans"],
    queryFn: async () => (await apiFetch<PlanItem[]>("/api/v1/subscriptions/plans")).data,
  });

  const currentQ = useQuery({
    queryKey: ["subscriptions-current", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<CurrentSubItem[]>("/api/v1/subscriptions/current", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const txQ = useQuery({
    queryKey: ["payment-transactions", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<TransactionItem[]>("/api/v1/payments/transactions", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const checkoutMut = useMutation({
    mutationFn: async (planCode: string) =>
      (await apiFetch<CheckoutResult>("/api/v1/subscriptions/checkout", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          plan_code: planCode,
          billing_cycle: billingCycle,
          provider_key: "sandbox",
        }),
      })).data,
    onSuccess: (res) => {
      setErrMsg(null);
      setPendingCheckout(res);
      setNotice("درخواست پرداخت آزمایشی (Sandbox) ایجاد شد. برای فعال‌سازی اشتراک، دکمه تأیید پرداخت را بزنید.");
      qc.invalidateQueries({ queryKey: ["payment-transactions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const verifyMut = useMutation({
    mutationFn: async (authority: string) =>
      apiFetch("/api/v1/subscriptions/verify", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ authority }),
      }),
    onSuccess: () => {
      setPendingCheckout(null);
      setErrMsg(null);
      setNotice("تراکنش تأیید و اشتراک آژانس فعال شد.");
      qc.invalidateQueries({ queryKey: ["subscriptions-current"] });
      qc.invalidateQueries({ queryKey: ["payment-transactions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const canCheckout = !!activeAgencyId && ["SUPER_ADMIN", "AGENCY_MANAGER", "AGENCY_ACCOUNTANT"].includes(effectiveRole);

  return (
    <div className="space-y-6">
      <PageHeader
        title="اشتراک و درگاه پرداخت"
        subtitle="انتخاب پلن سازمانی آژانس، پرداخت از طریق آداپتر درگاه پرداخت و مشاهده تاریخچه تراکنش‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "اشتراک و پرداخت" }]}
        actions={
          <div className="inline-flex rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-1">
            <button
              type="button"
              onClick={() => setBillingCycle("MONTHLY")}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
                billingCycle === "MONTHLY" ? "bg-teal-700 text-white" : "text-slate-600 dark:text-slate-400"
              }`}
            >
              ماهانه
            </button>
            <button
              type="button"
              onClick={() => setBillingCycle("ANNUAL")}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
                billingCycle === "ANNUAL" ? "bg-teal-700 text-white" : "text-slate-600 dark:text-slate-400"
              }`}
            >
              سالانه
            </button>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {pendingCheckout && (
        <div className="flex flex-col items-start justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50 p-5 sm:flex-row sm:items-center">
          <div className="space-y-1 text-sm">
            <div className="font-bold text-amber-950">درگاه پرداخت آزمایشی (Sandbox) آماده تأیید است</div>
            <div className="text-xs text-amber-900">
              کد پیگیری (Authority): <span className="font-mono font-bold">{pendingCheckout.authority}</span> | مبلغ:{" "}
              <MoneyDisplay amount={pendingCheckout.amount} sourceCurrency={pendingCheckout.currency} className="font-bold" />
            </div>
          </div>
          <button
            type="button"
            disabled={verifyMut.isPending}
            onClick={() => verifyMut.mutate(pendingCheckout.authority)}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-emerald-700 px-4 text-xs font-semibold text-white hover:bg-emerald-800"
          >
            <ShieldCheck className="h-4 w-4" />
            تأیید و فعال‌سازی اشتراک
          </button>
        </div>
      )}

      {plansQ.isLoading ? (
        <LoadingState />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {(plansQ.data || []).map((p) => {
            const price = billingCycle === "ANNUAL" ? p.annual_price : p.monthly_price;
            return (
              <div key={p.id} className="flex flex-col justify-between rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">{p.name_fa}</h3>
                    <span className="font-mono text-xs text-slate-500 dark:text-slate-400">{p.code}</span>
                  </div>
                  <div className="text-xl font-bold text-teal-800 dark:text-teal-300">
                    <MoneyDisplay amount={price} sourceCurrency={p.currency} />
                    <span className="mr-1 text-xs font-normal text-slate-500 dark:text-slate-400">
                      / {billingCycle === "ANNUAL" ? "سالانه" : "ماهانه"}
                    </span>
                  </div>
                  <ul className="space-y-2 border-t border-slate-100 dark:border-slate-800 pt-3 text-xs text-slate-700 dark:text-slate-300">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                      حداکثر مشاوران فعال: {formatNumberFa(p.max_agents)} نفر
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                      حداکثر فایل ملکی فعال: {formatNumberFa(p.max_properties)} ملک
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                      سقف شعب آژانس: {formatNumberFa(p.max_branches)} شعبه
                    </li>
                  </ul>
                </div>

                {canCheckout && (
                  <button
                    type="button"
                    disabled={checkoutMut.isPending}
                    onClick={() => checkoutMut.mutate(p.code)}
                    className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                  >
                    <CreditCard className="h-4 w-4" />
                    انتخاب و خرید اشتراک
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">اشتراک‌های فعلی</h3>
        {(currentQ.data || []).length === 0 ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">اشتراک فعالی ثبت نشده است.</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {currentQ.data?.map((s) => (
              <div key={s.id} className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 p-3.5 text-xs">
                <div>
                  <div className="font-bold text-slate-900 dark:text-slate-100">{s.agency_name} — {s.plan_name_fa}</div>
                  <div className="mt-1 text-slate-500 dark:text-slate-400">
                    شروع: <DateDisplay value={s.starts_at} /> | انقضا: <DateDisplay value={s.expires_at} />
                  </div>
                </div>
                <StatusText status={s.status} />
              </div>
            ))}
          </div>
        )}
      </div>

      <DataTable
        rows={txQ.data || []}
        rowKey={(t) => t.id}
        isLoading={txQ.isLoading}
        error={txQ.error instanceof Error ? txQ.error.message : null}
        searchPlaceholder="جستجو در کد رهگیری یا درگاه..."
        columns={[
          { key: "ag", header: "آژانس", render: (t) => t.agency_name },
          { key: "prov", header: "درگاه", render: (t) => <span className="font-mono text-xs">{t.provider_key}</span> },
          { key: "auth", header: "کد Authority", render: (t) => <span className="font-mono text-xs">{t.authority}</span> },
          { key: "amt", header: "مبلغ", render: (t) => <MoneyDisplay amount={t.amount} sourceCurrency={t.currency} className="font-semibold" /> },
          { key: "st", header: "وضعیت", render: (t) => <StatusText status={t.status} /> },
          { key: "dt", header: "تاریخ", render: (t) => <DateDisplay value={t.created_at} withTime /> },
        ]}
      />
    </div>
  );
}
