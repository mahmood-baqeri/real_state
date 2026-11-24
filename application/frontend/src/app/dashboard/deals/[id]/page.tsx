"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, Handshake, Wallet, CalendarDays, ClipboardCheck, Plus } from "lucide-react";
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
  deal_room?: { checklist?: { id: string; title: string; done: boolean }[]; events?: { id: string; title: string; date: string; note?: string }[] };
  payment_schedule?: { items?: { id: string; title: string; due_date: string; amount: string; status: "planned" | "paid"; note?: string }[] };
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
  const [eventTitle, setEventTitle] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [eventNote, setEventNote] = useState("");
  const [payTitle, setPayTitle] = useState("");
  const [payDate, setPayDate] = useState("");
  const [payAmount, setPayAmount] = useState("");
  const [payNote, setPayNote] = useState("");

  const detailQ = useQuery({
    queryKey: ["deal-detail", id, activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId && !!id,
    queryFn: async () =>
      (await apiFetch<DealDetail>(`/api/v1/deals/${id}`, {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const roomMut = useMutation({
    mutationFn: async (room: { checklist: { id: string; title: string; done: boolean }[]; events: { id: string; title: string; date: string; note?: string }[] }) =>
      apiFetch(`/api/v1/deals/${id}/room`, { method: "PUT", token: accessToken, agencyId: activeAgencyId, body: JSON.stringify(room) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["deal-detail", id, activeAgencyId] }); toast.success("اتاق معامله ذخیره شد."); },
    onError: (e: Error) => toast.error(e.message),
  });


  const scheduleMut = useMutation({
    mutationFn: async (items: NonNullable<DealDetail["payment_schedule"]>["items"] = []) =>
      apiFetch(`/api/v1/deals/${id}/payment-schedule`, { method: "PUT", token: accessToken, agencyId: activeAgencyId, body: JSON.stringify({ items }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["deal-detail", id, activeAgencyId] }); toast.success("برنامه پرداخت ذخیره شد."); },
    onError: (e: Error) => toast.error(e.message),
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

      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <h2 className="flex items-center gap-2 text-sm font-bold"><Wallet className="h-4 w-4 text-teal-700" /> برنامه اقساط و سررسیدها</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
          <input value={payTitle} onChange={e => setPayTitle(e.target.value)} placeholder="عنوان پرداخت (مثلاً پیش‌پرداخت)" className="h-9 rounded-md border px-3 text-xs dark:bg-slate-950 dark:border-slate-700" />
          <input type="date" value={payDate} onChange={e => setPayDate(e.target.value)} className="h-9 rounded-md border px-3 text-xs dark:bg-slate-950 dark:border-slate-700" />
          <input type="number" min="0" value={payAmount} onChange={e => setPayAmount(e.target.value)} placeholder="مبلغ" className="h-9 rounded-md border px-3 text-xs dark:bg-slate-950 dark:border-slate-700" />
          <button disabled={scheduleMut.isPending || !payTitle.trim() || !payDate || !payAmount} onClick={() => { const items = deal.payment_schedule?.items || []; scheduleMut.mutate([...items, { id: `pay-${Date.now()}`, title: payTitle.trim(), due_date: payDate, amount: payAmount, status: "planned" as const, note: payNote.trim() }]); setPayTitle(""); setPayDate(""); setPayAmount(""); setPayNote(""); }} className="h-9 rounded-md bg-teal-700 px-3 text-xs font-semibold text-white disabled:opacity-50">افزودن سررسید</button>
        </div>
        <input value={payNote} onChange={e => setPayNote(e.target.value)} placeholder="توضیحات اختیاری" className="h-9 w-full rounded-md border px-3 text-xs dark:bg-slate-950 dark:border-slate-700" />
        {(() => { const items = deal.payment_schedule?.items || []; const total = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0); const paid = items.filter(x => x.status === "paid").reduce((sum, item) => sum + (Number(item.amount) || 0), 0); return <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-3"><div className="rounded border p-2"><span className="text-slate-500">جمع برنامه</span><p className="font-bold">{total.toLocaleString("fa-IR")} {deal.currency}</p></div><div className="rounded border p-2"><span className="text-slate-500">علامت‌خورده پرداخت</span><p className="font-bold text-emerald-700">{paid.toLocaleString("fa-IR")} {deal.currency}</p></div><div className="rounded border p-2"><span className="text-slate-500">باقی برنامه</span><p className="font-bold">{Math.max(0, total-paid).toLocaleString("fa-IR")} {deal.currency}</p></div></div>; })()}
        <ul className="space-y-2">{(deal.payment_schedule?.items || []).slice().sort((a,b) => a.due_date.localeCompare(b.due_date)).map(item => <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded border p-3 text-xs"><div><div className="font-semibold">{item.title} — {item.due_date}</div><div className="mt-1 text-slate-500">{Number(item.amount).toLocaleString("fa-IR")} {deal.currency}{item.note ? ` · ${item.note}` : ""}</div></div><div className="flex gap-2"><button disabled={scheduleMut.isPending} onClick={() => scheduleMut.mutate((deal.payment_schedule?.items || []).map(x => x.id === item.id ? { ...x, status: (x.status === "paid" ? "planned" : "paid") as "paid" | "planned" } : x))} className={`rounded px-2 py-1 ${item.status === "paid" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"}`}>{item.status === "paid" ? "پرداخت شد ✓" : "علامت پرداخت"}</button><button disabled={scheduleMut.isPending} onClick={() => scheduleMut.mutate((deal.payment_schedule?.items || []).filter(x => x.id !== item.id))} className="text-rose-600">حذف</button></div></li>)}{!(deal.payment_schedule?.items?.length) && <li className="text-xs text-slate-500">سررسیدی ثبت نشده است.</li>}</ul>
        <p className="text-[11px] text-amber-700 dark:text-amber-400">این بخش فقط برنامه و وضعیت سررسیدها را نگه می‌دارد؛ علامت پرداخت، ثبت دریافت در کاردکس مالی نیست.</p>
      </section>

      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <h2 className="flex items-center gap-2 text-sm font-bold"><ClipboardCheck className="h-4 w-4 text-teal-700" /> اتاق معامله — چک‌لیست و تقویم</h2>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div className="space-y-3">
            <h3 className="text-xs font-semibold">چک‌لیست پیشرفت</h3>
            {((deal.deal_room?.checklist?.length ? deal.deal_room.checklist : [
              { id: "docs", title: "تکمیل و بررسی مدارک طرفین", done: false },
              { id: "deposit", title: "ثبت پرداخت‌ها و بیعانه", done: false },
              { id: "inspection", title: "تأیید بازدید و بررسی ملک", done: false },
              { id: "contract", title: "بررسی و امضای قرارداد", done: false },
              { id: "handover", title: "تحویل ملک و کلید", done: false },
            ])).map((item) => (
              <label key={item.id} className="flex items-center gap-2 rounded-md border border-slate-200 dark:border-slate-700 p-2 text-xs">
                <input type="checkbox" checked={item.done} disabled={roomMut.isPending} onChange={(e) => {
                  const current = deal.deal_room?.checklist?.length ? deal.deal_room.checklist : [
                    { id: "docs", title: "تکمیل و بررسی مدارک طرفین", done: false }, { id: "deposit", title: "ثبت پرداخت‌ها و بیعانه", done: false }, { id: "inspection", title: "تأیید بازدید و بررسی ملک", done: false }, { id: "contract", title: "بررسی و امضای قرارداد", done: false }, { id: "handover", title: "تحویل ملک و کلید", done: false },
                  ];
                  roomMut.mutate({ checklist: current.map((x) => x.id === item.id ? { ...x, done: e.target.checked } : x), events: deal.deal_room?.events || [] });
                }} />
                <span className={item.done ? "line-through text-slate-500" : ""}>{item.title}</span>
              </label>
            ))}
          </div>
          <div className="space-y-3">
            <h3 className="flex items-center gap-1 text-xs font-semibold"><CalendarDays className="h-4 w-4" /> برنامه و رویدادهای معامله</h3>
            <form className="grid grid-cols-1 gap-2" onSubmit={(e) => { e.preventDefault(); if (!eventTitle.trim() || !eventDate) return; const ev = { id: `ev-${Date.now()}`, title: eventTitle.trim(), date: eventDate, note: eventNote.trim() }; roomMut.mutate({ checklist: deal.deal_room?.checklist || [{ id: "docs", title: "تکمیل و بررسی مدارک طرفین", done: false }, { id: "deposit", title: "ثبت پرداخت‌ها و بیعانه", done: false }, { id: "inspection", title: "تأیید بازدید و بررسی ملک", done: false }, { id: "contract", title: "بررسی و امضای قرارداد", done: false }, { id: "handover", title: "تحویل ملک و کلید", done: false }], events: [...(deal.deal_room?.events || []), ev] }); setEventTitle(""); setEventDate(""); setEventNote(""); }}>
              <input value={eventTitle} onChange={(e) => setEventTitle(e.target.value)} placeholder="عنوان رویداد (مثلاً دفترخانه)" required className="h-9 rounded-md border px-3 text-xs dark:bg-slate-950 dark:border-slate-700" />
              <input type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)} required className="h-9 rounded-md border px-3 text-xs dark:bg-slate-950 dark:border-slate-700" />
              <input value={eventNote} onChange={(e) => setEventNote(e.target.value)} placeholder="یادداشت اختیاری" className="h-9 rounded-md border px-3 text-xs dark:bg-slate-950 dark:border-slate-700" />
              <button type="submit" disabled={roomMut.isPending} className="inline-flex h-9 items-center justify-center gap-1 rounded-md bg-teal-700 px-3 text-xs font-semibold text-white disabled:opacity-50"><Plus className="h-4 w-4" /> افزودن رویداد</button>
            </form>
            <ul className="space-y-2">
              {(deal.deal_room?.events || []).slice().sort((a,b) => a.date.localeCompare(b.date)).map((ev) => <li key={ev.id} className="rounded-md border border-slate-200 dark:border-slate-700 p-2 text-xs"><div className="font-semibold">{ev.title} — {ev.date}</div>{ev.note && <div className="mt-1 text-slate-500">{ev.note}</div>}<button type="button" onClick={() => roomMut.mutate({ checklist: deal.deal_room?.checklist || [], events: (deal.deal_room?.events || []).filter(x => x.id !== ev.id) })} className="mt-1 text-rose-600">حذف</button></li>)}
              {!deal.deal_room?.events?.length && <li className="text-xs text-slate-500">رویدادی ثبت نشده است.</li>}
            </ul>
          </div>
        </div>
      </section>

    </div>
  );
}
