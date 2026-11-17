"use client";

import React, { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Landmark, Plus, RotateCcw, Scale, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CoaAccount, CurrencyCode, JournalEntryItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";
import { KpiCard } from "@/components/ui/KpiCard";

interface TreasuryResponse {
  bank_accounts: {
    id: string;
    bank_name: string;
    account_number: string;
    iban: string;
    currency: CurrencyCode;
    current_balance: string;
  }[];
  cash_boxes: {
    id: string;
    name: string;
    currency: CurrencyCode;
    current_balance: string;
  }[];
  cheques: {
    id: string;
    direction: string;
    cheque_number: string;
    bank_name: string;
    due_date: string;
    amount: string;
    currency: CurrencyCode;
    status: string;
    deal_code: string | null;
  }[];
  deal_ledgers: {
    id: string;
    deal_id: string;
    deal_code: string;
    currency: CurrencyCode;
    deal_amount: string;
    total_received: string;
    total_paid: string;
    gross_commission: string;
    agency_share: string;
    agents_share: string;
    net_profit: string;
    settlement_status: string;
  }[];
}

interface JournalDraftLine {
  account_id: string;
  description: string;
  debit: string;
  credit: string;
}

const ACCOUNT_TYPES: Record<string, string> = {
  ASSET: "دارایی",
  LIABILITY: "بدهی",
  EQUITY: "سرمایه",
  REVENUE: "درآمد",
  EXPENSE: "هزینه",
};

const CHEQUE_DIR: Record<string, string> = {
  RECEIVABLE: "دریافتنی",
  PAYABLE: "پرداختنی",
};

export default function AccountingPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"journal" | "coa" | "treasury" | "ledgers">("journal");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [jeModal, setJeModal] = useState(false);
  const [coaModal, setCoaModal] = useState(false);
  const [chequeModal, setChequeModal] = useState(false);

  const [entryNumber, setEntryNumber] = useState("");
  const [entryDesc, setEntryDesc] = useState("");
  const [entryLines, setEntryLines] = useState<JournalDraftLine[]>([
    { account_id: "", description: "", debit: "0", credit: "0" },
    { account_id: "", description: "", debit: "0", credit: "0" },
  ]);

  const [coaForm, setCoaForm] = useState({
    code: "",
    name: "",
    account_type: "EXPENSE",
    level: "SUBSIDIARY",
  });

  const [chequeForm, setChequeForm] = useState({
    direction: "RECEIVABLE",
    cheque_number: "",
    bank_name: "",
    due_date: new Date().toISOString().slice(0, 10),
    amount: "",
    currency_id: "IRT",
  });

  const canManage = ["SUPER_ADMIN", "AGENCY_MANAGER", "AGENCY_ACCOUNTANT"].includes(effectiveRole);

  const coaQ = useQuery({
    queryKey: ["accounting-coa", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<CoaAccount[]>("/api/v1/accounting/coa", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const journalsQ = useQuery({
    queryKey: ["accounting-journals", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<JournalEntryItem[]>("/api/v1/accounting/journal-entries?page_size=50", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const treasuryQ = useQuery({
    queryKey: ["accounting-treasury", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<TreasuryResponse>("/api/v1/accounting/treasury", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const totals = useMemo(() => {
    const totalDebit = entryLines.reduce((acc, l) => acc + (Number(l.debit) || 0), 0);
    const totalCredit = entryLines.reduce((acc, l) => acc + (Number(l.credit) || 0), 0);
    const isBalanced = totalDebit > 0 && Math.abs(totalDebit - totalCredit) < 0.0001;
    return { totalDebit, totalCredit, isBalanced };
  }, [entryLines]);

  const postJeMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/accounting/journal-entries", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          entry_number: entryNumber,
          description: entryDesc,
          currency_id: "IRT",
          source_type: "MANUAL",
          lines: entryLines.map((l) => ({
            account_id: l.account_id,
            description: l.description,
            debit: l.debit || "0",
            credit: l.credit || "0",
          })),
        }),
      }),
    onSuccess: () => {
      setJeModal(false);
      setEntryNumber("");
      setEntryDesc("");
      setEntryLines([
        { account_id: "", description: "", debit: "0", credit: "0" },
        { account_id: "", description: "", debit: "0", credit: "0" },
      ]);
      setErrMsg(null);
      setNotice("سند حسابداری دوبل با موفقیت تراز و قطعی شد.");
      qc.invalidateQueries({ queryKey: ["accounting-journals"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const reverseJeMut = useMutation({
    mutationFn: async (entryId: string) =>
      apiFetch(`/api/v1/accounting/journal-entries/${entryId}/reverse`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("سند برگشتی (Reversal) در دفتر روزنامه ثبت شد.");
      qc.invalidateQueries({ queryKey: ["accounting-journals"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createCoaMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/accounting/coa", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(coaForm),
      }),
    onSuccess: () => {
      setCoaModal(false);
      setCoaForm({ code: "", name: "", account_type: "EXPENSE", level: "SUBSIDIARY" });
      setErrMsg(null);
      setNotice("سرفصل حساب جدید به کدینگ اضافه شد.");
      qc.invalidateQueries({ queryKey: ["accounting-coa"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createChequeMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/accounting/cheques", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(chequeForm),
      }),
    onSuccess: () => {
      setChequeModal(false);
      setChequeForm({
        direction: "RECEIVABLE",
        cheque_number: "",
        bank_name: "",
        due_date: new Date().toISOString().slice(0, 10),
        amount: "",
        currency_id: "IRT",
      });
      setErrMsg(null);
      setNotice("چک در دفتر خزانه‌داری ثبت شد.");
      qc.invalidateQueries({ queryKey: ["accounting-treasury"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const patchChequeMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/accounting/cheques/${id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("وضعیت چک به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["accounting-treasury"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const totalBankBalance = useMemo(
    () =>
      (treasuryQ.data?.bank_accounts || []).reduce((acc, b) => acc + (Number(b.current_balance) || 0), 0),
    [treasuryQ.data]
  );

  const totalCashBalance = useMemo(
    () =>
      (treasuryQ.data?.cash_boxes || []).reduce((acc, c) => acc + (Number(c.current_balance) || 0), 0),
    [treasuryQ.data]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="حسابداری دوبل و خزانه‌داری"
        subtitle="ثبت اسناد روزنامه متوازن (بدهکار/بستانکار)، کدینگ حساب‌ها، مدیریت بانک، صندوق و چک‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "حسابداری و خزانه" }]}
        actions={
          canManage ? (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => {
                  setEntryNumber(`JE-${Date.now().toString().slice(-6)}`);
                  setJeModal(true);
                }}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <Plus className="h-4 w-4" />
                ثبت سند حسابداری
              </button>
              <button
                type="button"
                onClick={() => setCoaModal(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
              >
                <BookOpen className="h-4 w-4" />
                سرفصل جدید
              </button>
              <button
                type="button"
                onClick={() => setChequeModal(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
              >
                <Landmark className="h-4 w-4" />
                ثبت چک جدید
              </button>
            </div>
          ) : null
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="اسناد روزنامه ثبت‌شده"
          value={(journalsQ.data || []).length}
          icon={<Scale className="h-5 w-5" />}
          tone="teal"
        />
        <KpiCard
          label="سرفصل‌های فعال"
          value={(coaQ.data || []).length}
          icon={<BookOpen className="h-5 w-5" />}
        />
        <KpiCard
          label="موجودی حساب‌های بانکی"
          value={<MoneyDisplay amount={totalBankBalance} sourceCurrency="IRT" />}
          tone="emerald"
        />
        <KpiCard
          label="موجودی صندوق‌های نقد"
          value={<MoneyDisplay amount={totalCashBalance} sourceCurrency="IRT" />}
          tone="amber"
        />
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        {[
          { key: "journal", label: "اسناد حسابداری (دفتر روزنامه)" },
          { key: "coa", label: "کدینگ و سرفصل حساب‌ها" },
          { key: "treasury", label: "بانک، صندوق و چک‌ها" },
          { key: "ledgers", label: "دفتر مالی معاملات" },
        ].map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key as typeof tab)}
            className={`h-9 rounded-lg border px-4 text-xs font-semibold transition-colors ${
              tab === item.key
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "journal" && (
        <DataTable
          rows={journalsQ.data || []}
          rowKey={(j) => j.id}
          isLoading={journalsQ.isLoading}
          error={journalsQ.error instanceof Error ? journalsQ.error.message : null}
          onRetry={() => journalsQ.refetch()}
          searchPlaceholder="جستجو در شماره سند یا شرح..."
          columns={[
            {
              key: "num",
              header: "شماره سند",
              render: (j) => (
                <div>
                  <div className="font-mono text-xs font-bold text-slate-900">{j.entry_number}</div>
                  <DateDisplay value={j.entry_date} className="text-[11px] text-slate-500" />
                </div>
              ),
            },
            {
              key: "desc",
              header: "شرح و منشأ",
              render: (j) => (
                <div>
                  <div className="font-medium text-slate-800">{j.description}</div>
                  <div className="text-[11px] text-slate-500">منشأ: {j.source_type}</div>
                </div>
              ),
            },
            {
              key: "lines",
              header: "ردیف‌های سند",
              render: (j) => (
                <div className="space-y-1 text-xs">
                  {j.lines.map((l) => (
                    <div key={l.id} className="flex items-center justify-between gap-4 border-b border-slate-100 pb-0.5 last:border-none">
                      <span className="text-slate-700">
                        <span className="font-mono text-[11px] text-slate-500">{l.account_code}</span>{" "}
                        {l.account_name}
                      </span>
                      <span className="tabular-nums">
                        {Number(l.debit) > 0 ? (
                          <span className="text-emerald-800">بد: <MoneyDisplay amount={l.debit} sourceCurrency={j.currency} /></span>
                        ) : (
                          <span className="text-rose-800">بس: <MoneyDisplay amount={l.credit} sourceCurrency={j.currency} /></span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              ),
            },
            { key: "status", header: "وضعیت", render: (j) => <StatusText status={j.status} /> },
            {
              key: "actions",
              header: "عملیات",
              render: (j) =>
                canManage && j.status === "POSTED" ? (
                  <button
                    type="button"
                    disabled={reverseJeMut.isPending}
                    onClick={() => reverseJeMut.mutate(j.id)}
                    className="inline-flex items-center gap-1 rounded border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-800 hover:bg-rose-100"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    سند برگشتی
                  </button>
                ) : (
                  <span className="text-xs text-slate-400">—</span>
                ),
            },
          ]}
        />
      )}

      {tab === "coa" && (
        <DataTable
          rows={coaQ.data || []}
          rowKey={(a) => a.id}
          isLoading={coaQ.isLoading}
          error={coaQ.error instanceof Error ? coaQ.error.message : null}
          searchPlaceholder="جستجو در کد یا نام سرفصل..."
          columns={[
            {
              key: "code",
              header: "کد حساب",
              sortValue: (a) => a.code,
              render: (a) => <span className="font-mono text-xs font-bold text-slate-900">{a.code}</span>,
            },
            { key: "name", header: "عنوان سرفصل", render: (a) => <span className="font-medium text-slate-900">{a.name}</span> },
            {
              key: "type",
              header: "ماهیت حساب",
              render: (a) => <span className="text-xs text-slate-700">{ACCOUNT_TYPES[a.account_type] || a.account_type}</span>,
            },
            { key: "level", header: "سطح", render: (a) => <span className="text-xs text-slate-500">{a.level}</span> },
          ]}
        />
      )}

      {tab === "treasury" && (
        <div className="space-y-6">
          {treasuryQ.isLoading ? (
            <LoadingState />
          ) : treasuryQ.error instanceof Error ? (
            <ErrorState message={treasuryQ.error.message} onRetry={() => treasuryQ.refetch()} />
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-white p-5">
                  <h3 className="mb-3 text-sm font-bold text-slate-900">حساب‌های بانکی آژانس</h3>
                  {(treasuryQ.data?.bank_accounts || []).length === 0 ? (
                    <p className="text-xs text-slate-500">حساب بانکی ثبت نشده است.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {treasuryQ.data?.bank_accounts.map((b) => (
                        <div key={b.id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                          <div>
                            <div className="font-bold text-slate-900">{b.bank_name}</div>
                            <div className="mt-0.5 font-mono text-[11px] text-slate-500">
                              شماره حساب: {b.account_number} {b.iban ? `| شبا: ${b.iban}` : ""}
                            </div>
                          </div>
                          <MoneyDisplay amount={b.current_balance} sourceCurrency={b.currency} className="font-bold text-teal-800" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-5">
                  <h3 className="mb-3 text-sm font-bold text-slate-900">صندوق‌های نقد</h3>
                  {(treasuryQ.data?.cash_boxes || []).length === 0 ? (
                    <p className="text-xs text-slate-500">صندوق نقد ثبت نشده است.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {treasuryQ.data?.cash_boxes.map((c) => (
                        <div key={c.id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                          <div className="font-bold text-slate-900">{c.name}</div>
                          <MoneyDisplay amount={c.current_balance} sourceCurrency={c.currency} className="font-bold text-slate-900" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <DataTable
                rows={treasuryQ.data?.cheques || []}
                rowKey={(c) => c.id}
                searchPlaceholder="جستجو در شماره چک یا بانک..."
                columns={[
                  { key: "num", header: "شماره چک", render: (c) => <span className="font-mono text-xs font-bold">{c.cheque_number}</span> },
                  { key: "dir", header: "نوع", render: (c) => <span className="text-xs">{CHEQUE_DIR[c.direction] || c.direction}</span> },
                  { key: "bank", header: "بانک", render: (c) => c.bank_name },
                  { key: "due", header: "سررسید", render: (c) => <DateDisplay value={c.due_date} /> },
                  { key: "amt", header: "مبلغ", render: (c) => <MoneyDisplay amount={c.amount} sourceCurrency={c.currency} className="font-semibold" /> },
                  { key: "st", header: "وضعیت", render: (c) => <StatusText status={c.status} /> },
                  {
                    key: "act",
                    header: "عملیات",
                    render: (c) =>
                      canManage && c.status === "HELD" ? (
                        <div className="flex gap-1.5">
                          <button
                            type="button"
                            onClick={() => patchChequeMut.mutate({ id: c.id, status: "CLEARED" })}
                            className="rounded bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white"
                          >
                            وصول شد
                          </button>
                          <button
                            type="button"
                            onClick={() => patchChequeMut.mutate({ id: c.id, status: "BOUNCED" })}
                            className="rounded bg-rose-700 px-2.5 py-1 text-xs font-semibold text-white"
                          >
                            برگشت خورد
                          </button>
                        </div>
                      ) : (
                        "—"
                      ),
                  },
                ]}
              />
            </>
          )}
        </div>
      )}

      {tab === "ledgers" && (
        <DataTable
          rows={treasuryQ.data?.deal_ledgers || []}
          rowKey={(dl) => dl.id}
          isLoading={treasuryQ.isLoading}
          searchPlaceholder="جستجو در کد معامله..."
          columns={[
            { key: "code", header: "کد معامله", render: (dl) => <span className="font-mono text-xs font-bold">{dl.deal_code}</span> },
            { key: "amt", header: "مبلغ کل معامله", render: (dl) => <MoneyDisplay amount={dl.deal_amount} sourceCurrency={dl.currency} /> },
            { key: "rec", header: "دریافتی کل", render: (dl) => <MoneyDisplay amount={dl.total_received} sourceCurrency={dl.currency} className="text-emerald-800" /> },
            { key: "gross", header: "کمیسیون ناخالص", render: (dl) => <MoneyDisplay amount={dl.gross_commission} sourceCurrency={dl.currency} /> },
            { key: "agency", header: "سهم آژانس", render: (dl) => <MoneyDisplay amount={dl.agency_share} sourceCurrency={dl.currency} className="font-bold text-teal-800" /> },
            { key: "st", header: "وضعیت تسویه", render: (dl) => <StatusText status={dl.settlement_status} /> },
          ]}
        />
      )}

      <ModalDrawer
        open={jeModal}
        onClose={() => setJeModal(false)}
        title="ثبت سند حسابداری دوبل"
        subtitle="مجموع ستون بدهکار و بستانکار باید دقیقاً برابر باشد."
        widthClass="max-w-3xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!totals.isBalanced) {
              setErrMsg("سند تراز نیست؛ مجموع بدهکار باید برابر با مجموع بستانکار و بزرگ‌تر از صفر باشد.");
              return;
            }
            postJeMut.mutate();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              required
              placeholder="شماره سند"
              value={entryNumber}
              onChange={(e) => setEntryNumber(e.target.value)}
              className="h-10 rounded-lg border border-slate-300 px-3 font-mono text-sm"
            />
            <input
              required
              placeholder="شرح کلی سند"
              value={entryDesc}
              onChange={(e) => setEntryDesc(e.target.value)}
              className="h-10 rounded-lg border border-slate-300 px-3 text-sm"
            />
          </div>

          <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800">آرتیکل‌های سند</span>
              <button
                type="button"
                onClick={() =>
                  setEntryLines([...entryLines, { account_id: "", description: "", debit: "0", credit: "0" }])
                }
                className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-800"
              >
                <Plus className="h-3.5 w-3.5" />
                افزودن ردیف
              </button>
            </div>

            {entryLines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-12 items-center gap-2">
                <select
                  required
                  value={line.account_id}
                  onChange={(e) => {
                    const next = [...entryLines];
                    next[idx].account_id = e.target.value;
                    setEntryLines(next);
                  }}
                  className="col-span-4 h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs"
                >
                  <option value="">انتخاب سرفصل...</option>
                  {(coaQ.data || []).map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} — {a.name}
                    </option>
                  ))}
                </select>
                <input
                  placeholder="شرح ردیف"
                  value={line.description}
                  onChange={(e) => {
                    const next = [...entryLines];
                    next[idx].description = e.target.value;
                    setEntryLines(next);
                  }}
                  className="col-span-3 h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs"
                />
                <input
                  type="number"
                  min="0"
                  placeholder="بدهکار"
                  value={line.debit}
                  onChange={(e) => {
                    const next = [...entryLines];
                    next[idx].debit = e.target.value;
                    if (Number(e.target.value) > 0) next[idx].credit = "0";
                    setEntryLines(next);
                  }}
                  className="col-span-2 h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs tabular-nums"
                />
                <input
                  type="number"
                  min="0"
                  placeholder="بستانکار"
                  value={line.credit}
                  onChange={(e) => {
                    const next = [...entryLines];
                    next[idx].credit = e.target.value;
                    if (Number(e.target.value) > 0) next[idx].debit = "0";
                    setEntryLines(next);
                  }}
                  className="col-span-2 h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs tabular-nums"
                />
                <button
                  type="button"
                  disabled={entryLines.length <= 2}
                  onClick={() => setEntryLines(entryLines.filter((_, i) => i !== idx))}
                  className="col-span-1 flex h-9 items-center justify-center rounded-lg text-rose-700 hover:bg-rose-50 disabled:opacity-30"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}

            <div className="flex flex-wrap items-center justify-between border-t border-slate-200 pt-2.5 text-xs">
              <div className="flex gap-4 tabular-nums">
                <span>جمع بدهکار: <MoneyDisplay amount={totals.totalDebit} sourceCurrency="IRT" className="font-bold" /></span>
                <span>جمع بستانکار: <MoneyDisplay amount={totals.totalCredit} sourceCurrency="IRT" className="font-bold" /></span>
              </div>
              <span className={`font-bold ${totals.isBalanced ? "text-emerald-700" : "text-rose-700"}`}>
                {totals.isBalanced ? "تراز سند برقرار است" : "سند هنوز تراز نشده است"}
              </span>
            </div>
          </div>

          <button
            type="submit"
            disabled={!totals.isBalanced || postJeMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white disabled:opacity-50"
          >
            ثبت قطعی سند در دفتر روزنامه
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={coaModal} onClose={() => setCoaModal(false)} title="تعریف سرفصل حساب جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createCoaMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="کد حساب (مثال: 5020)"
            value={coaForm.code}
            onChange={(e) => setCoaForm({ ...coaForm, code: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm"
          />
          <input
            required
            placeholder="عنوان حساب (مثال: هزینه تبلیغات و آگهی)"
            value={coaForm.name}
            onChange={(e) => setCoaForm({ ...coaForm, name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <select
            value={coaForm.account_type}
            onChange={(e) => setCoaForm({ ...coaForm, account_type: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="ASSET">دارایی</option>
            <option value="LIABILITY">بدهی</option>
            <option value="EQUITY">سرمایه</option>
            <option value="REVENUE">درآمد</option>
            <option value="EXPENSE">هزینه</option>
          </select>
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت سرفصل
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={chequeModal} onClose={() => setChequeModal(false)} title="ثبت چک در خزانه‌داری">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createChequeMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            value={chequeForm.direction}
            onChange={(e) => setChequeForm({ ...chequeForm, direction: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="RECEIVABLE">چک دریافتنی</option>
            <option value="PAYABLE">چک پرداختنی</option>
          </select>
          <input
            required
            placeholder="شماره صیادی / چک"
            value={chequeForm.cheque_number}
            onChange={(e) => setChequeForm({ ...chequeForm, cheque_number: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm"
          />
          <input
            required
            placeholder="نام بانک صادرکننده"
            value={chequeForm.bank_name}
            onChange={(e) => setChequeForm({ ...chequeForm, bank_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              required
              type="date"
              value={chequeForm.due_date}
              onChange={(e) => setChequeForm({ ...chequeForm, due_date: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 px-3 text-sm"
            />
            <input
              required
              type="number"
              placeholder="مبلغ (تومان)"
              value={chequeForm.amount}
              onChange={(e) => setChequeForm({ ...chequeForm, amount: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 px-3 text-sm tabular-nums"
            />
          </div>
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت چک
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
