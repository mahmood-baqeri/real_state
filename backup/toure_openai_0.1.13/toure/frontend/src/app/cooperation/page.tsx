import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Building2, Handshake, Layers } from "lucide-react";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata: Metadata = {
  title: "همکاری آژانس‌های املاک",
  description: "شرایط پیوستن آژانس‌های املاک معتبر به شبکه همکاری بین‌آژانسی و پلتفرم بنیان ملک",
};

export default function CooperationPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-10">
        <div className="space-y-3">
          <div className="text-xs font-bold text-teal-700 dark:text-teal-400">شبکه همکاری آژانس‌های معتبر</div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
            مدل همکاری آژانس‌ها و معاملات مشارکتی بین‌دفاتری
          </h1>
          <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            با عضویت در شبکه بنیان ملک، علاوه بر داشتن پنل سازمانی مستقل برای مدیریت داخلی آژانس خود، می‌توانید فایل‌های منتخب را با قرارداد تقسیم پورسانت شفاف با آژانس‌های همکار به اشتراک بگذارید.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Building2 className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">پنل و برند اختصاصی آژانس</h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              تعریف نامحدود شعب، مشاوران، قوانین دسترسی داخلی و مدیریت کامل حسابداری و حقوق.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Handshake className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">قرارداد همکاری بین‌آژانسی</h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              تعیین درصد سهم کمیسیون مشارکتی در معاملات مشترک بدون نیاز به افشای شماره تماس مالکین.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Layers className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">انتشار تاییدشده در پورتال</h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              جذب سرنخ‌های واقعی خریداران و مستاجران مستقیماً در کارتابل مشاور مسئول آژانس شما.
            </p>
          </div>
        </div>

        <Link
          href="/agency-application"
          className="inline-flex h-11 items-center rounded-lg bg-teal-700 px-6 text-sm font-semibold text-white hover:bg-teal-800"
        >
          تکمیل فرم درخواست عضویت آژانس
        </Link>
      </main>
      <PublicFooter />
    </div>
  );
}
