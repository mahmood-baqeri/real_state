// Path: frontend/src/app/dashboard/negotiations/page.tsx

"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { History, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CustomerItem, NegotiationItem, PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function NegotiationsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [offersTarget, setOffersTarget] = useState<NegotiationItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    property_id: "",
    customer_id: "",
    deal_type_id: "SALE",
    initial_price: "36500000000",
    notes: "",
  });

  const [offerForm, setOfferForm] = useState({
    offered_by: "SELLER",
    proposed_price: "37500000000",
    discount_amount: "0",
  });

  const negsQ = useQuery({
    queryKey: ["negotiations", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<NegotiationItem[]>("/api/v1/negotiations", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const propsQ = useQuery({
    queryKey: ["props-neg", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<PropertyItem[]>("/api/v1/properties?page_size=50", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const custQ = useQuery({
    queryKey: ["custs-neg", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<CustomerItem[]>("/api/v1/customers", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/negotiations", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      setCreateOpen(false);
      setNotice("پرونده مذاکره و پیشنهاد اولیه ثبت شد.");
      qc.invalidateQueries({ queryKey: ["negotiations"] });
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
      setNotice("نتیجه مذاکره ثبت شد.");
      qc.invalidateQueries({ queryKey: ["negotiations"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="مذاکرات و پیشنهادهای قیمتی (Counter-Offers)"
        subtitle="ثبت نسخه‌های متوالی پیشنهاد خریدار و مالک تا توافق نهایی"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "مذاکرات" }]}
        actions={
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            شروع مذاکره جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={negsQ.data || []}
        rowKey={(n) => n.id}
        isLoading={negsQ.isLoading}
        error={negsQ.error instanceof Error ? negsQ.error.message : null}
        searchPlaceholder="جستجو در ملک یا نام مشتری..."
        columns={[
          { key: "prop", header: "ملک", render: (n) => <div><div className="font-semibold">{n.property_title}</div><div className="font-mono text-xs text-slate-400">{n.property_code}</div></div> },
          { key: "cust", header: "مشتری", render: (n) => n.customer_name },
          {
            key: "latest",
            header: "آخرین پیشنهاد",
            render: (n) => {
              const last = n.offers[n.offers.length - 1];
              return last ? (
                <div>
                  <MoneyDisplay amount={last.proposed_price} sourceCurrency={last.currency} className="font-bold text-xs" />
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">نسخه {last.version_number} ({last.offered_by})</div>
                </div>
              ) : (
                "—"
              );
            },
          },
          { key: "status", header: "وضعیت", render: (n) => <StatusText status={n.status} /> },
          {
            key: "act",
            header: "عملیات",
            render: (n) => (
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setOffersTarget(n)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300"
                >
                  <History className="h-3.5 w-3.5" />
                  پیشنهادها ({n.offers.length})
                </button>
                {["OPEN", "COUNTER_OFFERED"].includes(n.status) && (
                  <>
                    <button
                      type="button"
                      onClick={() => respondMut.mutate({ id: n.id, status: "ACCEPTED" })}
                      className="h-7 rounded bg-emerald-700 px-2 text-xs font-semibold text-white"
                    >
                      توافق نهایی
                    </button>
                    <button
                      type="button"
                      onClick={() => respondMut.mutate({ id: n.id, status: "REJECTED" })}
                      className="h-7 rounded border border-rose-200 bg-rose-50 px-2 text-xs font-semibold text-rose-700"
                    >
                      رد
                    </button>
                  </>
                )}
              </div>
            ),
          },
        ]}
      />

      <ModalDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="ایجاد پرونده مذاکره جدید">
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
          <select
            required
            value={form.customer_id}
            onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب مشتری...</option>
            {(custQ.data || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </select>
          <input
            type="number"
            placeholder="قیمت پیشنهادی اولیه"
            value={form.initial_price}
            onChange={(e) => setForm({ ...form, initial_price: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت مذاکره
          </button>
        </form>
      </ModalDrawer>

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
                  <MoneyDisplay amount={o.proposed_price} sourceCurrency={o.currency} className="font-bold text-slate-900 dark:text-slate-100" />
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
            <div className="text-xs font-bold text-slate-900 dark:text-slate-100">ثبت پیشنهاد متقابل جدید</div>
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
        </div>
      </ModalDrawer>
    </div>
  );
}
