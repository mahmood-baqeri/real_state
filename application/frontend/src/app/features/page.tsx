// Path: frontend/src/app/features/page.tsx

import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Bot, Building2, Calculator, FileCheck2, Lock, ShieldCheck, Users } from "lucide-react";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export const metadata: Metadata = {
  title: "امکانات سامانه",
  description: "آشنایی با ماژول‌های CRM، حسابداری دوطرفه، مدیریت کمیسیون، امنیت چندآژانسی و دستیار هوشمند بنیان ملک",
};

const MODULES = [
  {
    icon: Lock,
    title: "معماری چندآژانسی و کنترل دسترسی ۱۰گانه",
    desc: "جداسازی کامل داده‌های هر آژانس در سطح ORM و API با تنظیمات دقیق برای مشاهده املاک، مشتریان، اطلاعات تماس مالکین و عملکرد مشاوران.",
  },
  {
    icon: Users,
    title: "پایپ‌لاین ۱۲مرحله‌ای CRM و تطبیق هوشمند",
    desc: "مدیریت سرنخ‌ها، اشتراک‌گذاری خصوصی مشتریان بین مشاوران، امتیازدهی آمادگی خرید و تطبیق خودکار فایل‌ها با نیاز مشتریان.",
  },
  {
    icon: FileCheck2,
    title: "مذاکرات نسخه‌دار و قراردادهای رسمی",
    desc: "ثبت پیشنهادهای متقابل خریدار و فروشنده، قالب‌های قرارداد تأییدشده توسط مدیر آژانس و آرشیو اسناد محرمانه با کنترل دسترسی.",
  },
  {
    icon: Calculator,
    title: "حسابداری دوطرفه، خزانه‌داری چک و کمیسیون",
    desc: "محاسبه دقیق اعشاری سهم مشاور اول، همکار و آژانس، صدور خودکار سند حسابداری متوازن، تراز آزمایشی، صورت‌های مالی و فیش حقوقی.",
  },
  {
    icon: Bot,
    title: "دستیار هوشمند ایزوله آژانس",
    desc: "تولید پیش‌نویس متن آگهی ملک، خلاصه‌سازی پرونده CRM و پیشنهاد متادیتای سئو صرفاً روی داده‌های مجاز هر آژانس و بدون انتشار خودکار.",
  },
  {
    icon: ShieldCheck,
    title: "تیکت پشتیبانی با SLA، شکایات و نظرسنجی NPS",
    desc: "مدیریت تیکت‌های پشتیبانی، پیگیری محرمانه شکایات با کد رهگیری عمومی و فرم‌ساز نظرسنجی ۸گانه با گزارش تحلیلی NPS.",
  },
];

export default function FeaturesPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-12">
        <div className="max-w-3xl space-y-3">
          <div className="text-xs font-bold text-teal-700 dark:text-teal-400">زیرساخت یکپارچه PropTech</div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
            تمام ابزارهای مورد نیاز یک آژانس املاک سازمانی در یک پلتفرم
          </h1>
          <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            بنیان ملک برای حذف جزیره‌های اطلاعاتی در دفاتر املاک طراحی شده است؛ از لحظه ثبت سرنخ و هماهنگی بازدید تا امضای مبایعه‌نامه، تقسیم پورسانت و صدور ترازنامه مالی.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m) => {
            const Icon = m.icon;
            return (
              <div key={m.title} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 space-y-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 dark:bg-teal-950/50 text-teal-700 dark:text-teal-400">
                  <Icon className="h-5 w-5" />
                </div>
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">{m.title}</h2>
                <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">{m.desc}</p>
              </div>
            );
          })}
        </div>

        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Building2 className="h-5 w-5 text-teal-700 dark:text-teal-400" />
              آماده استقرار برای آژانس یا شبکه شعب خود هستید؟
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              پلن‌های اشتراک را بررسی کنید یا درخواست دموی اختصاصی ثبت نمایید.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/pricing" className="inline-flex h-10 items-center rounded-lg border border-slate-300 dark:border-slate-700 px-4 text-xs font-semibold text-slate-800 dark:text-slate-200">
              مشاهده تعرفه‌ها
            </Link>
            <Link href="/agency-application" className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-5 text-xs font-semibold text-white hover:bg-teal-800">
              ثبت درخواست عضویت آژانس
            </Link>
          </div>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
