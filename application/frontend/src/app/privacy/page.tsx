import React from "react";
import type { Metadata } from "next";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata: Metadata = {
  title: "سیاست حریم خصوصی",
  description: "نحوه حفاظت از اطلاعات هویتی مالکین، مشتریان و رمزنگاری داده‌های حساس در بنیان ملک",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-12 sm:px-6 space-y-6">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">سیاست حریم خصوصی و حفاظت از داده‌ها</h1>
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 space-y-5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          <section className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">۱. محرمانگی اطلاعات مالکین و پلاک دقیق</h2>
            <p className="text-xs">شماره تماس مالک، کد ملی و پلاک دقیق ملک در جستجوی عمومی پنهان است و صرفاً مطابق سیاست دسترسی ۱۰گانه آژانس به افراد مجاز نمایش داده می‌شود.</p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">۲. ایزوله‌سازی چندآژانسی و دستیار هوشمند</h2>
            <p className="text-xs">فهرست مشتریان و سوابق مالی هر آژانس هرگز برای آژانس‌های دیگر قابل مشاهده نیست و ابزارهای هوش مصنوعی صرفاً درون داده‌های مجاز همان آژانس اجرا می‌شوند.</p>
          </section>
          <section className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">۳. مدیریت نشست‌ها و اعلان‌های پوش</h2>
            <p className="text-xs">کاربران می‌توانند در بخش پروفایل و تنظیمات اعلان‌ها، نشست‌های فعال خود را لغو یا اشتراک وب‌پوش را در هر لحظه غیرفعال کنند.</p>
          </section>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
