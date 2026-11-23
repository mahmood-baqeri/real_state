"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calculator, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CommissionItem, DealItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

interface PolicyItem {
  id: string;
  name: string;
  deal_type: string;
  deal_type_name: string;
  versions: {
    id: string;
    version_number: number;
    gross_rate_percent: string;
    agency_house_percent: string;
    primary_agent_percent: string;
  }[];
}

export default function CommissionsPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [policyModal, setPolicyModal] = useState(false);
  const [calcModal, setCalcModal] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [polForm, setPolForm] = useState({
    name: "",
    deal_type_id: "SALE",
    gross_rate_percent: "1.0000",
    agency_house_percent: "50.0000",
    primary_agent_percent: "50.0000",
  });
  const [calcForm, setCalcForm] = useState({ deal_id: "", discount_amount: "0" });

  const commQ = useQuery({
    queryKey: ["commissions", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<CommissionItem[]>("/api/v1/commissions", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const policiesQ = useQuery({
    queryKey: ["commission-policies", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<PolicyItem[]>("/api/v1/commissions/policies", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const dealsQ = useQuery({
    queryKey: ["deals-for-comm", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<DealItem[]>("/api/v1/deals", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const canManage = ["SUPER_ADMIN", "AGENCY_MANAGER", "AGENCY_ACCOUNTANT"].includes(effectiveRole);

  const createPolMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/commissions/policies", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(polForm),
      }),
    onSuccess: () => {
      setPolicyModal(false);
      setNotice("تعرفه کمیسیون جدید تعریف شد.");
      qc.invalidateQueries({ queryKey: ["commission-policies"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const calcMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/commissions/calculate", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(calcForm),
      }),
    onSuccess: () => {
      setCalcModal(false);
      setNotice("کمیسیون معامله با دقت Decimal محاسبه و سهم‌ها تفکیک شد.");
      qc.invalidateQueries({ queryKey: ["commissions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const statusMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/commissions/${id}/status`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setNotice("وضعیت کمیسیون به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["commissions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="کمیسیون‌ها و تقسیم سهم (Splits)"
        subtitle="محاسبه دقیق سهم آژانس، مشاور اصلی، مشاور همکار و مدیریت تعرفه‌های کمیسیون"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "کمیسیون‌ها" }]}
        actions={
          canManage ? (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setCalcModal(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white"
              >
                <Calculator className="h-4 w-4" />
                محاسبه کمیسیون معامله
              </button>
              <button
                type="button"
                onClick={() => setPolicyModal(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200"
              >
                <Plus className="h-4 w-4" />
                تعرفه جدید
              </button>
            </div>
          ) : null
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={commQ.data || []}
        rowKey={(c) => c.id}
        isLoading={commQ.isLoading}
        error={commQ.error instanceof Error ? commQ.error.message : null}
        searchPlaceholder="جستجو در کد معامله یا ملک..."
        columns={[
          { key: "deal", header: "معامله", render: (c) => <div><div className="font-mono text-xs font-semibold">{c.deal_code}</div><div className="text-xs text-slate-500 dark:text-slate-400">{c.property_title}</div></div> },
          { key: "gross", header: "کمیسیون ناخالص", render: (c) => <MoneyDisplay amount={c.gross_commission} sourceCurrency={c.currency} /> },
          { key: "net", header: "خالص قابل تقسیم", render: (c) => <MoneyDisplay amount={c.net_distributable} sourceCurrency={c.currency} className="font-bold text-teal-800 dark:text-teal-300" /> },
          {
            key: "shares",
            header: "سهم ذی‌نفعان",
            render: (c) => (
              <div className="space-y-1 text-xs">
                {c.shares.map((s) => (
                  <div key={s.id} className="flex items-center justify-between gap-3">
                    <span className="text-slate-600 dark:text-slate-400">{s.beneficiary_name}:</span>
                    <MoneyDisplay amount={s.calculated_amount} sourceCurrency={c.currency} className="font-semibold" />
                  </div>
                ))}
              </div>
            ),
          },
          { key: "status", header: "وضعیت", render: (c) => <StatusText status={c.status} /> },
          {
            key: "act",
            header: "تأیید مالی",
            render: (c) =>
              canManage ? (
                <div className="flex gap-1.5">
                  {c.status === "CALCULATED" && (
                    <button
                      type="button"
                      onClick={() => statusMut.mutate({ id: c.id, status: "APPROVED" })}
                      className="rounded bg-teal-700 px-2.5 py-1 text-xs font-semibold text-white"
                    >
                      تأیید نهایی
                    </button>
                  )}
                  {c.status === "APPROVED" && (
                    <button
                      type="button"
                      onClick={() => statusMut.mutate({ id: c.id, status: "SETTLED" })}
                      className="rounded bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white"
                    >
                      تسویه شد
                    </button>
                  )}
                </div>
              ) : (
                "—"
              ),
          },
        ]}
      />

      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
        <h3 className="mb-3 text-sm font-bold text-slate-900 dark:text-slate-100">تعرفه‌های فعال کمیسیون آژانس</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(policiesQ.data || []).map((pol) => (
            <div key={pol.id} className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 p-3.5 text-xs space-y-1">
              <div className="font-bold text-slate-900 dark:text-slate-100">{pol.name}</div>
              <div className="text-slate-500 dark:text-slate-400">نوع معامله: {pol.deal_type_name}</div>
              {pol.versions[0] && (
                <div className="pt-1 text-slate-700 dark:text-slate-300 tabular-nums">
                  نرخ کل: {pol.versions[0].gross_rate_percent}% | سهم مشاور: {pol.versions[0].primary_agent_percent}%
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <ModalDrawer open={policyModal} onClose={() => setPolicyModal(false)} title="تعریف تعرفه کمیسیون جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createPolMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام تعرفه (مثال: تعرفه فروش ۱٪)"
            value={polForm.name}
            onChange={(e) => setPolForm({ ...polForm, name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
          />
          <select
            value={polForm.deal_type_id}
            onChange={(e) => setPolForm({ ...polForm, deal_type_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="SALE">فروش</option>
            <option value="MORTGAGE_RENT">رهن و اجاره</option>
          </select>
          <div className="grid grid-cols-3 gap-2">
            <input
              type="number"
              step="0.1"
              value={polForm.gross_rate_percent}
              onChange={(e) => setPolForm({ ...polForm, gross_rate_percent: e.target.value })}
              placeholder="نرخ کل %"
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-2 text-xs tabular-nums"
            />
            <input
              type="number"
              value={polForm.agency_house_percent}
              onChange={(e) => setPolForm({ ...polForm, agency_house_percent: e.target.value })}
              placeholder="سهم آژانس %"
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-2 text-xs tabular-nums"
            />
            <input
              type="number"
              value={polForm.primary_agent_percent}
              onChange={(e) => setPolForm({ ...polForm, primary_agent_percent: e.target.value })}
              placeholder="سهم مشاور %"
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-2 text-xs tabular-nums"
            />
          </div>
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت تعرفه
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={calcModal} onClose={() => setCalcModal(false)} title="محاسبه کمیسیون معامله">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            calcMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={calcForm.deal_id}
            onChange={(e) => setCalcForm({ ...calcForm, deal_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب معامله...</option>
            {(dealsQ.data || []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.deal_code} — {d.property_title}
              </option>
            ))}
          </select>
          <input
            type="number"
            placeholder="تخفیف کمیسیون (اختیاری)"
            value={calcForm.discount_amount}
            onChange={(e) => setCalcForm({ ...calcForm, discount_amount: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            محاسبه و ثبت تقسیم سهم
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
