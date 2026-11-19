"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check } from "lucide-react";

interface RoleSpec {
  id: string;
  label: string;
  title: string;
  summary: string;
  phone: string;
  image: string;
  imageCaption: string;
  highlights: string[];
  metrics: { label: string; value: string }[];
}

const ROLE_SPECS: RoleSpec[] = [
  {
    id: "SUPER_ADMIN",
    label: "مدیر کل پلتفرم",
    title: "نظارت سراسری بر تمام آژانس‌ها، اشتراک‌ها و CMS",
    summary:
      "کنترل تأیید درخواست همکاری آژانس‌های جدید، مدیریت پلن‌های اشتراک، انتشار محتوای مجله تخصصی و پایش لاگ ممیزی در مقیاس کلان پلتفرم.",
    phone: "09120000001",
    image: "/images/studio-agency-office.jpg",
    imageCaption: "ستاد مرکزی پلتفرم سازمانی بنیان ملک",
    highlights: [
      "تأیید و فعال‌سازی آژانس‌های جدید و مدیریت وضعیت تعلیق",
      "مدیریت متمرکز درگاه‌های پرداخت، پیامک، نقشه و ارزها",
      "انتشار مقالات تخصصی، ریدایرکت‌های سئو و فرصت‌های شغلی",
      "ممیزی سراسری رویدادهای حساس مالی و کاربری",
    ],
    metrics: [
      { label: "سطح دسترسی", value: "کل پلتفرم" },
      { label: "کنترل مستأجرها", value: "چندآژانسی" },
      { label: "سیاست داده", value: "ایزوله کامل" },
    ],
  },
  {
    id: "AGENCY_MANAGER",
    label: "مدیر آژانس",
    title: "فرماندهی کامل شعب، فایل‌ها، سیاست‌های دسترسی و قراردادها",
    summary:
      "تنظیم دقیق ۱۰ سیاست دسترسی آژانس، تأیید نهایی انتشار فایل‌های ملکی در پورتال عمومی، بررسی عملکرد مشاوران و کنترل جریان نقدینگی.",
    phone: "09121111111",
    image: "/images/hero-penthouse-tehran.jpg",
    imageCaption: "پورتال اختصاصی املاک لوکس و مدیریت فایل",
    highlights: [
      "تأیید و انتشار عمومی املاک ثبت‌شده توسط مشاوران",
      "پیکربندی ۱۰ سیاست دسترسی مجزا برای مالک، فایل و کمیسیون",
      "مدیریت شعب چندگانه، هم‌فروشی بین آژانس‌ها و قالب قراردادها",
      "پایش تابلوی رهبری عملکرد تیم فروش در بازه‌های زمانی دلخواه",
    ],
    metrics: [
      { label: "دامنه کنترل", value: "کل شعب آژانس" },
      { label: "سیاست‌های RBAC", value: "۱۰ حوزه مستقل" },
      { label: "گزارش مدیریتی", value: "لحظه‌ای" },
    ],
  },
  {
    id: "BRANCH_MANAGER",
    label: "مدیر شعبه",
    title: "مدیریت متمرکز تیم مشاوران، بازدیدها و سرنخ‌های شعبه",
    summary:
      "نظارت مستقیم بر کیفیت فایل‌های شعبه، توزیع سرنخ‌های ورودی بین مشاوران، پیگیری مذاکرات باز و هماهنگی بازدیدهای منطقه‌ای.",
    phone: "09125555555",
    image: "/images/modern-villa-facade.jpg",
    imageCaption: "شعبه تخصصی نیاوران و فرمانیه",
    highlights: [
      "پایش اختصاصی فایل‌ها و قراردادهای شعبه تحت سرپرستی",
      "تخصیص هوشمند سرنخ‌ها و نظارت بر وظایف پیگیری CRM",
      "بررسی بازدیدهای زمان‌بندی‌شده و جلوگیری از تداخل تقویم",
      "رسیدگی سریع به تیکت‌های عملیاتی و شکایات مرتبط با شعبه",
    ],
    metrics: [
      { label: "دامنه نظارت", value: "شعبه نیاوران" },
      { label: "اختیار تأیید فایل", value: "فعال (Override)" },
      { label: "اشتراک مشتری", value: "درون‌شعبه‌ای" },
    ],
  },
  {
    id: "AGENT",
    label: "مشاور املاک",
    title: "میز کار چابک فروش، CRM دوازده‌مرحله‌ای و تطبیق هوشمند",
    summary:
      "ثبت سریع مشخصات و تصاویر ملک، مدیریت مشتریان خریدار و مالک با حفاظت PII، دریافت امتیاز تطبیق هوشمند و پیگیری شفاف سهم پورسانت.",
    phone: "09122222222",
    image: "/images/prop-fereshteh.jpg",
    imageCaption: "فایل‌های تأییدشده منطقه فرشته و زعفرانیه",
    highlights: [
      "پایپ‌لاین ۱۲مرحله‌ای مشتری از سرنخ تا بسته‌شدن قرارداد",
      "زمان‌بندی بازدید بدون تداخل و ثبت گزارش بازدید",
      "ثبت پیشنهاد و پاسخ پیشنهاد نسخه‌دار در فرایند مذاکره",
      "تولید پیش‌نویس متون معرفی ملک با دستیار هوشمند آژانس",
    ],
    metrics: [
      { label: "مراحل پایپ‌لاین", value: "۱۲ مرحله" },
      { label: "محاسبه پورسانت", value: "خودکار و شفاف" },
      { label: "دسترسی مالی کل", value: "محدود به سهم خود" },
    ],
  },
  {
    id: "AGENCY_ACCOUNTANT",
    label: "حسابدار آژانس",
    title: "حسابداری دوطرفه متوازن، خزانه‌داری چک و حقوق و دستمزد",
    summary:
      "کدینگ درختی حساب‌ها، صدور اسناد حسابداری تغییرناپذیر با قابلیت سند معکوس، مدیریت چک‌های دریافتنی و پرداختنی و محاسبه فیش حقوقی.",
    phone: "09126666666",
    image: "/images/studio-agency-office.jpg",
    imageCaption: "میز کار مالی و دفتر کل یکپارچه آژانس",
    highlights: [
      "کنترل توازن بدهکار و بستانکار در تمام اسناد حسابداری قطعی",
      "دفتر کل مالی اختصاصی برای هر معامله (Deal Financial Ledger)",
      "ردیابی سررسید چک‌ها، موجودی حساب‌های بانکی و تنخواه صندوق",
      "تسویه دوره‌ای حقوق ثابت + کمیسیون مشاوران در فیش حقوقی",
    ],
    metrics: [
      { label: "دقت محاسباتی", value: "اعشاری Decimal" },
      { label: "اسناد قطعی", value: "تغییرناپذیر" },
      { label: "مراکز هزینه", value: "به تفکیک شعبه" },
    ],
  },
  {
    id: "CUSTOMER",
    label: "مشتری و متقاضی",
    title: "پورتال شفاف جستجوی ملک، پیگیری بازدید و ثبت درخواست",
    summary:
      "جستجوی پیشرفته در فایل‌های تأییدشده، ذخیره جستجوهای موردعلاقه، مشاهده زمان بازدیدهای تاییدشده و ثبت تیکت یا شکایت با کد رهگیری.",
    phone: "09124444444",
    image: "/images/modern-villa-facade.jpg",
    imageCaption: "پورتال امن متقاضیان با حریم خصوصی مالکین",
    highlights: [
      "جستجوی پیشرفته بر اساس محله، متراژ، تعداد خواب و بودجه",
      "نمایش قیمت کل و قیمت هر مترمربع به تومان یا ریال",
      "پیگیری وضعیت بازدیدهای رزروشده و پاسخ تیکت‌های پشتیبانی",
      "مشارکت در نظرسنجی کیفیت خدمات پس از بازدید",
    ],
    metrics: [
      { label: "حریم خصوصی مالک", value: "حفظ آدرس دقیق" },
      { label: "اصالت فایل‌ها", value: "تأییدشده توسط مدیر" },
      { label: "کد رهگیری", value: "پیگیری آنلاین" },
    ],
  },
];

