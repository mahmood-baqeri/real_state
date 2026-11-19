// Path: frontend/src/app/services/page.tsx

import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata: Metadata = {
  title: "خدمات و استقرار سازمانی",
  description: "خدمات استقرار، مهاجرت داده‌ها، آموزش تیم فروش و مشاوره مالی برای آژانس‌های املاک",
};

const SERVICES = [
  {
    title: "استقرار و انتقال داده آژانس‌های بزرگ",
    desc: "ورود امن فایل‌های ملکی، مشتریان و دفتر کل حسابداری قبلی شما بدون توقف فعالیت روزانه مشاوران.",
    points: ["پاک‌سازی و استانداردسازی اطلاعات فایل‌ها", "تعریف شعب، نقش‌ها و ماتریس دسترسی", "اتصال درگاه پرداخت و پیامک سازمانی"],
  },
  {
    title: "طراحی قالب‌های حقوقی و فرمول‌های کمیسیون",
    desc: "پیاده‌سازی دقیق سیاست‌های تقسیم پورسانت درصدی، پلکانی و مشارکتی همراه با قالب‌های مبایعه‌نامه و اجاره‌نامه.",
    points: ["سیاست‌های نسخه‌دار کمیسیون", "تنظیم حساب‌های معین و کل در دفتر کل", "پیکربندی حقوق ثابت و پورسانت"],
  },
  {
    title: "آموزش تخصصی مدیران، حسابداران و مشاوران",
    desc: "کارگاه‌های عملی کار با پایپ‌لاین ۱۲مرحله‌ای CRM، مدیریت بازدیدها، چک‌های خزانه و گزارش‌گیری مدیریتی.",
    points: ["پشتیبانی اختصاصی با SLA تضمین‌شده", "مانیتورینگ شاخص رضایت مشتریان (NPS)", "به‌روزرسانی مستمر امکانات"],
  },
];

export default function ServicesPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-10">
        <div className="max-w-2xl space-y-2">
          <div className="text-xs font-bold text-teal-700 dark:text-teal-400">خدمات حرفه‌ای بنیان ملک</div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">خدمات استقرار، مهاجرت داده و مشاوره تخصصی</h1>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {SERVICES.map((s) => (
            <div key={s.title} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 space-y-4">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">{s.title}</h2>
              <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">{s.desc}</p>
              <ul className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                {s.points.map((pt) => (
                  <li key={pt} className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-teal-700 dark:text-teal-400" />
                    {pt}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-3">
          <Link href="/requests/new" className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-5 text-xs font-semibold text-white">
            ثبت درخواست مشاوره و دمو
          </Link>
          <Link href="/cooperation" className="inline-flex h-10 items-center rounded-lg border border-slate-300 dark:border-slate-700 px-5 text-xs font-semibold text-slate-800 dark:text-slate-200">
            مدل همکاری آژانس‌ها
          </Link>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
