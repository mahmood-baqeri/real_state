// Path: frontend/src/app/terms/page.tsx

import React from "react";
import type { Metadata } from "next";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata: Metadata = {
  title: "قوانین و مقررات پلتفرم",
  description: "قوانین انتشار آگهی، اصالت اسناد، محاسبه کمیسیون و مسئولیت‌های آژانس‌های عضو بنیان ملک",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-12 sm:px-6 space-y-6">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">قوانین و مقررات پلتفرم بنیان ملک</h1>
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 space-y-5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          <section className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">۱. احراز اصالت فایل‌های ملکی</h2>
            <p className="text-xs">آژانس‌های عضو متعهد هستند پیش از انتشار عمومی هر آگهی در پورتال، وجود فیزیکی ملک، وضعیت سند و رضایت مالک را تایید نمایند.</p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">۲. شفافیت قیمتی و حقوقی</h2>
            <p className="text-xs">ثبت قیمت‌های صوری، آگهی تکراری یا اطلاعات گمراه‌کننده تخلف محسوب شده و توسط تیم بازرسی قابل پیگیری است.</p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">۳. ثبت وقایع و ممیزی مالی</h2>
            <p className="text-xs">کلیه اسناد حسابداری، قراردادها و تغییر سیاست‌های دسترسی با مهر زمانی و شناسه کاربر در گزارش ممیزی ثبت می‌شوند.</p>
          </section>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
