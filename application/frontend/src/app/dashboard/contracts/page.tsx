"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { ContractItem, PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

interface TemplateItem {
  id: string;
  contract_type: string;
  title: string;
  body_template: string;
  legal_disclaimer: string;
  is_manager_verified: boolean;
}

export default function ContractsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"contracts" | "templates">("contracts");
  const [modalOpen, setModalOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    contract_number: `CNT-${Math.floor(1000 + Math.random() * 9000)}`,
    contract_type: "SALE",
    property_id: "",
    deal_type_id: "SALE",
    amount: "38000000000",
    advance_payment: "5000000000",
    buyer_name: "",
    seller_name: "",
  });

  const contractsQ = useQuery({
    queryKey: ["contracts", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<ContractItem[]>("/api/v1/contracts", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const templatesQ = useQuery({
    queryKey: ["contract-templates", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<TemplateItem[]>("/api/v1/contracts/templates", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const propsQ = useQuery({
    queryKey: ["props-cnt", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<PropertyItem[]>("/api/v1/properties?page_size=50", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/contracts", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          contract_number: form.contract_number,
          contract_type: form.contract_type,
          property_id: form.property_id,
          deal_type_id: form.deal_type_id,
          amount: form.amount,
          advance_payment: form.advance_payment,
          parties: [
            ...(form.seller_name ? [{ full_name: form.seller_name, party_role: "SELLER" }] : []),
            ...(form.buyer_name ? [{ full_name: form.buyer_name, party_role: "BUYER" }] : []),
          ],
        }),
      }),
    onSuccess: () => {
      setModalOpen(false);
      setNotice("قرارداد جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const statusMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/contracts/${id}/status`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setNotice("وضعیت قرارداد به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="قراردادها و قالب‌های حقوقی"
        subtitle="ثبت مبایعه‌نامه و اجاره‌نامه، طرفین قرارداد و پیگیری چرخه امضا"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "قراردادها" }]}
        actions={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white"
          >
            <Plus className="h-4 w-4" />
            ثبت قرارداد جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        <button
          type="button"
          onClick={() => setTab("contracts")}
          className={`h-9 rounded-lg border px-4 text-xs font-semibold ${
            tab === "contracts" ? "border-teal-700 bg-teal-700 text-white" : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
          }`}
        >
          فهرست قراردادها
        </button>
        <button
          type="button"
          onClick={() => setTab("templates")}
          className={`h-9 rounded-lg border px-4 text-xs font-semibold ${
            tab === "templates" ? "border-teal-700 bg-teal-700 text-white" : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
          }`}
        >
          قالب‌های حقوقی آماده
        </button>
      </div>

      {tab === "contracts" ? (
        <DataTable
          rows={contractsQ.data || []}
          rowKey={(c) => c.id}
          isLoading={contractsQ.isLoading}
          error={contractsQ.error instanceof Error ? contractsQ.error.message : null}
          searchPlaceholder="جستجو در شماره قرارداد یا ملک..."
          exportFileName="contracts"
          columns={[
            {
              key: "num",
              header: "شماره قرارداد",
              render: (c) => (
                <Link href={`/dashboard/contracts/${c.id}`} className="font-mono text-xs font-semibold text-teal-700 dark:text-teal-400 hover:underline">
                  {c.contract_number}
                </Link>
              ),
            },
            { key: "prop", header: "ملک", render: (c) => c.property_title },
            { key: "parties", header: "طرفین", render: (c) => c.parties.map((p) => p.full_name).join(" / ") || "—" },
            { key: "amt", header: "مبلغ کل", render: (c) => <MoneyDisplay amount={c.amount} sourceCurrency={c.currency} className="font-semibold text-xs" /> },
            { key: "status", header: "وضعیت", render: (c) => <StatusText status={c.status} /> },
            {
              key: "act",
              header: "چرخه امضا",
              render: (c) => (
                <div className="flex gap-1.5">
                  {c.status === "DRAFT" && (
                    <button
                      type="button"
                      onClick={() => statusMut.mutate({ id: c.id, status: "APPROVED" })}
                      className="rounded bg-amber-600 px-2 py-1 text-xs font-semibold text-white"
                    >
                      تأیید متن
                    </button>
                  )}
                  {c.status !== "SIGNED" && (
                    <button
                      type="button"
                      onClick={() => statusMut.mutate({ id: c.id, status: "SIGNED" })}
                      className="rounded bg-teal-700 px-2 py-1 text-xs font-semibold text-white"
                    >
                      امضای نهایی
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {(templatesQ.data || []).map((t) => (
            <div key={t.id} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{t.title}</h3>
                <span className="text-xs font-mono text-slate-500 dark:text-slate-400">{t.contract_type}</span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-3">{t.body_template}</p>
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-900">
                {t.legal_disclaimer}
              </div>
            </div>
          ))}
        </div>
      )}

      <ModalDrawer open={modalOpen} onClose={() => setModalOpen(false)} title="ثبت قرارداد جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="شماره قرارداد"
            value={form.contract_number}
            onChange={(e) => setForm({ ...form, contract_number: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 font-mono text-sm"
          />
          <select
            required
            value={form.property_id}
            onChange={(e) => setForm({ ...form, property_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب ملک...</option>
            {(propsQ.data || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.property_code} — {p.title}
              </option>
            ))}
          </select>
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="نام فروشنده / موجر"
              value={form.seller_name}
              onChange={(e) => setForm({ ...form, seller_name: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
            <input
              placeholder="نام خریدار / مستأجر"
              value={form.buyer_name}
              onChange={(e) => setForm({ ...form, buyer_name: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
          </div>
          <input
            type="number"
            placeholder="مبلغ قرارداد (تومان)"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت قرارداد
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
