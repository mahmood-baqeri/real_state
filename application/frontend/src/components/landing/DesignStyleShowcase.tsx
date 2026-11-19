"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  Building2,
  Eye,
  Layers,
  MapPin,
  Sparkles,
  Sun,
} from "lucide-react";
import { formatMoney, formatNumberFa } from "@/lib/formatters";
import type { PublicSearchProperty } from "@/lib/types";

type StyleKey = "cinematic_dark" | "luxury_light" | "visual_portal" | "analytics_bi";

const STYLE_PRESETS: {
  key: StyleKey;
  title: string;
  subtitle: string;
  badge: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  {
    key: "cinematic_dark",
    title: "سبک ۱: دارک سینماتیک",
    subtitle: "کنتراست عمیق با تایپوگرافی معماری برای معرفی فایل‌های شاخص و لوکس",
    badge: "Cinematic Dark",
    icon: Sparkles,
  },
  {
    key: "luxury_light",
    title: "سبک ۲: روشن معماری",
    subtitle: "پالت روشن، حاشیه‌های دقیق و خوانایی بالا برای جستجوی روزمره متقاضیان",
    badge: "Luxury Light",
    icon: Sun,
  },
  {
    key: "visual_portal",
    title: "سبک ۳: ویترین تصویری املاک",
    subtitle: "چیدمان گالری‌محور با تمرکز بر تصویر، مشخصات فنی و مقایسه سریع فایل‌ها",
    badge: "Visual Gallery",
    icon: Eye,
  },
  {
    key: "analytics_bi",
    title: "سبک ۴: داشبورد تحلیلی BI",
    subtitle: "گزارش‌های مدیریتی، قیف فروش ۱۲مرحله‌ای و شاخص قیمت مناطق در لحظه",
    badge: "Executive BI",
    icon: BarChart3,
  },
];

