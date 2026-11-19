// Path: frontend/src/app/about/page.tsx

import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Building2, Shield, Users } from "lucide-react";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata: Metadata = {
  title: "درباره ما",
  description: "آشنایی با ماموریت، معماری امنیتی و استانداردهای سازمانی پلتفرم املاک بنیان ملک",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-10">
        <div className="space-y-3">
          <div className="text-xs font-bold text-teal-700 dark:text-teal-400">درباره بنیان ملک</div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
            زیرساخت اعتماد، شفافیت مالی و مدیریت علمی در بازار املاک
          </h1>
          <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            بنیان ملک با هدف استانداردسازی عملیات آژانس‌های املاک، حفاظت از حریم خصوصی مالکین و متقاضیان، و ارائه ابزارهای دقیق مالی و حقوقی توسعه یافته است.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Shield className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">ایزوله‌سازی سخت‌گیرانه داده‌ها</h2>
            <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              فایل‌های اختصاصی و فهرست مشتریان هر آژانس کاملاً ایزوله است و پلاک و اطلاعات مالک بدون مجوز افشا نمی‌شود.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Building2 className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">پشتیبانی از شبکه‌های چندشعبه‌ای</h2>
            <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              طراحی‌شده برای دفاتر تک‌شعبه‌ای تا هلدینگ‌های املاک با ده‌ها شعبه، قراردادهای همکاری متقابل و حسابداری یکپارچه.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Users className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">تیم مهندسی و حقوقی متخصص</h2>
            <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              همراهی مداوم با مدیران آژانس‌ها برای انطباق قالب‌های قرارداد، محاسبات مالیاتی و گزارش‌های مدیریتی.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link href="/careers" className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-5 text-xs font-semibold text-white">
            فرصت‌های شغلی و پیوستن به تیم
          </Link>
          <Link href="/contact" className="inline-flex h-10 items-center rounded-lg border border-slate-300 dark:border-slate-700 px-5 text-xs font-semibold text-slate-800 dark:text-slate-200">
            تماس با ما
          </Link>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
