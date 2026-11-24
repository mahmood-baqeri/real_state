"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { ContractItem, DealItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function DealsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    deal_code: `DL-${Math.floor(1000 + Math.random() * 9000)}`,
    contract_id: "",
    deal_value: "",
  });

  const dealsQ = useQuery({
    queryKey: ["deals", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<DealItem[]>("/api/v1/deals", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const financeSummaryQ = useQuery({
    queryKey: ["deals-financial-summary", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () => (await apiFetch<{ deal_count: number; currencies: Array<{ currency: string; deal_amount: string; received: string; paid: string; receivable: string; net_profit: string; ledger_count: number; open_count: number; partial_count: number; settled_count: number }> }>(
      "/api/v1/deals/financial-summary", { token: accessToken, agencyId: activeAgencyId }
    )).data,
  });

  const contractsQ = useQuery({
    queryKey: ["contracts-for-deals", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<ContractItem[]>("/api/v1/contracts", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/deals", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          deal_code: form.deal_code,
          contract_id: form.contract_id,
          deal_value: form.deal_value || undefined,
        }),
      }),
    onSuccess: () => {
      setModalOpen(false);
      setNotice("پرونده معامله و کاردکس مالی آن ایجاد شد.");
      qc.invalidateQueries({ queryKey: ["deals"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const closeWonMut = useMutation({
    mutationFn: async (dealId: string) =>
      apiFetch(`/api/v1/deals/${dealId}/close`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ auto_calculate_commission: true }),
      }),
    onSuccess: () => {
      setNotice("معامله با موفقیت مختومه (Closed Won) شد و کمیسیون آن محاسبه گردید.");
      qc.invalidateQueries({ queryKey: ["deals"] });
      qc.invalidateQueries({ queryKey: ["commissions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="مدیریت معاملات و کاردکس"
        subtitle="ثبت معامله متصل به قرارداد و اختتام معامله همراه با محاسبه خودکار کمیسیون"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "معاملات" }]}
        actions={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white"
          >
            <Plus className="h-4 w-4" />
            ثبت معامله جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">خلاصه مالی معاملات</h2>
          <span className="text-xs text-slate-500">{financeSummaryQ.data?.deal_count ?? 0} معامله قابل دسترس</span>
        </div>
        {financeSummaryQ.isLoading ? <p className="text-xs text-slate-500">در حال دریافت خلاصه مالی...</p> : null}
        {financeSummaryQ.error instanceof Error ? <p className="text-xs text-rose-600">خلاصه مالی بارگذاری نشد: {financeSummaryQ.error.message}</p> : null}
        {(financeSummaryQ.data?.currencies || []).length === 0 && !financeSummaryQ.isLoading ? <p className="text-xs text-slate-500">برای معاملات قابل دسترس، کاردکس مالی ثبت نشده است.</p> : null}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {(financeSummaryQ.data?.currencies || []).map((f) => (
            <div key={f.currency} className="rounded-lg border border-slate-100 p-3 dark:border-slate-800">
              <div className="mb-2 text-xs font-semibold text-teal-700 dark:text-teal-400">ارز: {f.currency}</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><div className="text-slate-500">ارزش معاملات</div><div className="font-semibold">{Number(f.deal_amount).toLocaleString("fa-IR")}</div></div>
                <div><div className="text-slate-500">دریافت‌شده</div><div className="font-semibold">{Number(f.received).toLocaleString("fa-IR")}</div></div>
                <div><div className="text-slate-500">مانده دریافت</div><div className="font-semibold">{Number(f.receivable).toLocaleString("fa-IR")}</div></div>
                <div><div className="text-slate-500">پرداخت‌شده</div><div className="font-semibold">{Number(f.paid).toLocaleString("fa-IR")}</div></div>
                <div><div className="text-slate-500">سود خالص</div><div className="font-semibold">{Number(f.net_profit).toLocaleString("fa-IR")}</div></div>
                <div><div className="text-slate-500">تسویه / ناقص / باز</div><div className="font-semibold">{f.settled_count} / {f.partial_count} / {f.open_count}</div></div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <DataTable
        rows={dealsQ.data || []}
        rowKey={(d) => d.id}
        isLoading={dealsQ.isLoading}
        error={dealsQ.error instanceof Error ? dealsQ.error.message : null}
        searchPlaceholder="جستجو در کد معامله، قرارداد یا ملک..."
        exportFileName="deals"
        columns={[
          {
            key: "code",
            header: "کد معامله",
            render: (d) => (
              <Link href={`/dashboard/deals/${d.id}`} className="font-mono text-xs font-semibold text-teal-700 dark:text-teal-400 hover:underline">
                {d.deal_code}
              </Link>
            ),
          },
          { key: "prop", header: "ملک", render: (d) => d.property_title },
          {
            key: "cnt",
            header: "شماره قرارداد",
            render: (d) => (
              <Link href={`/dashboard/contracts/${d.contract_id}`} className="font-mono text-xs text-slate-700 dark:text-slate-300 hover:underline">
                {d.contract_number}
              </Link>
            ),
          },
          { key: "agent", header: "مشاور اصلی", render: (d) => d.primary_agent_name },
          { key: "val", header: "ارزش معامله", render: (d) => <MoneyDisplay amount={d.deal_value} sourceCurrency={d.currency} className="font-bold text-xs" /> },
          { key: "status", header: "وضعیت", render: (d) => <StatusText status={d.status} /> },
          { key: "dt", header: "تاریخ اختتام", render: (d) => <DateDisplay value={d.closed_at} /> },
          {
            key: "act",
            header: "عملیات",
            render: (d) =>
              d.status !== "CLOSED_WON" ? (
                <button
                  type="button"
                  onClick={() => closeWonMut.mutate(d.id)}
                  className="inline-flex h-7 items-center gap-1 rounded bg-emerald-700 px-2.5 text-xs font-semibold text-white hover:bg-emerald-800"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  اختتام موفق و کمیسیون
                </button>
              ) : (
                "—"
              ),
          },
        ]}
      />

      <ModalDrawer open={modalOpen} onClose={() => setModalOpen(false)} title="ثبت معامله از قرارداد">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="کد معامله"
            value={form.deal_code}
            onChange={(e) => setForm({ ...form, deal_code: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 font-mono text-sm"
          />
          <select
            required
            value={form.contract_id}
            onChange={(e) => setForm({ ...form, contract_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب قرارداد مرتبط...</option>
            {(contractsQ.data || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.contract_number} — {c.property_title}
              </option>
            ))}
          </select>
          <input
            type="number"
            placeholder="مبلغ معامله (در صورت خالی بودن از قرارداد خوانده می‌شود)"
            value={form.deal_value}
            onChange={(e) => setForm({ ...form, deal_value: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت معامله
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
