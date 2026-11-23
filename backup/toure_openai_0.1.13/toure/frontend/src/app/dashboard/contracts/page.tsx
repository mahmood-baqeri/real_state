"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Edit3, Lock, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { ContractItem, PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";
import { useToast } from "@/components/ui/ToastProvider";

interface TemplateItem {
  id: string;
  contract_type: string;
  title: string;
  body_template: string;
  legal_disclaimer: string;
  is_manager_verified: boolean;
}

const STATUS_TABS = [
  { key: "ALL", label: "همه" },
  { key: "DRAFT", label: "پیش‌نویس" },
  { key: "PENDING_REVIEW", label: "در انتظار بررسی" },
  { key: "PENDING_PARTIES_APPROVAL", label: "تأیید طرفین" },
  { key: "SIGNED", label: "امضاشده" },
  { key: "ACTIVE", label: "فعال" },
  { key: "COMPLETED", label: "تکمیل‌شده" },
  { key: "ARCHIVED", label: "بایگانی" },
];

export default function ContractsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [tab, setTab] = useState<"contracts" | "templates">("contracts");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<ContractItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    contract_number: `CNT-${Math.floor(1000 + Math.random() * 9000)}`,
    contract_type: "SALE",
    property_id: "",
    deal_type_id: "SALE",
    amount: "38000000000",
    advance_payment: "5000000000",
    payment_method: "",
    terms_snapshot: "",
    buyer_name: "",
    seller_name: "",
  });

  const [editForm, setEditForm] = useState({
    contract_type: "SALE",
    amount: "0",
    advance_payment: "0",
    remaining_amount: "0",
    payment_method: "",
  });

  const contractsQ = useQuery({
    queryKey: ["contracts", activeAgencyId, statusFilter],
    enabled: !!accessToken,
    queryFn: async () => {
      const qs = statusFilter !== "ALL" ? `?status=${encodeURIComponent(statusFilter)}&page_size=100` : "?page_size=100";
      return (
        await apiFetch<ContractItem[]>(`/api/v1/contracts${qs}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const templatesQ = useQuery({
    queryKey: ["contract-templates", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<TemplateItem[]>("/api/v1/contracts/templates", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const propsQ = useQuery({
    queryKey: ["props-cnt", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<PropertyItem[]>("/api/v1/properties?page_size=50", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
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
          remaining_amount: Math.max(0, Number(form.amount || 0) - Number(form.advance_payment || 0)).toString(),
          payment_method: form.payment_method,
          terms_snapshot: form.terms_snapshot,
          parties: [
            ...(form.seller_name ? [{ full_name: form.seller_name, party_role: "SELLER" }] : []),
            ...(form.buyer_name ? [{ full_name: form.buyer_name, party_role: "BUYER" }] : []),
          ],
        }),
      }),
    onSuccess: () => {
      setModalOpen(false);
      setErrMsg(null);
      setNotice("قرارداد جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const editMut = useMutation({
    mutationFn: async () => {
      if (!editTarget) return;
      return apiFetch(`/api/v1/contracts/${editTarget.id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId || editTarget.agency_id,
        body: JSON.stringify(editForm),
      });
    },
    onSuccess: () => {
      setEditTarget(null);
      setErrMsg(null);
      setNotice("پیش‌نویس قرارداد با موفقیت ویرایش شد.");
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const statusMut = useMutation({
    mutationFn: async ({
      id,
      agencyId,
      status,
      reason,
    }: {
      id: string;
      agencyId?: string;
      status: string;
      reason?: string;
    }) =>
      apiFetch(`/api/v1/contracts/${id}/status`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId || agencyId,
        body: JSON.stringify({ status, reason: reason || "" }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("وضعیت قرارداد به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const archiveMut = useMutation({
    mutationFn: async ({ id, agencyId }: { id: string; agencyId?: string }) =>
      apiFetch(`/api/v1/contracts/${id}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId || agencyId,
      }),
    onSuccess: () => {
      toast.success("قرارداد پیش‌نویس با موفقیت بایگانی شد.");
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const openEdit = (c: ContractItem) => {
    setEditTarget(c);
    setEditForm({
      contract_type: c.contract_type,
      amount: c.amount,
      advance_payment: c.advance_payment,
      remaining_amount: c.remaining_amount,
      payment_method: c.payment_method || "",
    });
  };

  const rows = useMemo(() => contractsQ.data || [], [contractsQ.data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="قراردادها و قالب‌های حقوقی"
        subtitle="ثبت مبایعه‌نامه و اجاره‌نامه، طرفین قرارداد، الحاقیه‌های رسمی و پیگیری چرخه امضا"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "قراردادها" }]}
        actions={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
          >
            <Plus className="h-4 w-4" />
            ثبت قرارداد جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-3">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setTab("contracts")}
            className={`h-9 rounded-lg border px-4 text-xs font-semibold whitespace-nowrap ${
              tab === "contracts"
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
            }`}
          >
            فهرست قراردادها
          </button>
          <button
            type="button"
            onClick={() => setTab("templates")}
            className={`h-9 rounded-lg border px-4 text-xs font-semibold whitespace-nowrap ${
              tab === "templates"
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
            }`}
          >
            قالب‌های حقوقی آماده
          </button>
        </div>

        {tab === "contracts" && (
          <div className="flex flex-wrap gap-1.5">
            {STATUS_TABS.map((st) => (
              <button
                key={st.key}
                type="button"
                onClick={() => setStatusFilter(st.key)}
                className={`h-8 rounded-lg border px-2.5 text-xs font-semibold whitespace-nowrap ${
                  statusFilter === st.key
                    ? "border-teal-700 bg-teal-700 text-white"
                    : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {tab === "contracts" ? (
        <DataTable
          rows={rows}
          rowKey={(c) => c.id}
          isLoading={contractsQ.isLoading}
          error={contractsQ.error instanceof Error ? contractsQ.error.message : null}
          onRetry={() => contractsQ.refetch()}
          searchPlaceholder="جستجو در شماره قرارداد یا ملک..."
          exportFileName="contracts"
          columns={[
            {
              key: "num",
              header: "شماره قرارداد",
              render: (c) => (
                <div>
                  <Link
                    href={`/dashboard/contracts/${c.id}`}
                    className="font-mono text-xs font-semibold text-teal-700 dark:text-teal-400 hover:underline"
                  >
                    {c.contract_number}
                  </Link>
                  {!activeAgencyId && c.agency_name && (
                    <div className="text-[11px] text-slate-400">{c.agency_name}</div>
                  )}
                </div>
              ),
            },
            { key: "prop", header: "ملک", render: (c) => c.property_title },
            {
              key: "parties",
              header: "طرفین",
              render: (c) => c.parties.map((p) => p.full_name).join(" / ") || "—",
            },
            {
              key: "amt",
              header: "مبلغ کل",
              render: (c) => (
                <MoneyDisplay amount={c.amount} sourceCurrency={c.currency} className="font-semibold text-xs" />
              ),
            },
            { key: "status", header: "وضعیت", render: (c) => <StatusText status={c.status} /> },
            {
              key: "act",
              header: "عملیات و چرخه امضا",
              render: (c) => {
                const isEditable =
                  c.is_editable ?? ["DRAFT", "PENDING_REVIEW", "PENDING_PARTIES_APPROVAL"].includes(c.status);
                const isLocked = ["SIGNED", "ACTIVE", "COMPLETED"].includes(c.status);

                return (
                  <div className="flex flex-wrap items-center gap-1.5">
                    {c.status === "DRAFT" && (
                      <button
                        type="button"
                        onClick={() =>
                          statusMut.mutate({ id: c.id, agencyId: c.agency_id, status: "PENDING_REVIEW" })
                        }
                        className="rounded bg-amber-600 px-2 py-1 text-xs font-semibold text-white whitespace-nowrap"
                      >
                        ارسال به بازبینی
                      </button>
                    )}
                    {c.status === "PENDING_REVIEW" && (
                      <button
                        type="button"
                        onClick={() =>
                          statusMut.mutate({
                            id: c.id,
                            agencyId: c.agency_id,
                            status: "PENDING_PARTIES_APPROVAL",
                          })
                        }
                        className="rounded bg-indigo-600 px-2 py-1 text-xs font-semibold text-white whitespace-nowrap"
                      >
                        تأیید طرفین
                      </button>
                    )}
                    {isEditable && (
                      <>
                        <button
                          type="button"
                          onClick={() => statusMut.mutate({ id: c.id, agencyId: c.agency_id, status: "SIGNED" })}
                          className="rounded bg-teal-700 px-2 py-1 text-xs font-semibold text-white whitespace-nowrap"
                        >
                          امضای نهایی
                        </button>
                        <button
                          type="button"
                          onClick={() => openEdit(c)}
                          title="ویرایش پیش‌نویس"
                          className="inline-flex h-7 w-7 items-center justify-center rounded border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => archiveMut.mutate({ id: c.id, agencyId: c.agency_id })}
                          title="بایگانی پیش‌نویس"
                          className="inline-flex h-7 w-7 items-center justify-center rounded border border-rose-200 dark:border-rose-900 text-rose-600"
                        >
                          <Archive className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                    {c.status === "SIGNED" && (
                      <button
                        type="button"
                        onClick={() => statusMut.mutate({ id: c.id, agencyId: c.agency_id, status: "ACTIVE" })}
                        className="rounded bg-emerald-700 px-2 py-1 text-xs font-semibold text-white whitespace-nowrap"
                      >
                        فعال‌سازی قرارداد
                      </button>
                    )}
                    {isLocked && (
                      <Link
                        href={`/dashboard/contracts/${c.id}`}
                        className="inline-flex items-center gap-1 rounded border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-semibold text-slate-700 dark:text-slate-300 whitespace-nowrap"
                      >
                        <Lock className="h-3 w-3 text-amber-600" />
                        پرونده / الحاقیه
                      </Link>
                    )}
                  </div>
                );
              },
            },
          ]}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {(templatesQ.data || []).map((t) => (
            <div
              key={t.id}
              className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{t.title}</h3>
                <span className="text-xs font-mono text-slate-500 dark:text-slate-400">{t.contract_type}</span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-3">{t.body_template}</p>
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                {t.legal_disclaimer}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Contract Modal */}
      <ModalDrawer open={modalOpen} onClose={() => setModalOpen(false)} title="ثبت قرارداد جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          {!activeAgencyId && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
              در حالت مشاهده سراسری هستید. برای ثبت قرارداد جدید، ابتدا آژانس فعال را از منوی بالای صفحه انتخاب کنید.
            </div>
          )}
          <input
            required
            placeholder="شماره قرارداد"
            value={form.contract_number}
            onChange={(e) => setForm({ ...form, contract_number: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm"
          />
          <select
            required
            disabled={!activeAgencyId}
            value={form.property_id}
            onChange={(e) => {
              const pid = e.target.value;
              const matched = (propsQ.data || []).find((p) => p.id === pid);
              setForm({
                ...form,
                property_id: pid,
                deal_type_id: matched?.deal_type?.code || form.deal_type_id,
                contract_type: matched?.deal_type?.is_rental ? "MORTGAGE_RENT" : "SALE",
                amount: matched ? matched.total_price : form.amount,
              });
            }}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm disabled:opacity-50"
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
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
            <input
              placeholder="نام خریدار / مستأجر"
              value={form.buyer_name}
              onChange={(e) => setForm({ ...form, buyer_name: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="number"
              placeholder="مبلغ کل قرارداد (تومان)"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm tabular-nums"
            />
            <input
              type="number"
              placeholder="پیش‌پرداخت (تومان)"
              value={form.advance_payment}
              onChange={(e) => setForm({ ...form, advance_payment: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm tabular-nums"
            />
          </div>
          <input
            placeholder="روش پرداخت (مثلاً چک صیادی + نقد)"
            value={form.payment_method}
            onChange={(e) => setForm({ ...form, payment_method: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <textarea
            rows={2}
            placeholder="شروط اختصاصی قرارداد..."
            value={form.terms_snapshot}
            onChange={(e) => setForm({ ...form, terms_snapshot: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-xs"
          />
          <button
            type="submit"
            disabled={createMut.isPending || !activeAgencyId}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {createMut.isPending ? "در حال ثبت..." : "ثبت قرارداد"}
          </button>
        </form>
      </ModalDrawer>

      {/* Edit Draft Contract Modal */}
      <ModalDrawer
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        title={`ویرایش پیش‌نویس قرارداد — ${editTarget?.contract_number || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            editMut.mutate();
          }}
          className="space-y-3"
        >
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
              مبلغ کل قرارداد
            </label>
            <input
              type="number"
              value={editForm.amount}
              onChange={(e) => setEditForm({ ...editForm, amount: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm tabular-nums"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">پیش‌پرداخت</label>
              <input
                type="number"
                value={editForm.advance_payment}
                onChange={(e) => setEditForm({ ...editForm, advance_payment: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm tabular-nums"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">باقیمانده</label>
              <input
                type="number"
                value={editForm.remaining_amount}
                onChange={(e) => setEditForm({ ...editForm, remaining_amount: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm tabular-nums"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">روش پرداخت</label>
            <input
              value={editForm.payment_method}
              onChange={(e) => setEditForm({ ...editForm, payment_method: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={editMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {editMut.isPending ? "در حال ذخیره..." : "ذخیره تغییرات قرارداد"}
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
