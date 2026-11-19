// Path: frontend/src/app/complaints/new/page.tsx

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, ShieldAlert } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export default function NewPublicComplaintPage() {
  const [form, setForm] = useState({
    complainant_name: "",
    complainant_phone: "",
    target_type: "AGENCY",
    target_title: "",
    subject: "",
    description: "",
    is_confidential: true,
  });
  const [trackingCode, setTrackingCode] = useState<string | null>(null);

  const submitMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<{ tracking_code: string }>("/api/v1/complaints/public", {
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
            <div className="flex items-center gap-2 text-xs font-bold text-amber-700 dark:text-amber-400">
              <ShieldAlert className="h-4 w-4" />
              بازرسی و رسیدگی به تخلفات
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">ثبت شکایت یا گزارش تخلف</h1>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              پرونده‌های محرمانه مستقیماً در اختیار بازرسی مرکزی پلتفرم قرار می‌گیرد و یادداشت‌های بررسی افشا نمی‌شوند.
            </p>
          </div>

          {trackingCode ? (
            <div className="py-6 text-center space-y-3">
              <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-700 dark:text-emerald-400" />
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">شکایت شما ثبت شد</h2>
              <div className="inline-block rounded-lg border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 px-5 py-2 font-mono text-lg font-bold text-teal-700 dark:text-teal-400">
                {trackingCode}
              </div>
              <div>
                <Link href="/complaints/track" className="text-xs font-semibold text-teal-700 dark:text-teal-400 underline">
                  پیگیری وضعیت شکایت با کد رهگیری
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
                  placeholder="نام و نام خانوادگی شاکی *"
                  value={form.complainant_name}
                  onChange={(e) => setForm({ ...form, complainant_name: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                />
                <input
                  required
                  dir="ltr"
                  placeholder="0912..."
                  value={form.complainant_phone}
                  onChange={(e) => setForm({ ...form, complainant_phone: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
                />
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <select
                  value={form.target_type}
                  onChange={(e) => setForm({ ...form, target_type: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                >
                  <option value="AGENCY">آژانس املاک</option>
                  <option value="AGENT">مشاور املاک</option>
                  <option value="PROPERTY">آگهی یا قیمت غیرواقعی</option>
                  <option value="PLATFORM">عملکرد سامانه</option>
                </select>
                <input
                  placeholder="نام آژانس / مشاور / کد ملک مرتبط"
                  value={form.target_title}
                  onChange={(e) => setForm({ ...form, target_title: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                />
              </div>
              <input
                required
                placeholder="موضوع شکایت *"
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
              />
              <textarea
                required
                rows={4}
                placeholder="شرح دقیق موضوع..."
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-sm text-slate-900 dark:text-slate-100"
              />
              <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_confidential}
                  onChange={(e) => setForm({ ...form, is_confidential: e.target.checked })}
                  className="accent-teal-700"
                />
                پرونده به صورت محرمانه ثبت شود (دسترسی فقط برای بازرسی کل پلتفرم)
              </label>
              <button
                type="submit"
                disabled={submitMut.isPending}
                className="h-11 w-full rounded-xl bg-teal-700 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                ثبت شکایت و دریافت کد رهگیری
              </button>
            </form>
          )}
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
