// Path: frontend/src/app/page.tsx

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpen,
  Building2,
  Check,
  FileSpreadsheet,
  Globe2,
  Landmark,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import type { PublicSearchProperty } from "@/lib/types";
import { formatMoney, formatNumberFa } from "@/lib/formatters";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { HorizontalBarChart } from "@/components/ui/AnalyticsCharts";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { JsonLd } from "@/components/seo/JsonLd";
import { buildOrganizationJsonLd } from "@/lib/seo";
import { RoleWorkspaceShowcase } from "@/components/landing/RoleWorkspaceShowcase";
import { CommissionCalculatorPreview } from "@/components/landing/CommissionCalculatorPreview";

interface PriceTrendRow {
  district: string;
  listing_count: number;
  avg_price_per_sqm: string;
}

interface PublicArticleSummary {
  id: string;
  slug: string;
  title: string;
  summary: string;
  cover_image_url: string;
  published_at: string | null;
  reading_time_minutes: number;
  category: { name: string; slug: string } | null;
}

interface SubscriptionPlanRow {
  id: string;
  code: string;
  name_fa: string;
  monthly_price: string;
  annual_price: string;
  max_agents: number;
  max_branches: number;
  max_active_listings: number;
  features: Record<string, boolean>;
}

const ARCHITECTURE_PILLARS = [
  {
    num: "۰۱.",
    icon: ShieldCheck,
    title: "ایزوله‌سازی چندآژانسی و ۱۰ سیاست دسترسی",
    body: "هر آژانس به صورت مستقل با سیاست‌های جداگانه برای رؤیت مالک، ویرایش ملک، مذاکرات، قراردادها و گزارش عملکرد مشاوران مدیریت می‌شود.",
  },
  {
    num: "۰۲.",
    icon: Users,
    title: "پایپ‌لاین ۱۲مرحله‌ای CRM و تطبیق هوشمند",
    body: "مشتریان خریدار و مالک، سرنخ‌ها و نیازهای بودجه‌ای بدون نشت اطلاعات با سایر مشاوران هم‌تراز و با امتیاز تطبیق رتبه‌بندی می‌شوند.",
  },
  {
    num: "۰۳.",
    icon: Landmark,
    title: "حسابداری دوبل و خزانه‌داری چک",
    body: "کدینگ حساب‌ها، کنترل اجباری توازن بدهکار و بستانکار، سند معکوس تغییرناپذیر و پیگیری دقیق سررسید چک‌های دریافتنی و پرداختنی.",
  },
  {
    num: "۰۴.",
    icon: FileSpreadsheet,
    title: "مذاکره نسخه‌دار و قراردادهای استاندارد",
    body: "تاریخچه کامل پیشنهادها و ردوبدل قیمت‌ها، قراردادهای تاییدشده مدیر، ثبت طرفین و بستن قطعی معامله با اتصال مستقیم به کمیسیون.",
  },
  {
    num: "۰۵.",
    icon: Sparkles,
    title: "پشتیبانی SLA، شکایات محرمانه و نظرسنجی NPS",
    body: "تیکتینگ درون‌سازمانی و پلتفرمی، پیگیری عمومی درخواست‌ها و شکایات با کد رهگیری و فرم‌های خودکار سنجش رضایت پس از بازدید.",
  },
  {
    num: "۰۶.",
    icon: Globe2,
    title: "چندارزی، چندزبانه و تقویم شمسی / میلادی",
    body: "پشتیبانی یکپارچه از تومان، ریال، دلار، یورو و درهم همراه با تبدیل خودکار در نمایش و تاریخ‌های دقیق جلالی و میلادی.",
  },
];

