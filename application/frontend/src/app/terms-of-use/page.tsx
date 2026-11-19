// Path: frontend/src/app/terms-of-use/page.tsx

import React from "react";
import type { Metadata } from "next";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata: Metadata = {
  title: "شرایط استفاده از خدمات",
  description: "شرایط بهره‌برداری از خدمات نرم‌افزاری، اشتراک‌های ماهانه و درگاه‌های پرداخت در بنیان ملک",
};

export default function TermsOfUsePage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-12 sm:px-6 space-y-6">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">شرایط استفاده از خدمات (Terms of Use)</h1>
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 space-y-5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          <section className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">۱. محدوده استفاده مجاز</h2>
            <p className="text-xs">حساب‌های کاربری آژانس بر اساس نقش‌های تعیین‌شده (مدیر، حسابدار، مشاور) و سقف پلن اشتراک فعال قابل استفاده هستند.</p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">۲. مالکیت داده‌ها</h2>
            <p className="text-xs">مالکیت کلیه فایل‌ها، قراردادها و اسناد حسابداری ثبت‌شده متعلق به آژانس عضو بوده و امکان دریافت خروجی استاندارد CSV از جداول فراهم است.</p>
          </section>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
