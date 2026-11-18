"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Mail, MapPin, Phone } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export default function ContactPage() {
  const [form, setForm] = useState({
    full_name: "",
    phone_number: "",
    email: "",
    inquiry_type: "GENERAL",
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
    onSuccess: (data) => setTrackingCode(data.tracking_code),
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-5">
            <div>
              <div className="text-xs font-bold text-teal-700 dark:text-teal-400">ارتباط مستقیم</div>
              <h1 className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">تماس با بنیان ملک</h1>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                برای دریافت مشاوره خرید، سپردن فایل ملکی، درخواست دموی سازمانی یا پیگیری درخواست‌ها با ما در ارتباط باشید.
              </p>
            </div>

            <div className="space-y-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 text-xs">
              <div className="flex items-center gap-2.5 text-slate-700 dark:text-slate-300">
                <Phone className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                <span className="font-mono" dir="ltr">021-22334455</span>
              </div>
              <div className="flex items-center gap-2.5 text-slate-700 dark:text-slate-300">
                <Mail className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                <span className="font-mono" dir="ltr">support@bonyanmelk.ir</span>
              </div>
              <div className="flex items-center gap-2.5 text-slate-700 dark:text-slate-300">
                <MapPin className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                <span>تهران، زعفرانیه، خیابان مقدس اردبیلی</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 text-xs">
              <Link href="/requests/track" className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 font-semibold text-teal-700 dark:text-teal-400">
                پیگیری درخواست با کد رهگیری ←
              </Link>
              <Link href="/complaints/new" className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 font-semibold text-slate-700 dark:text-slate-300">
                ثبت شکایت یا گزارش تخلف
              </Link>
            </div>
          </div>

          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8">
              {trackingCode ? (
                <div className="py-6 text-center space-y-3">
                  <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-700 dark:text-emerald-400" />
                  <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">پیام شما ثبت شد</h2>
                  <p className="text-xs text-slate-600 dark:text-slate-400">کد رهگیری درخواست شما:</p>
                  <div className="inline-block rounded-lg border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 px-4 py-2 font-mono text-base font-bold text-teal-700 dark:text-teal-400">
                    {trackingCode}
                  </div>
                  <div>
                    <Link href="/requests/track" className="text-xs font-semibold text-teal-700 dark:text-teal-400 underline">
                      مشاهده وضعیت پیگیری
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
                    <option value="GENERAL">سؤال و ارتباط عمومی</option>
                    <option value="BUY_CONSULT">مشاوره خرید یا اجاره ملک</option>
                    <option value="SELL_PROPERTY">سپردن فایل فروش یا اجاره</option>
                    <option value="ENTERPRISE_DEMO">درخواست دموی سازمانی آژانس</option>
                  </select>
                  <input
                    required
                    placeholder="موضوع پیام *"
                    value={form.subject}
                    onChange={(e) => setForm({ ...form, subject: e.target.value })}
                    className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                  />
                  <textarea
                    required
                    rows={4}
                    placeholder="متن کامل پیام..."
                    value={form.message}
                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-sm text-slate-900 dark:text-slate-100"
                  />
                  <button
                    type="submit"
                    disabled={submitMut.isPending}
                    className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                  >
                    ارسال پیام و دریافت کد رهگیری
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