export function RoleWorkspaceShowcase() {
  const [activeId, setActiveId] = useState<string>(ROLE_SPECS[1].id);
  const current = ROLE_SPECS.find((r) => r.id === activeId) ?? ROLE_SPECS[0];

  return (
    <section className="border-y border-slate-200 bg-white py-16 dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-bold tracking-wide text-teal-700 dark:text-teal-400">
              ۰۲. معماری مبتنی بر نقش (RBAC)
            </p>
            <h2
              className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100 sm:text-3xl"
              style={{ textWrap: "balance" }}
            >
              یک زیرساخت یکپارچه؛ میز کار متمایز برای هر نقش سازمانی
            </h2>
          </div>
          <p className="max-w-md text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            منوها، عملیات مجاز و دسترسی به اطلاعات هویتی و مالی در لایه ORM بک‌اند و رابط کاربری
            بر اساس نقش واقعی هر کاربر تنظیم می‌شود.
          </p>
        </div>

        {/* Role Selector Tabs */}
        <div className="mb-8 flex flex-wrap gap-2 border-b border-slate-200 pb-4 dark:border-slate-800">
          {ROLE_SPECS.map((role) => {
            const active = role.id === current.id;
            return (
              <button
                key={role.id}
                type="button"
                onClick={() => setActiveId(role.id)}
                className={`rounded-lg border px-4 py-2 text-xs font-semibold transition-colors ${
                  active
                    ? "border-teal-700 bg-teal-700 text-white dark:border-teal-500 dark:bg-teal-600"
                    : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                {role.label}
              </button>
            );
          })}
        </div>

        {/* Split Showcase */}
        <div className="grid grid-cols-1 items-stretch gap-8 lg:grid-cols-12">
          <div className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-950/70 sm:p-8 lg:col-span-7">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-teal-700 dark:text-teal-400">
                  {current.label}
                </span>
                <span className="font-mono text-xs text-slate-500 dark:text-slate-400" dir="ltr">
                  {current.phone}
                </span>
              </div>

              <h3 className="mt-2 text-xl font-bold text-slate-900 dark:text-slate-100">
                {current.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                {current.summary}
              </p>

              <ul className="mt-6 space-y-3 border-t border-slate-200 pt-5 dark:border-slate-800">
                {current.highlights.map((h) => (
                  <li
                    key={h}
                    className="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300"
                  >
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-teal-700 dark:text-teal-400" />
                    <span>{h}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-8 flex flex-col justify-between gap-4 border-t border-slate-200 pt-5 dark:border-slate-800 sm:flex-row sm:items-center">
              <div className="grid grid-cols-3 gap-4">
                {current.metrics.map((m) => (
                  <div key={m.label}>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">{m.label}</div>
                    <div className="mt-0.5 text-xs font-bold text-slate-900 dark:text-slate-100">
                      {m.value}
                    </div>
                  </div>
                ))}
              </div>

              <Link
                href="/login"
                className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-teal-700 px-5 text-xs font-semibold text-white transition-colors hover:bg-teal-800 dark:bg-teal-600 dark:hover:bg-teal-500"
              >
                تجربه زنده این نقش
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-800 lg:col-span-5">
            <div className="relative h-full min-h-[300px]">
              <img
                src={current.image}
                alt={current.imageCaption}
                className="h-full w-full object-cover"
              />
              <div className="absolute inset-x-0 bottom-0 border-t border-white/15 bg-slate-950/75 px-4 py-3 text-xs text-slate-100 backdrop-blur-xs">
                {current.imageCaption}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
