// Path: frontend/src/app/dashboard/deals/[id]/page.tsx

"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, Handshake, Wallet } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { DealItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { useToast } from "@/components/ui/ToastProvider";

interface DealDetail extends DealItem {
  ledger: {
    deal_amount: string;
    total_received: string;
    total_paid: string;
    receivable_balance: string;
  } | null;
  commission: {
    id: string;
    gross_commission: string;
    net_distributable: string;
    status: string;
  } | null;
}

export default function DealDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();

  const detailQ = useQuery({
    queryKey: ["deal-detail", id, activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId && !!id,
    queryFn: async () =>
      (await apiFetch<DealDetail>(`/api/v1/deals/${id}`, {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const closeWonMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/deals/${id}/close`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ auto_calculate_commission: true }),
      }),
    onSuccess: () => {
      toast.success("معامله مختومه (Closed Won) شد و کمیسیون آن محاسبه گردید.");
      qc.invalidateQueries({ queryKey: ["deal-detail", id] });
      qc.invalidateQueries({ queryKey: ["deals"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (detailQ.isLoading) return <LoadingState message="در حال بارگذاری پرونده معامله..." />;
  if (detailQ.error) return <ErrorState message={(detailQ.error as Error).message} onRetry={() => detailQ.refetch()} />;
  const deal = detailQ.data;
  if (!deal) return <ErrorState message="معامله یافت نشد." />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`پرونده معامله ${deal.deal_code}`}
        subtitle={`ملک: ${deal.property_title} — قرارداد: ${deal.contract_number}`}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "معاملات", href: "/dashboard/deals" },
          { label: deal.deal_code },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            {deal.status !== "CLOSED_WON" && (
              <button
                type="button"
                onClick={() => closeWonMut.mutate()}
                disabled={closeWonMut.isPending}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-emerald-700 px-3.5 text-xs font-semibold text-white hover:bg-emerald-800"
              >
                <CheckCircle2 className="h-4 w-4" />
                اختتام موفق و محاسبه کمیسیون
              </button>
            )}
            <Link
              href="/dashboard/deals"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
              <Handshake className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              مشخصات پرونده معامله
            </h2>
            <StatusText status={deal.status} />
          </div>
          <dl className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-3">
            <div>
              <dt className="text-slate-500 dark:text-slate-400">ارزش کل معامله</dt>
              <dd className="mt-1 font-bold text-teal-800 dark:text-teal-300">
                <MoneyDisplay amount={deal.deal_value} sourceCurrency={deal.currency} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">مشاور اصلی</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{deal.primary_agent_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">مشاور همکار</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{deal.co_agent_name || "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">ملک مرتبط</dt>
              <dd className="mt-1">
                <Link href={`/dashboard/properties/${deal.property_id}`} className="font-semibold text-teal-700 dark:text-teal-400 hover:underline">
                  {deal.property_code} — {deal.property_title}
                </Link>
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">قرارداد مرتبط</dt>
              <dd className="mt-1">
                <Link href={`/dashboard/contracts/${deal.contract_id}`} className="font-mono font-semibold text-teal-700 dark:text-teal-400 hover:underline">
                  {deal.contract_number}
                </Link>
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">تاریخ اختتام</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100"><DateDisplay value={deal.closed_at} /></dd>
            </div>
          </dl>
        </section>

        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-3">
            <Wallet className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            کاردکس مالی و کمیسیون
          </h2>
          {deal.ledger ? (
            <dl className="space-y-2.5 text-xs">
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">مبلغ کل کاردکس:</dt>
                <dd className="font-bold"><MoneyDisplay amount={deal.ledger.deal_amount} sourceCurrency={deal.currency} /></dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">دریافتی ثبت‌شده:</dt>
                <dd className="font-semibold text-emerald-700 dark:text-emerald-400"><MoneyDisplay amount={deal.ledger.total_received} sourceCurrency={deal.currency} /></dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">مانده دریافتنی:</dt>
                <dd className="font-semibold text-amber-700 dark:text-amber-400"><MoneyDisplay amount={deal.ledger.receivable_balance} sourceCurrency={deal.currency} /></dd>
              </div>
            </dl>
          ) : (
            <p className="text-xs text-slate-500 dark:text-slate-400">کاردکس مالی ایجاد نشده است.</p>
          )}
          <div className="border-t border-slate-200 dark:border-slate-800 pt-3 text-xs">
            <div className="font-bold text-slate-900 dark:text-slate-100 mb-2">کمیسیون محاسبه‌شده</div>
            {deal.commission ? (
              <div className="space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">ناخالص کمیسیون:</span>
                  <MoneyDisplay amount={deal.commission.gross_commission} sourceCurrency={deal.currency} className="font-semibold" />
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">خالص قابل تقسیم:</span>
                  <MoneyDisplay amount={deal.commission.net_distributable} sourceCurrency={deal.currency} className="font-bold text-teal-800 dark:text-teal-300" />
                </div>
                <div className="flex justify-between pt-1">
                  <span className="text-slate-500 dark:text-slate-400">وضعیت تسویه:</span>
                  <StatusText status={deal.commission.status} />
                </div>
              </div>
            ) : (
              <p className="text-slate-500 dark:text-slate-400">پس از اختتام معامله محاسبه می‌شود.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
