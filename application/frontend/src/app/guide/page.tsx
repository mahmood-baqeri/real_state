import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { BookOpen } from "lucide-react";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata: Metadata = {
  title: "راهنمای استفاده از سامانه",
  description: "راهنمای گام‌به‌گام برای متقاضیان ملک، مشاوران املاک، مدیران آژانس و حسابداران در بنیان ملک",
};

const GUIDES = [
  {
    role: "متقاضیان خرید و اجاره",
    steps: [
      "در جستجوی پیشرفته شهر، محله و بودجه خود را فیلتر کنید.",
      "در صفحه جزئیات هر ملک، زمان بازدید حضوری را ثبت و پیگیری نمایید.",
      "در صورت نیاز به مشاوره اختصاصی یا شکایت، از کد رهگیری یکتا برای پیگیری استفاده کنید.",
    ],
  },
  {
    role: "مشاوران املاک",
    steps: [
      "پس از ورود، فایل‌های جدید را با مشخصات کامل ثبت و برای تایید مدیر ارسال کنید.",
      "از بخش CRM و تطبیق هوشمند، خریداران متناسب با هر ملک را شناسایی نمایید.",
      "بازدیدها، پیشنهادهای قیمتی مذاکره و تیکت‌های خود را در کارتابل پیگیری کنید.",
    ],
  },
  {
    role: "مدیران آژانس و حسابداران",
    steps: [
      "تنظیمات دسترسی ۱۰گانه آژانس، شعب و تعرفه‌های کمیسیون را پیکربندی کنید.",
      "معاملات نهایی را تایید کرده و اسناد حسابداری دوطرفه و چک‌های خزانه را کنترل نمایید.",
      "در پایان ماه، چرخه حقوق و دستمزد را اجرا و فیش حقوقی مشاوران را صادر کنید.",
    ],
  },
];

export default function GuidePage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-8">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-teal-700 dark:text-teal-400">
            <BookOpen className="h-4 w-4" />
            راهنمای جامع کاربری
          </div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">راهنمای گام‌به‌گام استفاده از بنیان ملک</h1>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {GUIDES.map((g) => (
            <div key={g.role} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 space-y-4">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">{g.role}</h2>
              <ol className="list-decimal list-inside space-y-2.5 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                {g.steps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-3">
          <Link href="/faq" className="inline-flex h-10 items-center rounded-lg border border-slate-300 dark:border-slate-700 px-4 text-xs font-semibold text-slate-800 dark:text-slate-200">
            مشاهده سؤالات متداول
          </Link>
          <Link href="/login" className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-5 text-xs font-semibold text-white">
            ورود به سامانه
          </Link>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
