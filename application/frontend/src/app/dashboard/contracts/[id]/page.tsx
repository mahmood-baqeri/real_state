"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, FileText, Printer } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { ContractItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { useToast } from "@/components/ui/ToastProvider";

interface ContractDetail extends ContractItem {
  template_title?: string | null;
  terms_snapshot?: string;
  history?: {
    id: string;
    from_status: string;
    to_status: string;
    reason: string;
    changed_by_name: string;
    created_at: string;
  }[];
}

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();

  const detailQ = useQuery({
    queryKey: ["contract-detail", id, activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId && !!id,
    queryFn: async () =>
      (await apiFetch<ContractDetail>(`/api/v1/contracts/${id}`, {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const statusMut = useMutation({
    mutationFn: async (status: string) =>
      apiFetch(`/api/v1/contracts/${id}/status`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      toast.success("وضعیت قرارداد به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["contract-detail", id] });
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (detailQ.isLoading) return <LoadingState message="در حال بارگذاری پرونده قرارداد..." />;
  if (detailQ.error) return <ErrorState message={(detailQ.error as Error).message} onRetry={() => detailQ.refetch()} />;
  const contract = detailQ.data;
  if (!contract) return <ErrorState message="قرارداد یافت نشد." />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`قرارداد ${contract.contract_number}`}
        subtitle={`کد رهگیری داخلی: ${contract.internal_tracking_code} — ملک: ${contract.property_title}`}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "قراردادها", href: "/dashboard/contracts" },
          { label: contract.contract_number },
        ]}
        actions={
          <div className="flex flex-wrap gap-2 print:hidden">
            {contract.status === "DRAFT" && (
              <button
                type="button"
                onClick={() => statusMut.mutate("APPROVED")}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 text-xs font-semibold text-white hover:bg-amber-700"
              >
                تأیید متن حقوقی
              </button>
            )}
            {contract.status !== "SIGNED" && (
              <button
                type="button"
                onClick={() => statusMut.mutate("SIGNED")}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <CheckCircle2 className="h-4 w-4" />
                امضای نهایی
              </button>
            )}
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <Printer className="h-4 w-4" />
              چاپ قرارداد
            </button>
            <Link
              href="/dashboard/contracts"
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
              <FileText className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              ارکان مالی و شرایط قرارداد
            </h2>
            <StatusText status={contract.status} />
          </div>
          <dl className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-3">
            <div>
              <dt className="text-slate-500 dark:text-slate-400">نوع قرارداد / معامله</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{contract.deal_type_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">مبلغ کل قرارداد</dt>
              <dd className="mt-1 font-bold text-teal-800 dark:text-teal-300">
                <MoneyDisplay amount={contract.amount} sourceCurrency={contract.currency} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">پیش‌پرداخت</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
                <MoneyDisplay amount={contract.advance_payment} sourceCurrency={contract.currency} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">مبلغ باقیمانده</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
                <MoneyDisplay amount={contract.remaining_amount} sourceCurrency={contract.currency} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">تاریخ شروع</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100"><DateDisplay value={contract.start_date} /></dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">ملک مرتبط</dt>
              <dd className="mt-1">
                <Link
                  href={`/dashboard/properties/${contract.property_id}`}
                  className="font-semibold text-teal-700 dark:text-teal-400 hover:underline"
                >
                  {contract.property_code} — {contract.property_title}
                </Link>
              </dd>
            </div>
          </dl>

          <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
            <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 mb-2">طرفین قرارداد</h3>
            {contract.parties.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">طرف قراردادی ثبت نشده است.</p>
            ) : (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {contract.parties.map((p) => (
                  <div key={p.id} className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 p-3 text-xs flex justify-between">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">{p.full_name}</span>
                    <span className="font-mono text-slate-500 dark:text-slate-400">{p.party_role}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {contract.terms_snapshot && (
            <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
              <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 mb-2">متن و شروط قرارداد</h3>
              <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 dark:bg-slate-800/60 p-4 text-xs leading-relaxed text-slate-800 dark:text-slate-200">
                {contract.terms_snapshot}
              </pre>
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-3">
            تاریخچه تغییرات وضعیت
          </h2>
          {(contract.history || []).length === 0 ? (
            <p className="text-xs text-slate-500 dark:text-slate-400">تغییر وضعیتی ثبت نشده است.</p>
          ) : (
            <div className="space-y-2.5 text-xs">
              {(contract.history || []).map((h) => (
                <div key={h.id} className="rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3">
                  <div className="flex items-center justify-between font-semibold text-slate-900 dark:text-slate-100">
                    <span>{h.from_status || "—"} ← {h.to_status}</span>
                    <DateDisplay value={h.created_at} />
                  </div>
                  <div className="mt-1 text-slate-500 dark:text-slate-400">توسط: {h.changed_by_name}</div>
                  {h.reason && <div className="mt-1 text-slate-700 dark:text-slate-300">{h.reason}</div>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
