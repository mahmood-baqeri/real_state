"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, ClipboardList } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export default function NewPublicRequestPage() {
  const [form, setForm] = useState({
    full_name: "",
    phone_number: "",
    email: "",
    inquiry_type: "BUY_CONSULT",
    subject: "",
    message: "",
  });
  const [trackingCode, setTrackingCode] = useState<string | null>(null);

  const submitMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<{ tracking_code: string }>("/api/v1/public-requests/contact", {
          method: "POST",
          body: JSON.stringify(form),
        })
      ).data,
    onSuccess: (d) => setTrackingCode(d.tracking_code),
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 space-y-6">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-5 space-y-1.5">
            <div className="flex items-center gap-2 text-xs font-bold text-teal-700 dark:text-teal-400">
              <ClipboardList className="h-4 w-4" />
              ثبت درخواست تخصصی
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">ثبت درخواست خرید، فروش یا مشاوره ملک</h1>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              پس از ثبت درخواست، کد رهگیری یکتا صادر می‌شود و کارشناسان مربوطه پیگیری می‌کنند.
            </p>
          </div>

          {trackingCode ? (
            <div className="py-6 text-center space-y-3">
              <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-700 dark:text-emerald-400" />
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">درخواست شما ثبت شد</h2>
              <div className="inline-block rounded-lg border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 px-5 py-2 font-mono text-lg font-bold text-teal-700 dark:text-teal-400">
                {trackingCode}
              </div>
              <div>
                <Link href="/requests/track" className="text-xs font-semibold text-teal-700 dark:text-teal-400 underline">
                  ورود به صفحه پیگیری درخواست
                </Link>
              </div>
            </div>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                submitMut.mutate();
              }}
              className="space-y-4"
            >
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <input
                  required
                  placeholder="نام و نام خانوادگی *"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                />
                <input
                  required
                  dir="ltr"
                  placeholder="0912..."
                  value={form.phone_number}
                  onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
                />
              </div>
              <select
                value={form.inquiry_type}
                onChange={(e) => setForm({ ...form, inquiry_type: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
              >
                <option value="BUY_CONSULT">درخواست جستجو و خرید / رهن ملک</option>
                <option value="SELL_PROPERTY">درخواست کارشناسی و سپردن ملک</option>
                <option value="ENTERPRISE_DEMO">درخواست دموی سازمانی آژانس</option>
                <option value="GENERAL">سایر درخواست‌ها</option>
              </select>
              <input
                required
                placeholder="عنوان درخواست (مثلاً: خرید آپارتمان ۱۵۰ متری در سعادت‌آباد) *"
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
              />
              <textarea
                required
                rows={4}
                placeholder="مشخصات بودجه، متراژ، محله یا توضیحات تکمیلی..."
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-sm text-slate-900 dark:text-slate-100"
              />
              <button
                type="submit"
                disabled={submitMut.isPending}
                className="h-11 w-full rounded-xl bg-teal-700 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                ثبت درخواست و دریافت کد رهگیری
              </button>
            </form>
          )}
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
