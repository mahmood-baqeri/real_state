// Path: frontend/src/app/dashboard/payroll/page.tsx

"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileSpreadsheet, Plus, Printer, Wallet } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { PayrollCycleItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";
import { formatNumberFa } from "@/lib/formatters";

export default function PayrollPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedCycle, setSelectedCycle] = useState<PayrollCycleItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    title: "دوره حقوق و کمیسیون ماه جاری",
    period_start: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10),
    period_end: new Date().toISOString().slice(0, 10),
  });

  const canManage = ["SUPER_ADMIN", "AGENCY_MANAGER", "AGENCY_ACCOUNTANT"].includes(effectiveRole);

  const cyclesQ = useQuery({
    queryKey: ["payroll-cycles", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<PayrollCycleItem[]>("/api/v1/payroll/cycles", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/payroll/cycles", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          title: form.title,
          period_start: `${form.period_start}T00:00:00Z`,
          period_end: `${form.period_end}T23:59:59Z`,
        }),
      }),
    onSuccess: () => {
      setCreateOpen(false);
      setErrMsg(null);
      setNotice("دوره حقوق و دستمزد ایجاد و فیش‌های پرسنل محاسبه شد.");
      qc.invalidateQueries({ queryKey: ["payroll-cycles"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const statusMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/payroll/cycles/${id}/status`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("وضعیت دوره حقوق به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["payroll-cycles"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="حقوق، دستمزد و تسویه کمیسیون"
        subtitle="ایجاد دوره پرداخت ماهانه، محاسبه خودکار حقوق پایه و سهم کمیسیون مشاوران و صدور فیش حقوقی"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "حقوق و دستمزد" }]}
        actions={
          canManage ? (
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Plus className="h-4 w-4" />
              محاسبه دوره حقوق جدید
            </button>
          ) : null
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={cyclesQ.data || []}
        rowKey={(c) => c.id}
        isLoading={cyclesQ.isLoading}
        error={cyclesQ.error instanceof Error ? cyclesQ.error.message : null}
        onRetry={() => cyclesQ.refetch()}
        searchPlaceholder="جستجو در عنوان دوره..."
        columns={[
          {
            key: "title",
            header: "عنوان دوره",
            render: (c) => (
              <div>
                <div className="font-semibold text-slate-900 dark:text-slate-100">{c.title}</div>
                <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  <DateDisplay value={c.period_start} /> تا <DateDisplay value={c.period_end} />
                </div>
              </div>
            ),
          },
          {
            key: "count",
            header: "تعداد فیش‌ها",
            render: (c) => <span className="tabular-nums font-semibold">{formatNumberFa(c.payslips.length)} فیش</span>,
          },
          {
            key: "total",
            header: "جمع خالص پرداختی",
            render: (c) => {
              const sum = c.payslips.reduce((acc, p) => acc + (Number(p.net_payable) || 0), 0);
              return <MoneyDisplay amount={sum} sourceCurrency="IRT" className="font-bold text-teal-800 dark:text-teal-300" />;
            },
          },
          { key: "status", header: "وضعیت", render: (c) => <StatusText status={c.status} /> },
          {
            key: "act",
            header: "عملیات",
            render: (c) => (
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setSelectedCycle(c)}
                  className="inline-flex items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  مشاهده فیش‌ها
                </button>
                {canManage && c.status === "CALCULATED" && (
                  <button
                    type="button"
                    onClick={() => statusMut.mutate({ id: c.id, status: "APPROVED" })}
                    className="inline-flex items-center gap-1 rounded bg-teal-700 px-2.5 py-1 text-xs font-semibold text-white"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    تأیید نهایی
                  </button>
                )}
                {canManage && c.status === "APPROVED" && (
                  <button
                    type="button"
                    onClick={() => statusMut.mutate({ id: c.id, status: "PAID" })}
                    className="inline-flex items-center gap-1 rounded bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white"
                  >
                    <Wallet className="h-3.5 w-3.5" />
                    ثبت پرداخت
                  </button>
                )}
              </div>
            ),
          },
        ]}
      />

      <ModalDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="ایجاد و محاسبه دوره حقوق جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">عنوان دوره</label>
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">تاریخ شروع بازه (میلادی)</label>
              <input
                required
                type="date"
                value={form.period_start}
                onChange={(e) => setForm({ ...form, period_start: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">تاریخ پایان بازه (میلادی)</label>
              <input
                required
                type="date"
                value={form.period_end}
                onChange={(e) => setForm({ ...form, period_end: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={createMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white disabled:opacity-50"
          >
            محاسبه خودکار فیش‌های پرسنل
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={!!selectedCycle}
        onClose={() => setSelectedCycle(null)}
        title={selectedCycle ? `فیش‌های حقوقی: ${selectedCycle.title}` : ""}
        widthClass="max-w-3xl"
      >
        {selectedCycle && (
          <div className="space-y-4">
            <div className="flex items-center justify-end print:hidden">
              <button
                type="button"
                onClick={() => window.print()}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <Printer className="h-3.5 w-3.5" />
                چاپ فیش‌های حقوقی
              </button>
            </div>
            {selectedCycle.payslips.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">هیچ فیش حقوقی در این دوره ایجاد نشده است.</p>
            ) : (
              selectedCycle.payslips.map((ps) => (
                <div key={ps.id} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-2.5">
                    <div>
                      <div className="font-bold text-slate-900 dark:text-slate-100">{ps.employee_name}</div>
                      <div className="font-mono text-xs text-slate-500 dark:text-slate-400">کد پرسنلی: {ps.employee_code}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <MoneyDisplay amount={ps.net_payable} sourceCurrency="IRT" className="text-base font-bold text-teal-800 dark:text-teal-300" />
                      <StatusText status={ps.status} />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="rounded bg-white dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-800">
                      <div className="text-slate-500 dark:text-slate-400">حقوق ثابت</div>
                      <MoneyDisplay amount={ps.base_salary_amount} sourceCurrency="IRT" className="font-semibold" />
                    </div>
                    <div className="rounded bg-white dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-800">
                      <div className="text-slate-500 dark:text-slate-400">کمیسیون تسویه‌نشده</div>
                      <MoneyDisplay amount={ps.commission_amount} sourceCurrency="IRT" className="font-semibold text-emerald-800" />
                    </div>
                    <div className="rounded bg-white dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-800">
                      <div className="text-slate-500 dark:text-slate-400">کسورات و مالیات</div>
                      <MoneyDisplay amount={ps.tax_amount} sourceCurrency="IRT" className="font-semibold text-rose-800" />
                    </div>
                  </div>
                  {ps.items.length > 0 && (
                    <div className="space-y-1 pt-1 text-xs">
                      {ps.items.map((it) => (
                        <div key={it.id} className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                          <span>{it.description} ({it.item_type})</span>
                          <MoneyDisplay amount={it.amount} sourceCurrency="IRT" className="font-medium text-slate-900 dark:text-slate-100" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </ModalDrawer>
    </div>
  );
}