export function DesignStyleShowcase({
  featuredProperties = [],
}: {
  featuredProperties?: PublicSearchProperty[];
}) {
  const [active, setActive] = useState<StyleKey>("cinematic_dark");
  const sample = featuredProperties[0];
  const sampleList = featuredProperties.slice(0, 3);

  return (
    <section
      id="design-showcase"
      className="border-t border-slate-200 bg-white py-16 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold tracking-wide text-teal-700 dark:text-teal-400">
              ۰۴. ویترین چهار سبک طراحی پلتفرم
            </p>
            <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100 sm:text-3xl">
              تجربه بصری هماهنگ در پورتال عمومی تا اتاق فرمان مدیریتی
            </h2>
          </div>
          <p className="max-w-md text-xs leading-relaxed text-slate-600 dark:text-slate-400">
            تمامی صفحات بنیان ملک در دو حالت روشن و تاریک و با استاندارد تایپوگرافی عددی یکپارچه
            طراحی شده‌اند. هر سبک را به صورت زنده پیش‌نمایش کنید:
          </p>
        </div>

        {/* Style Selector Tabs */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STYLE_PRESETS.map((preset) => {
            const Icon = preset.icon;
            const isActive = active === preset.key;
            return (
              <button
                key={preset.key}
                type="button"
                onClick={() => setActive(preset.key)}
                className={`flex flex-col items-start rounded-xl border p-4 text-right transition-all ${
                  isActive
                    ? "border-teal-700 bg-teal-50/70 shadow-sm dark:border-teal-500 dark:bg-teal-950/40"
                    : "border-slate-200 bg-slate-50/60 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950/60 dark:hover:border-slate-700"
                }`}
              >
                <div className="mb-2 flex w-full items-center justify-between">
                  <Icon
                    className={`h-4 w-4 ${
                      isActive ? "text-teal-700 dark:text-teal-400" : "text-slate-400"
                    }`}
                  />
                  <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    {preset.badge}
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {preset.title}
                </div>
                <div className="mt-1 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
                  {preset.subtitle}
                </div>
              </button>
            );
          })}
        </div>

        {/* Live Interactive Style Preview Stage */}
        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800">
          {active === "cinematic_dark" && (
            <div className="grid grid-cols-1 bg-slate-950 text-slate-100 lg:grid-cols-12">
              <div className="flex flex-col justify-between p-7 sm:p-9 lg:col-span-6">
                <div className="space-y-4">
                  <span className="inline-flex items-center gap-1.5 text-xs font-bold tracking-wide text-amber-400">
                    <Sparkles className="h-3.5 w-3.5" />
                    کلکسیون منتخب پنت‌هاوس و املاک خاص
                  </span>
                  <h3 className="text-2xl font-extrabold leading-snug text-white sm:text-3xl">
                    {sample?.title || "پنت‌هاوس مدرن زعفرانیه با تراس پانوراما و دید مشرف"}
                  </h3>
                  <p className="text-xs leading-relaxed text-slate-300 sm:text-sm">
                    نمایش با کنتراست سینماتیک تیره برای پرونده‌های ممتاز و ارائه اختصاصی به
                    خریدارهای VIP همراه با گالری تمام‌صفحه و حریم خصوصی کامل مالک.
                  </p>
                </div>
                <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-slate-800 pt-5">
                  <div>
                    <div className="text-[11px] text-slate-400">ارزش پیشنهادی فایل شاخص</div>
                    <div className="mt-1 tabular-nums text-lg font-extrabold text-teal-400">
                      {sample
                        ? formatMoney(sample.total_price, sample.currency_id, sample.currency_id)
                        : "۷۵٬۰۰۰٬۰۰۰٬۰۰۰ تومان"}
                    </div>
                  </div>
                  <Link
                    href={sample ? `/properties/${sample.id}` : "/search"}
                    className="inline-flex h-10 items-center gap-2 rounded-lg bg-teal-600 px-4 text-xs font-semibold text-white hover:bg-teal-500"
                  >
                    مشاهده جزئیات ملک
                    <ArrowLeft className="h-4 w-4" />
                  </Link>
                </div>
              </div>
              <div className="relative min-h-[260px] lg:col-span-6">
                <img
                  src={sample?.cover_url || "/images/hero-penthouse-tehran.jpg"}
                  alt={sample?.title || "پنت‌هاوس زعفرانیه"}
                  referrerPolicy="no-referrer"
                  className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/70 via-transparent to-transparent" />
              </div>
            </div>
          )}

          {active === "luxury_light" && (
            <div className="grid grid-cols-1 bg-[#faf9f6] p-7 text-slate-900 sm:p-9 lg:grid-cols-12 lg:gap-8">
              <div className="space-y-4 lg:col-span-7">
                <div className="text-xs font-bold text-teal-800">معماری روشن و شفافیت اطلاعات</div>
                <h3 className="text-2xl font-extrabold text-slate-900">
                  کارت اطلاعات مهندسی‌شده بدون شلوغی بصری
                </h3>
                <p className="text-xs leading-relaxed text-slate-600 sm:text-sm">
                  تفکیک دقیق داده‌های کلیدی از متراژ، موقعیت منطقه، وضعیت سند و شرایط مالی با
                  صفحه‌بندی تایپوگرافیک روشن و سلسله‌مراتب واضح.
                </p>
                <div className="grid grid-cols-3 gap-3 pt-2">
                  <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                    <div className="text-[11px] text-slate-500">قیمت کل تاییدشده</div>
                    <div className="mt-1 tabular-nums text-sm font-bold text-teal-800">
                      {sample
                        ? formatMoney(sample.total_price, sample.currency_id, sample.currency_id)
                        : "۲۴٬۵۰۰٬۰۰۰٬۰۰۰ تومان"}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                    <div className="text-[11px] text-slate-500">زیربنای مفید</div>
                    <div className="mt-1 tabular-nums text-sm font-bold text-slate-900">
                      {sample ? `${formatNumberFa(sample.built_area_sqm)} متر` : "۱۸۵ متر"}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                    <div className="text-[11px] text-slate-500">محدوده و شهر</div>
                    <div className="mt-1 text-sm font-bold text-slate-900">
                      {sample ? `${sample.city}، ${sample.district}` : "تهران، زعفرانیه"}
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-6 flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 lg:col-span-5 lg:mt-0">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3 text-xs">
                  <span className="font-bold text-slate-800">سند و اصالت فایل</span>
                  <span className="font-mono text-teal-700">
                    {sample?.property_code || "PN-1001"}
                  </span>
                </div>
                <div className="my-4 space-y-2 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <span>آژانس کارگزار:</span>
                    <span className="font-semibold text-slate-900">
                      {sample?.agency_name || "املاک پارس نگین"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>تعداد خواب:</span>
                    <span className="tabular-nums font-semibold text-slate-900">
                      {formatNumberFa(sample?.bedrooms ?? 3)} خواب
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>نوع معامله:</span>
                    <span className="font-semibold text-slate-900">
                      {sample?.deal_type_name || "فروش نقدی"}
                    </span>
                  </div>
                </div>
                <Link
                  href="/search"
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-300 bg-slate-50 text-xs font-semibold text-slate-800 hover:bg-slate-100"
                >
                  باز کردن جستجوی پیشرفته
                </Link>
              </div>
            </div>
          )}

          {active === "visual_portal" && (
            <div className="bg-slate-50 p-7 dark:bg-slate-950 sm:p-9">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-200">
                  <Layers className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  نمای چندستونه گالری و مقایسه هم‌زمان
                </div>
                <Link
                  href="/search"
                  className="text-xs font-semibold text-teal-700 hover:underline dark:text-teal-400"
                >
                  مشاهده نقشه و فیلترها ←
                </Link>
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {(sampleList.length > 0
                  ? sampleList
                  : [
                      {
                        id: "preview-1",
                        title: "آپارتمان لوکس فرشته",
                        city: "تهران",
                        district: "فرشته",
                        built_area_sqm: "220",
                        total_price: "52000000000",
                        currency_id: "IRT" as const,
                        cover_url: "/images/prop-fereshteh.jpg",
                      },
                      {
                        id: "preview-2",
                        title: "برج باغ مدرن زعفرانیه",
                        city: "تهران",
                        district: "زعفرانیه",
                        built_area_sqm: "310",
                        total_price: "85000000000",
                        currency_id: "IRT" as const,
                        cover_url: "/images/prop-zafaranieh.jpg",
                      },
                      {
                        id: "preview-3",
                        title: "واحد اداری مدرن جردن",
                        city: "تهران",
                        district: "جردن",
                        built_area_sqm: "145",
                        total_price: "34000000000",
                        currency_id: "IRT" as const,
                        cover_url: "/images/prop-office.jpg",
                      },
                    ]
                ).map((item, idx) => (
                  <div
                    key={item.id}
                    className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
                  >
                    <img
                      src={
                        item.cover_url ||
                        ["/images/prop-zafaranieh.jpg", "/images/prop-fereshteh.jpg", "/images/prop-office.jpg"][
                          idx % 3
                        ]
                      }
                      alt={item.title}
                      referrerPolicy="no-referrer"
                      className="aspect-[16/10] w-full object-cover"
                    />
                    <div className="p-4">
                      <div className="line-clamp-1 text-sm font-bold text-slate-900 dark:text-slate-100">
                        {item.title}
                      </div>
                      <div className="mt-1 flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                        <MapPin className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                        {item.city}، {item.district} · {formatNumberFa(item.built_area_sqm)} متر
                      </div>
                      <div className="mt-3 tabular-nums text-xs font-bold text-teal-800 dark:text-teal-300">
                        {formatMoney(item.total_price, item.currency_id, item.currency_id)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {active === "analytics_bi" && (
            <div className="bg-slate-900 p-7 text-slate-100 sm:p-9">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-xs font-bold text-teal-400">
                  <Building2 className="h-4 w-4" />
                  داشبورد مدیریتی و گزارش‌ساز هوشمند آژانس
                </div>
                <Link
                  href="/login"
                  className="text-xs font-semibold text-amber-400 hover:underline"
                >
                  ورود به پنل تحلیلی ←
                </Link>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                {[
                  { label: "فایل‌های فعال شبکه", val: `${formatNumberFa(featuredProperties.length || 8)} فایل` },
                  { label: "مراحل پایپ‌لاین CRM", val: `${formatNumberFa(12)} مرحله` },
                  { label: "تراز دفتر کل حسابداری", val: `${formatNumberFa(100)}٪ متوازن` },
                  { label: "گزارش خروجی اکسل/CSV", val: "لحظه‌ای" },
                ].map((kpi) => (
                  <div
                    key={kpi.label}
                    className="rounded-xl border border-slate-800 bg-slate-950/70 p-4"
                  >
                    <div className="text-[11px] text-slate-400">{kpi.label}</div>
                    <div className="mt-1.5 tabular-nums text-base font-extrabold text-white">
                      {kpi.val}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
