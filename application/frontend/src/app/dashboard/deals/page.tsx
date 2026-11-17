"use client";

import React, { useState } from "react";
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

      <DataTable
        rows={dealsQ.data || []}
        rowKey={(d) => d.id}
        isLoading={dealsQ.isLoading}
        error={dealsQ.error instanceof Error ? dealsQ.error.message : null}
        searchPlaceholder="جستجو در کد معامله، قرارداد یا ملک..."
        columns={[
          { key: "code", header: "کد معامله", render: (d) => <span className="font-mono text-xs font-semibold">{d.deal_code}</span> },
          { key: "prop", header: "ملک", render: (d) => d.property_title },
          { key: "cnt", header: "شماره قرارداد", render: (d) => <span className="font-mono text-xs">{d.contract_number}</span> },
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
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm"
          />
          <select
            required
            value={form.contract_id}
            onChange={(e) => setForm({ ...form, contract_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
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
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت معامله
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
