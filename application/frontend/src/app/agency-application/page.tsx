// Path: frontend/src/app/agency-application/page.tsx

"use client";

import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Building2, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export default function AgencyApplicationPage() {
  const [form, setForm] = useState({
    agency_name: "",
    city: "تهران",
    manager_name: "",
    manager_phone: "",
    email: "",
    agents_count: 5,
    license_number: "",
    notes: "",
  });
  const [trackingCode, setTrackingCode] = useState<string | null>(null);

  const submitMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<{ tracking_code: string }>("/api/v1/public-requests/cooperation", {
          method: "POST",
          body: JSON.stringify(form),
        })
      ).data,
    onSuccess: (data) => {
      setTrackingCode(data.tracking_code);
    },
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 space-y-6">
          <div className="space-y-2 border-b border-slate-200 dark:border-slate-800 pb-5">
            <div className="flex items-center gap-2 text-xs font-bold text-teal-700 dark:text-teal-400">
              <Building2 className="h-4 w-4" />
              عضویت آژانس‌های املاک
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">درخواست همکاری و فعال‌سازی پنل آژانس</h1>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              پس از تایید درخواست توسط تیم نظارت بنیان ملک، فضای کاری اختصاصی و شناسه مدیریت آژانس برای شما صادر می‌شود.
            </p>
          </div>

          {trackingCode ? (
            <div className="rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50 dark:bg-emerald-950/30 p-6 text-center space-y-3">
              <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-700 dark:text-emerald-400" />
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">درخواست همکاری شما ثبت شد</h2>
              <p className="text-xs text-slate-600 dark:text-slate-300">کد رهگیری پرونده شما:</p>
              <div className="inline-block rounded-lg border border-emerald-300 dark:border-emerald-800 bg-white dark:bg-slate-900 px-5 py-2 font-mono text-lg font-bold text-teal-700 dark:text-teal-400">
                {trackingCode}
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
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <input
                  required
                  placeholder="نام رسمی آژانس / هلدینگ املاک *"
                  value={form.agency_name}
                  onChange={(e) => setForm({ ...form, agency_name: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                />
                <input
                  required
                  placeholder="شهر فعالیت *"
                  value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                />
                <input
                  required
                  placeholder="نام مدیر مسئول *"
                  value={form.manager_name}
                  onChange={(e) => setForm({ ...form, manager_name: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                />
                <input
                  required
                  dir="ltr"
                  placeholder="0912..."
                  value={form.manager_phone}
                  onChange={(e) => setForm({ ...form, manager_phone: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
                />
                <input
                  placeholder="شماره پروانه کسب اتحادیه"
                  value={form.license_number}
                  onChange={(e) => setForm({ ...form, license_number: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
                />
                <input
                  type="number"
                  min={1}
                  placeholder="تعداد مشاوران"
                  value={form.agents_count}
                  onChange={(e) => setForm({ ...form, agents_count: Number(e.target.value) })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
                />
              </div>
              <textarea
                rows={3}
                placeholder="مناطق تخصصی و توضیحات تکمیلی..."
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-sm text-slate-900 dark:text-slate-100"
              />
              {submitMut.error && (
                <div className="text-xs font-medium text-rose-600 dark:text-rose-400">
                  {submitMut.error instanceof Error ? submitMut.error.message : "خطا در ثبت درخواست"}
                </div>
              )}
              <button
                type="submit"
                disabled={submitMut.isPending}
                className="h-11 w-full rounded-xl bg-teal-700 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                {submitMut.isPending ? "در حال ارسال..." : "ارسال درخواست عضویت آژانس"}
              </button>
            </form>
          )}
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