export default function HomePage() {
  const [city, setCity] = useState("تهران");
  const [district, setDistrict] = useState("");
  const [dealType, setDealType] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [q, setQ] = useState("");

  const [appliedFilters, setAppliedFilters] = useState({
    city: "تهران",
    district: "",
    dealType: "",
    propertyType: "",
    q: "",
  });

  const {
    data: properties = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["public-search-properties", appliedFilters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (appliedFilters.city) params.set("city", appliedFilters.city);
      if (appliedFilters.district) params.set("district", appliedFilters.district);
      if (appliedFilters.dealType) params.set("deal_type", appliedFilters.dealType);
      if (appliedFilters.propertyType) params.set("property_type", appliedFilters.propertyType);
      if (appliedFilters.q) params.set("q", appliedFilters.q);
      const env = await apiFetch<PublicSearchProperty[]>(
        `/api/v1/search/properties?${params.toString()}`
      );
      return Array.isArray(env.data) ? env.data : [];
    },
  });

  const { data: trends = [] } = useQuery({
    queryKey: ["public-price-trends", appliedFilters.city],
    queryFn: async () => {
      const env = await apiFetch<PriceTrendRow[]>(
        `/api/v1/matching/analytics/price-trends?city=${encodeURIComponent(
          appliedFilters.city || "تهران"
        )}`
      );
      return Array.isArray(env.data) ? env.data : [];
    },
  });

  const { data: articles = [] } = useQuery({
    queryKey: ["public-home-articles"],
    queryFn: async () => {
      const env = await apiFetch<PublicArticleSummary[]>(
        "/api/v1/cms/public/articles?page_size=3"
      );
      return Array.isArray(env.data) ? env.data : [];
    },
  });

  const { data: plans = [] } = useQuery({
    queryKey: ["public-home-plans"],
    queryFn: async () => {
      const env = await apiFetch<SubscriptionPlanRow[]>("/api/v1/subscriptions/plans");
      return Array.isArray(env.data) ? env.data : [];
    },
  });

  const safeProperties = Array.isArray(properties) ? properties : [];
  const safeTrends = Array.isArray(trends) ? trends : [];
  const safeArticles = Array.isArray(articles) ? articles : [];
  const safePlans = Array.isArray(plans) ? plans : [];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedFilters({ city, district, dealType, propertyType, q });
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <JsonLd data={buildOrganizationJsonLd()} />
      <PublicHeader />

      {/* Section 1: Architectural Hero Split + Quantified 4-Metric Strip */}
      <section className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto max-w-7xl px-4 pt-10 pb-12 sm:px-6 lg:px-8 lg:pt-14 lg:pb-14">
          <div className="grid grid-cols-1 items-stretch gap-10 lg:grid-cols-12">
            <div className="flex flex-col justify-center space-y-5 lg:col-span-6">
              <p className="text-xs font-bold tracking-wide text-teal-700 dark:text-teal-400">
                زیرساخت یکپارچه چندآژانسی املاک، CRM و مالی
              </p>
              <h1
                className="text-3xl font-extrabold leading-[1.25] tracking-tight text-slate-900 dark:text-slate-50 sm:text-4xl lg:text-[44px]"
                style={{ textWrap: "balance" }}
              >
                پلتفرم جامع مدیریت املاک، قراردادها و حسابداری آژانس‌های پیشرو
              </h1>
              <p className="max-w-xl text-base leading-relaxed text-slate-600 dark:text-slate-300">
                بنیان ملک، جستجوی شفاف فایل‌های احراز‌شده برای متقاضیان را با یک میز کار سازمانی
                کامل شامل پایپ‌لاین ۱۲مرحله‌ای CRM، تقسیم دقیق کمیسیون و دفتر کل حسابداری دوطرفه
                ترکیب می‌کند.
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <a
                  href="#listings"
                  className="inline-flex h-11 items-center gap-2 rounded-lg bg-teal-700 px-6 text-sm font-semibold text-white transition-colors hover:bg-teal-800 dark:bg-teal-600 dark:hover:bg-teal-500"
                >
                  جستجو در فایل‌های تأییدشده
                  <ArrowLeft className="h-4 w-4" />
                </a>
                <Link
                  href="/login"
                  className="inline-flex h-11 items-center rounded-lg border border-slate-300 bg-white px-5 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
                >
                  ورود با ۷ حساب کاربری دمو
                </Link>
              </div>
            </div>

            <div className="lg:col-span-6">
              <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 shadow-sm dark:border-slate-800 dark:bg-slate-800">
                <img
                  src="/images/hero-penthouse-tehran.jpg"
                  alt="پنت‌هاوس لوکس مشرف به شمال تهران — بنیان ملک"
                  className="aspect-[16/9] w-full object-cover"
                />
                <div className="flex items-center justify-between border-t border-slate-200 bg-white px-4 py-2.5 text-xs dark:border-slate-800 dark:bg-slate-950/90">
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    زعفرانیه · پنت‌هاوس ۱۸۵ متری نوساز با تراس پانوراما
                  </span>
                  <span className="font-mono text-teal-700 dark:text-teal-400">PN-1001</span>
                </div>
              </div>
            </div>
          </div>

          {/* 4-Column Quantified Metrics Strip */}
          <div className="mt-10 grid grid-cols-2 divide-y divide-slate-200 rounded-xl border border-slate-200 bg-slate-50 dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-950/60 lg:grid-cols-4 lg:divide-x lg:divide-x-reverse lg:divide-y-0">
            <div className="p-4 sm:p-5">
              <div className="tabular-nums text-2xl font-extrabold text-teal-800 dark:text-teal-400">
                {formatNumberFa(29)} ماژول
              </div>
              <div className="mt-1 text-xs font-medium text-slate-600 dark:text-slate-400">
                معماری یکپارچه از ثبت فایل تا حقوق و ترازنامه
              </div>
            </div>
            <div className="p-4 sm:p-5">
              <div className="tabular-nums text-2xl font-extrabold text-slate-900 dark:text-slate-100">
                {formatNumberFa(12)} مرحله
              </div>
              <div className="mt-1 text-xs font-medium text-slate-600 dark:text-slate-400">
                پایپ‌لاین اختصاصی CRM، مذاکره و تطبیق خریدار
              </div>
            </div>
            <div className="p-4 sm:p-5">
              <div className="tabular-nums text-2xl font-extrabold text-slate-900 dark:text-slate-100">
                {formatNumberFa(7)} نقش RBAC
              </div>
              <div className="mt-1 text-xs font-medium text-slate-600 dark:text-slate-400">
                مدیر کل، مدیر آژانس، مدیر شعبه، مشاور، حسابدار و مشتری
              </div>
            </div>
            <div className="p-4 sm:p-5">
              <div className="tabular-nums text-2xl font-extrabold text-amber-700 dark:text-amber-400">
                {formatNumberFa(100)}٪ متوازن
              </div>
              <div className="mt-1 text-xs font-medium text-slate-600 dark:text-slate-400">
                حسابداری دوطرفه Decimal با چک و مرکز هزینه
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Live Portal Search & Curated Verified Listings */}
      <section id="listings" className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="mb-6">
          <p className="text-xs font-bold tracking-wide text-teal-700 dark:text-teal-400">
            ۰۱. پورتال عمومی فایل‌های تأییدشده
          </p>
          <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              جستجوی زنده در بانک املاک احراز‌شده
            </h2>
            <span className="tabular-nums text-xs font-semibold text-slate-600 dark:text-slate-300">
              {formatNumberFa(safeProperties.length)} ملک فعال در پورتال
            </span>
          </div>
        </div>

        <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <form onSubmit={handleSearch} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="عنوان، محله یا کلیدواژه..."
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 lg:col-span-2"
            />
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="شهر (مثال: تهران)"
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
            <input
              type="text"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              placeholder="منطقه (مثال: زعفرانیه)"
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
            <select
              value={dealType}
              onChange={(e) => setDealType(e.target.value)}
              aria-label="نوع معامله"
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            >
              <option value="">همه معاملات</option>
              <option value="SALE">فروش</option>
              <option value="MORTGAGE_RENT">رهن و اجاره</option>
            </select>
            <button
              type="submit"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white transition-colors hover:bg-teal-800 dark:bg-teal-600 dark:hover:bg-teal-500"
            >
              <Search className="h-4 w-4" />
              جستجو
            </button>
          </form>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              {[
                { code: "", label: "همه کاربری‌ها" },
                { code: "APARTMENT", label: "آپارتمان" },
                { code: "VILLA", label: "ویلا" },
                { code: "OFFICE", label: "اداری و تجاری" },
                { code: "LAND", label: "زمین" },
              ].map((item) => (
                <button
                  key={item.code || "ALL"}
                  type="button"
                  onClick={() => {
                    setPropertyType(item.code);
                    setAppliedFilters((prev) => ({ ...prev, propertyType: item.code }));
                  }}
                  className={`rounded-lg border px-3 py-1 text-xs font-medium transition-colors ${
                    propertyType === item.code
                      ? "border-teal-700 bg-teal-700 text-white dark:border-teal-500 dark:bg-teal-600"
                      : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <Link
              href="/search"
              className="text-xs font-semibold text-teal-700 hover:underline dark:text-teal-400"
            >
              فیلترهای پیشرفته و تطبیق هوشمند ←
            </Link>
          </div>
        </div>

        {isLoading ? (
          <LoadingState message="در حال جستجو در بانک املاک..." />
        ) : error ? (
          <ErrorState
            message={error instanceof Error ? error.message : "خطا در دریافت املاک"}
            onRetry={() => refetch()}
          />
        ) : safeProperties.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
            ملکی با فیلترهای انتخابی یافت نشد. شهر یا منطقه را تغییر دهید و دوباره جستجو کنید.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {safeProperties.map((p, idx) => (
              <PropertyCard key={p.id} property={p} index={idx} />
            ))}
          </div>
        )}

        <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
          * مطابق سیاست حریم خصوصی بنیان ملک، پلاک دقیق و شماره تماس مالکین تا زمان هماهنگی بازدید
          توسط مشاور مسئول پنهان می‌ماند.
        </p>
      </section>

      {/* Section 3: Interactive 7-Role Workspace Switcher */}
      <RoleWorkspaceShowcase />

      {/* Section 4: Numbered Architecture Bento Grid */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mb-8">
          <p className="text-xs font-bold tracking-wide text-teal-700 dark:text-teal-400">
            ۰۳. قابلیت‌های هسته سازمانی
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100 sm:text-3xl">
            مهندسی‌شده برای آژانس‌های املاک در حال رشد
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {ARCHITECTURE_PILLARS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.num}
                className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-6 transition-colors hover:border-teal-600/60 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-teal-500/60"
              >
                <div>
                  <div className="mb-4 flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-teal-700 dark:text-teal-400">
                      {item.num}
                    </span>
                    <Icon className="h-5 w-5 text-slate-400 dark:text-slate-500" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    {item.body}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Section 5: Interactive Double-Entry Commission Calculator */}
      <div className="border-t border-slate-200 bg-slate-100/60 dark:border-slate-800 dark:bg-slate-900/40">
        <CommissionCalculatorPreview />
      </div>

      {/* Section 6: Market Price Trends & Live CMS Magazine Highlights */}
      <section
        id="market-trends"
        className="border-t border-slate-200 bg-white py-16 dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-4 sm:px-6 lg:grid-cols-12 lg:px-8">
          <div className="lg:col-span-6">
            <HorizontalBarChart
              title="شاخص میانگین قیمت هر مترمربع در مناطق"
              subtitle={`داده‌های زنده تحلیلی برای شهر ${appliedFilters.city || "تهران"} (تومان)`}
              items={safeTrends.slice(0, 6).map((t) => ({
                label: t.district,
                value: Number(t.avg_price_per_sqm || 0),
                secondary: `${formatNumberFa(t.listing_count)} فایل`,
              }))}
              unitLabel="تومان"
            />
          </div>

          <div className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-950/60 lg:col-span-6">
            <div>
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    تازه‌ترین گزارش‌ها و مقالات تخصصی
                  </h3>
                </div>
                <Link
                  href="/blog"
                  className="text-xs font-semibold text-teal-700 hover:underline dark:text-teal-400"
                >
                  مشاهده مجله ←
                </Link>
              </div>

              {safeArticles.length === 0 ? (
                <p className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">
                  در حال بارگذاری مقالات تحلیلی بازار مسکن...
                </p>
              ) : (
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                  {safeArticles.map((art) => (
                    <Link
                      key={art.id}
                      href={`/blog/${art.slug}`}
                      className="group block py-3.5 first:pt-0 last:pb-0"
                    >
                      <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                        <span className="font-semibold text-teal-700 dark:text-teal-400">
                          {art.category?.name || "تحلیل بازار"} · {formatNumberFa(art.reading_time_minutes || 4)} دقیقه مطالعه
                        </span>
                        {art.published_at && <DateDisplay value={art.published_at} />}
                      </div>
                      <h4 className="mt-1 line-clamp-1 text-sm font-bold text-slate-900 transition-colors group-hover:text-teal-700 dark:text-slate-100 dark:group-hover:text-teal-400">
                        {art.title}
                      </h4>
                      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                        {art.summary}
                      </p>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Section 7: Live Subscription Tier Comparison & Agency Onboarding CTA */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold tracking-wide text-teal-700 dark:text-teal-400">
              ۰۵. پلن‌های اشتراک سازمانی
            </p>
            <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
              مقیاس‌پذیر برای یک دفتر محلی تا هلدینگ چندشعبه‌ای
            </h2>
          </div>
          <Link
            href="/pricing"
            className="text-xs font-semibold text-teal-700 hover:underline dark:text-teal-400"
          >
            مقایسه کامل تعرفه‌ها ←
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {safePlans.map((plan) => {
            const isPro = plan.code === "PRO";
            return (
              <div
                key={plan.id}
                className={`flex flex-col justify-between rounded-2xl border p-6 ${
                  isPro
                    ? "border-teal-700 bg-white shadow-sm dark:border-teal-500 dark:bg-slate-900"
                    : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                      {plan.name_fa}
                    </h3>
                    {isPro && (
                      <span className="text-xs font-bold text-teal-700 dark:text-teal-400">
                        پیشنهاد ویژه
                      </span>
                    )}
                  </div>
                  <div className="mt-4 flex items-baseline gap-1.5">
                    <span className="tabular-nums text-2xl font-extrabold text-slate-900 dark:text-slate-50">
                      {formatMoney(plan.monthly_price, "IRT", "IRT")}
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">/ ماهانه</span>
                  </div>

                  <ul className="mt-6 space-y-2.5 border-t border-slate-100 pt-4 text-xs text-slate-700 dark:border-slate-800 dark:text-slate-300">
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      تا {formatNumberFa(plan.max_agents)} مشاور فعال
                    </li>
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      تا {formatNumberFa(plan.max_branches)} شعبه هم‌زمان
                    </li>
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      تا {formatNumberFa(plan.max_active_listings)} فایل ملکی فعال
                    </li>
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      پایپ‌لاین CRM و پورتال عمومی اختصاصی
                    </li>
                  </ul>
                </div>

                <Link
                  href="/agency-application"
                  className={`mt-6 inline-flex h-10 items-center justify-center rounded-lg text-xs font-semibold transition-colors ${
                    isPro
                      ? "bg-teal-700 text-white hover:bg-teal-800 dark:bg-teal-600 dark:hover:bg-teal-500"
                      : "border border-slate-300 bg-slate-50 text-slate-800 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                  }`}
                >
                  درخواست راه‌اندازی آژانس
                </Link>
              </div>
            );
          })}
        </div>

        {/* Closing Agency Onboarding CTA Band */}
        <div className="mt-12 flex flex-col justify-between gap-6 rounded-2xl border border-slate-200 bg-slate-900 p-8 text-white dark:border-slate-700 dark:bg-slate-900 sm:flex-row sm:items-center">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-teal-400">
              <Building2 className="h-4 w-4" />
              شروع همکاری سازمانی آژانس‌ها
            </div>
            <h3 className="text-xl font-bold sm:text-2xl">
              آماده تحول دیجیتال در آژانس املاک خود هستید؟
            </h3>
            <p className="max-w-2xl text-xs leading-relaxed text-slate-300 sm:text-sm">
              همین الان با هر یک از ۷ نقش مدیریتی و عملیاتی وارد محیط زنده پلتفرم شوید یا درخواست
              راه‌اندازی پنل اختصاصی آژانس خود را ثبت کنید.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-3">
            <Link
              href="/login"
              className="inline-flex h-11 items-center gap-2 rounded-lg bg-teal-600 px-5 text-xs font-semibold text-white transition-colors hover:bg-teal-500 sm:text-sm"
            >
              ورود فوری با ۷ نقش
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <Link
              href="/agency-application"
              className="inline-flex h-11 items-center rounded-lg border border-slate-600 bg-transparent px-5 text-xs font-semibold text-slate-100 transition-colors hover:bg-slate-800 sm:text-sm"
            >
              ثبت درخواست همکاری
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
