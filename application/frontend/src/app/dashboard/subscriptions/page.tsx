"use client";

import React, { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CreditCard, ExternalLink, ShieldCheck } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CurrencyCode, PaymentGatewayItem } from "@/lib/types";
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
  order_id?: string;
  provider_key: string;
  is_sandbox?: boolean;
  redirect_url: string;
  amount: string;
  currency: CurrencyCode;
  subscription_id: string;
  idempotent_replay?: boolean;
}

const GATEWAY_LABELS: Record<string, string> = {
  zarinpal: "زرین‌پال (Zarinpal v4)",
  zibal: "زیبال (Zibal v1)",
  idpay: "آیدی‌پی (IDPay v1.1)",
  sandbox: "درگاه آزمایشی داخلی (Sandbox)",
};

export default function SubscriptionsPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [billingCycle, setBillingCycle] = useState<"MONTHLY" | "ANNUAL">("MONTHLY");
  const [selectedGateway, setSelectedGateway] = useState<string>("sandbox");
  const [pendingCheckout, setPendingCheckout] = useState<CheckoutResult | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const callbackHandledRef = useRef(false);

  const plansQ = useQuery({
    queryKey: ["subscription-plans"],
    queryFn: async () => (await apiFetch<PlanItem[]>("/api/v1/subscriptions/plans")).data,
  });

  const gatewaysQ = useQuery({
    queryKey: ["active-payment-gateways", activeAgencyId],
    queryFn: async () =>
      (
        await apiFetch<PaymentGatewayItem[]>("/api/v1/payments/gateways/active", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  useEffect(() => {
    const items = gatewaysQ.data || [];
    if (items.length > 0 && !items.some((g) => g.provider_key === selectedGateway)) {
      setSelectedGateway(items[0].provider_key);
    }
  }, [gatewaysQ.data, selectedGateway]);

  const currentQ = useQuery({
    queryKey: ["subscriptions-current", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<CurrentSubItem[]>("/api/v1/subscriptions/current", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const txQ = useQuery({
    queryKey: ["payment-transactions", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<TransactionItem[]>("/api/v1/payments/transactions", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const checkoutMut = useMutation({
    mutationFn: async (planCode: string) => {
      const nonce =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID().slice(0, 8)
          : String(Date.now());
      const callbackUrl =
        typeof window !== "undefined"
          ? `${window.location.origin}/dashboard/subscriptions`
          : "/dashboard/subscriptions";
      return (
        await apiFetch<CheckoutResult>("/api/v1/payments/initiate", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({
            plan_code: planCode,
            billing_cycle: billingCycle,
            provider_key: selectedGateway,
            callback_url: callbackUrl,
            idempotency_key: `sub-${planCode}-${billingCycle}-${selectedGateway}-${nonce}`,
          }),
        })
      ).data;
    },
    onSuccess: (res) => {
      setErrMsg(null);
      setPendingCheckout(res);
      const gwTitle = GATEWAY_LABELS[res.provider_key] || res.provider_key;
      setNotice(`تراکنش درگاه ${gwTitle} با موفقیت ایجاد شد. آماده انتقال یا تأیید پرداخت است.`);
      qc.invalidateQueries({ queryKey: ["payment-transactions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const verifyMut = useMutation({
    mutationFn: async ({ authority, status = "OK" }: { authority: string; status?: string }) =>
      (
        await apiFetch<{
          transaction_id: string;
          status: string;
          reference_id: string;
          error_message?: string;
        }>("/api/v1/payments/verify", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({ authority, status }),
        })
      ).data,
    onSuccess: (res) => {
      setPendingCheckout(null);
      if (res.status === "PAID") {
        setErrMsg(null);
        setNotice(`تراکنش با موفقیت تأیید شد (کد مرجع: ${res.reference_id || "ثبت‌شده"}) و اشتراک فعال گردید.`);
      } else {
        setNotice(null);
        setErrMsg(res.error_message || "تأیید تراکنش از سوی درگاه ناموفق بود.");
      }
      qc.invalidateQueries({ queryKey: ["subscriptions-current"] });
      qc.invalidateQueries({ queryKey: ["payment-transactions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  // Handle callback return parameters automatically (?Authority=...&Status=... / ?trackId=... / ?id=...)
  useEffect(() => {
    if (callbackHandledRef.current || !accessToken || !activeAgencyId || typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const auth =
      params.get("Authority") ||
      params.get("authority") ||
      params.get("trackId") ||
      params.get("id");
    if (!auth) return;
    const rawStatus =
      params.get("Status") ||
      params.get("status") ||
      (params.get("success") === "1" ? "OK" : params.get("success") === "0" ? "NOK" : "OK");
    callbackHandledRef.current = true;
    verifyMut.mutate({ authority: auth, status: rawStatus });
    window.history.replaceState({}, "", window.location.pathname);
  }, [accessToken, activeAgencyId, verifyMut]);

  const canCheckout =
    !!activeAgencyId &&
    ["SUPER_ADMIN", "AGENCY_MANAGER", "AGENCY_ACCOUNTANT"].includes(effectiveRole);

  const gateways = gatewaysQ.data || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="اشتراک سازمانی و درگاه‌های پرداخت ایرانی"
        subtitle="انتخاب پلن آژانس، پرداخت امن از طریق درگاه‌های زرین‌پال، زیبال، آیدی‌پی یا سندباکس و پایش تراکنش‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "اشتراک و پرداخت" }]}
        actions={
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 dark:border-slate-800 dark:bg-slate-900">
            <button
              type="button"
              onClick={() => setBillingCycle("MONTHLY")}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                billingCycle === "MONTHLY"
                  ? "bg-teal-700 text-white dark:bg-teal-600"
                  : "text-slate-600 dark:text-slate-400"
              }`}
            >
              ماهانه
            </button>
            <button
              type="button"
              onClick={() => setBillingCycle("ANNUAL")}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                billingCycle === "ANNUAL"
                  ? "bg-teal-700 text-white dark:bg-teal-600"
                  : "text-slate-600 dark:text-slate-400"
              }`}
            >
              سالانه (به‌صرفه‌تر)
            </button>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {/* Gateway Selector */}
      <div className="surface-card rounded-xl p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              انتخاب درگاه پرداخت فعال
            </h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              مبلغ پرداختی مستقیماً در سمت سرور از روی تعرفه رسمی پلن محاسبه می‌شود.
            </p>
          </div>
          <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
            {gateways.length} درگاه فعال
          </span>
        </div>

        {gatewaysQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {gateways.map((gw) => {
              const selected = selectedGateway === gw.provider_key;
              return (
                <button
                  key={gw.id}
                  type="button"
                  onClick={() => setSelectedGateway(gw.provider_key)}
                  className={`flex flex-col justify-between rounded-xl border p-3.5 text-right transition-all ${
                    selected
                      ? "border-teal-600 bg-teal-50/70 ring-1 ring-teal-600 dark:border-teal-500 dark:bg-teal-950/40"
                      : "border-slate-200 bg-slate-50/70 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-800/40 dark:hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                      {gw.display_name}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${
                        gw.is_sandbox
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                          : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                      }`}
                    >
                      {gw.is_sandbox ? "Sandbox" : "Live"}
                    </span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
                    {gw.description || "آماده پردازش تراکنش‌های اشتراک"}
                  </p>
                  <div className="mt-2 flex items-center justify-between border-t border-slate-200/70 pt-2 text-[10px] text-slate-500 dark:border-slate-700/70 dark:text-slate-400">
                    <span className="font-mono">{gw.provider_key}</span>
                    <span>{selected ? "انتخاب‌شده" : "انتخاب"}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Pending Checkout Card */}
      {pendingCheckout && (
        <div className="flex flex-col items-start justify-between gap-4 rounded-xl border border-amber-300 bg-amber-50/90 p-5 dark:border-amber-800/70 dark:bg-amber-950/40 sm:flex-row sm:items-center">
          <div className="space-y-1 text-sm">
            <div className="font-bold text-amber-950 dark:text-amber-200">
              درخواست پرداخت ({GATEWAY_LABELS[pendingCheckout.provider_key] || pendingCheckout.provider_key}) آماده تکمیل است
            </div>
            <div className="text-xs text-amber-900 dark:text-amber-300">
              شناسه پیگیری (Authority):{" "}
              <span className="font-mono font-bold">{pendingCheckout.authority}</span>
              {pendingCheckout.order_id && (
                <>
                  {" "}
                  | سفارش: <span className="font-mono font-bold">{pendingCheckout.order_id}</span>
                </>
              )}{" "}
              | مبلغ:{" "}
              <MoneyDisplay
                amount={pendingCheckout.amount}
                sourceCurrency={pendingCheckout.currency}
                className="font-bold tabular-nums"
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {pendingCheckout.redirect_url && !pendingCheckout.is_sandbox && (
              <a
                href={pendingCheckout.redirect_url}
                rel="noopener noreferrer"
                className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <ExternalLink className="h-4 w-4" />
                انتقال به صفحه بانک
              </a>
            )}
            <button
              type="button"
              disabled={verifyMut.isPending}
              onClick={() =>
                verifyMut.mutate({ authority: pendingCheckout.authority, status: "OK" })
              }
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-emerald-700 px-4 text-xs font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              <ShieldCheck className="h-4 w-4" />
              {pendingCheckout.is_sandbox ? "شبیه‌سازی و تأیید پرداخت" : "استعلام و تأیید تراکنش"}
            </button>
          </div>
        </div>
      )}

      {/* Plans Grid */}
      {plansQ.isLoading ? (
        <LoadingState />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {(plansQ.data || []).map((p) => {
            const price = billingCycle === "ANNUAL" ? p.annual_price : p.monthly_price;
            return (
              <div
                key={p.id}
                className="surface-card flex flex-col justify-between rounded-xl p-5 transition-shadow hover:shadow-md"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                      {p.name_fa}
                    </h3>
                    <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                      {p.code}
                    </span>
                  </div>
                  <div className="text-xl font-bold text-teal-800 dark:text-teal-300 tabular-nums">
                    <MoneyDisplay amount={price} sourceCurrency={p.currency} />
                    <span className="mr-1 text-xs font-normal text-slate-500 dark:text-slate-400">
                      / {billingCycle === "ANNUAL" ? "سالانه" : "ماهانه"}
                    </span>
                  </div>
                  <ul className="space-y-2 border-t border-slate-100 pt-3 text-xs text-slate-700 dark:border-slate-800 dark:text-slate-300">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-teal-700 dark:text-teal-400" />
                      <span className="tabular-nums">
                        حداکثر مشاوران فعال: {formatNumberFa(p.max_agents)} نفر
                      </span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-teal-700 dark:text-teal-400" />
                      <span className="tabular-nums">
                        حداکثر فایل ملکی فعال: {formatNumberFa(p.max_properties)} ملک
                      </span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-teal-700 dark:text-teal-400" />
                      <span className="tabular-nums">
                        سقف شعب آژانس: {formatNumberFa(p.max_branches)} شعبه
                      </span>
                    </li>
                  </ul>
                </div>

                {canCheckout && (
                  <button
                    type="button"
                    disabled={checkoutMut.isPending}
                    onClick={() => checkoutMut.mutate(p.code)}
                    className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-teal-700 text-xs font-semibold text-white transition-colors hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
                  >
                    <CreditCard className="h-4 w-4" />
                    پرداخت با {GATEWAY_LABELS[selectedGateway]?.split(" ")[0] || selectedGateway}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Active Subscriptions */}
      <div className="surface-card rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">اشتراک‌های فعلی</h3>
        {(currentQ.data || []).length === 0 ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            اشتراک فعالی ثبت نشده است.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {currentQ.data?.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-xs dark:border-slate-800 dark:bg-slate-800/60"
              >
                <div>
                  <div className="font-bold text-slate-900 dark:text-slate-100">
                    {s.agency_name} — {s.plan_name_fa}
                  </div>
                  <div className="mt-1 text-slate-500 dark:text-slate-400">
                    شروع: <DateDisplay value={s.starts_at} /> | انقضا:{" "}
                    <DateDisplay value={s.expires_at} />
                  </div>
                </div>
                <StatusText status={s.status} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Transactions Ledger Table */}
      <DataTable
        rows={txQ.data || []}
        rowKey={(t) => t.id}
        isLoading={txQ.isLoading}
        error={txQ.error instanceof Error ? txQ.error.message : null}
        searchPlaceholder="جستجو در کد پیگیری، مرجع یا نام درگاه..."
        searchableText={(t) => `${t.agency_name} ${t.provider_key} ${t.authority} ${t.reference_id}`}
        exportFileName="payment-transactions"
        columns={[
          { key: "ag", header: "آژانس", render: (t) => t.agency_name },
          {
            key: "prov",
            header: "درگاه",
            render: (t) => (
              <span className="font-mono text-xs font-semibold text-slate-700 dark:text-slate-300">
                {t.provider_key}
              </span>
            ),
          },
          {
            key: "auth",
            header: "شناسه Authority",
            render: (t) => <span className="font-mono text-xs">{t.authority}</span>,
          },
          {
            key: "ref",
            header: "کد مرجع بانکی",
            render: (t) => <span className="font-mono text-xs">{t.reference_id || "—"}</span>,
          },
          {
            key: "amt",
            header: "مبلغ",
            render: (t) => (
              <MoneyDisplay
                amount={t.amount}
                sourceCurrency={t.currency}
                className="font-semibold tabular-nums"
              />
            ),
          },
          { key: "st", header: "وضعیت", render: (t) => <StatusText status={t.status} /> },
          { key: "dt", header: "تاریخ", render: (t) => <DateDisplay value={t.created_at} withTime /> },
        ]}
      />
    </div>
  );
}
