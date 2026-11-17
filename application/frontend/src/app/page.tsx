"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Building2, CheckCircle2, Landmark, Search, ShieldCheck, Users } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import type { PublicSearchProperty } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { HorizontalBarChart } from "@/components/ui/AnalyticsCharts";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

interface PriceTrendRow {
  district: string;
  listing_count: number;
  avg_price_per_sqm: string;
}

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
      return env.data;
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
      return env.data;
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedFilters({ city, district, dealType, propertyType, q });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <PublicHeader />

      {/* Editorial Hero Section */}
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-10 px-4 py-12 sm:px-6 lg:grid-cols-12 lg:px-8 lg:py-16">
          <div className="space-y-6 lg:col-span-6">
            <div className="inline-flex items-center gap-2 rounded-md border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">
              <ShieldCheck className="h-4 w-4" />
              زیرساخت یکپارچه چندآژانسی املاک و مالی
            </div>
            <h1 className="text-3xl font-bold leading-tight tracking-tight text-slate-900 sm:text-4xl lg:text-[42px]">
              مدیریت هوشمند املاک، قراردادها و حسابداری آژانس‌های پیشرو
            </h1>
            <p className="max-w-xl text-base leading-relaxed text-slate-600">
              پلتفرم بنیان ملک، جستجوی شفاف فایل‌های تأییدشده برای متقاضیان را با یک میز کار
              سازمانی کامل شامل پایپ‌لاین ۱۲مرحله‌ای CRM، محاسبه دقیق کمیسیون و حسابداری دوبل ترکیب می‌کند.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <a
                href="#listings"
                className="inline-flex h-11 items-center gap-2 rounded-lg bg-teal-700 px-6 text-sm font-semibold text-white hover:bg-teal-800 transition-colors"
              >
                جستجو در فایل‌های منتشرشده
                <ArrowLeft className="h-4 w-4" />
              </a>
              <Link
                href="/login"
                className="inline-flex h-11 items-center rounded-lg border border-slate-300 bg-white px-5 text-sm font-semibold text-slate-800 hover:bg-slate-50 transition-colors"
              >
                ورود به میز کار آژانس
              </Link>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 shadow-sm">
              <img
                src="/images/prop-zafaranieh.jpg"
                alt="نمای معماری املاک منتخب بنیان ملک"
                className="aspect-[16/9] w-full object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Search Bar & Property Listings */}
      <section id="listings" className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="mb-8 rounded-xl border border-slate-200 bg-white p-5">
          <form onSubmit={handleSearch} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="عنوان، محله یا کلیدواژه..."
              className="h-10 rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none lg:col-span-2"
            />
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="شهر (مثال: تهران)"
              className="h-10 rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
            <input
              type="text"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              placeholder="منطقه (مثال: زعفرانیه)"
              className="h-10 rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
            <select
              value={dealType}
              onChange={(e) => setDealType(e.target.value)}
              aria-label="نوع معامله"
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-teal-600 focus:outline-none"
            >
              <option value="">همه معاملات</option>
              <option value="SALE">فروش</option>
              <option value="MORTGAGE_RENT">رهن و اجاره</option>
            </select>
            <button
              type="submit"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800 transition-colors"
            >
              <Search className="h-4 w-4" />
              جستجو
            </button>
          </form>
          <div className="mt-3 flex flex-wrap items-center gap-2">
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
                    ? "border-teal-700 bg-teal-700 text-white"
                    : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900">فایل‌های تأییدشده پورتال</h2>
            <p className="mt-1 text-xs text-slate-500">
              نشانی دقیق مالکین تا زمان هماهنگی بازدید محفوظ می‌ماند.
            </p>
          </div>
          <span className="tabular-nums text-xs font-semibold text-slate-600">
            {properties.length} ملک یافت شد
          </span>
        </div>

        {isLoading ? (
          <LoadingState message="در حال جستجو در بانک املاک..." />
        ) : error ? (
          <ErrorState
            message={error instanceof Error ? error.message : "خطا در دریافت املاک"}
            onRetry={() => refetch()}
          />
        ) : properties.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-600">
            ملکی با فیلترهای انتخابی یافت نشد. شهر یا منطقه را تغییر دهید و دوباره جستجو کنید.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {properties.map((p, idx) => (
              <PropertyCard key={p.id} property={p} index={idx} />
            ))}
          </div>
        )}
      </section>

      {/* Market Trends & Enterprise Architecture Highlights */}
      <section id="market-trends" className="border-t border-slate-200 bg-white py-12">
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-4 sm:px-6 lg:grid-cols-12 lg:px-8">
          <div className="lg:col-span-6">
            <HorizontalBarChart
              title="شاخص میانگین قیمت هر مترمربع در مناطق"
              subtitle={`داده‌های زنده تحلیلی برای شهر ${appliedFilters.city || "تهران"} (تومان)`}
              items={trends.slice(0, 6).map((t) => ({
                label: t.district,
                value: Number(t.avg_price_per_sqm || 0),
                secondary: `${t.listing_count} فایل`,
              }))}
              unitLabel="تومان"
            />
          </div>

          <div id="capabilities" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:col-span-6">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
              <Building2 className="mb-3 h-5 w-5 text-teal-700" />
              <h3 className="text-sm font-bold text-slate-900">جداسازی کامل چندآژانسی</h3>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                ایزوله‌سازی داده‌های هر آژانس با ۱۰ سیاست دسترسی قابل تنظیم برای فایل‌ها، مشتریان و اطلاعات مالک.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
              <Users className="mb-3 h-5 w-5 text-teal-700" />
              <h3 className="text-sm font-bold text-slate-900">CRM و تطبیق هوشمند</h3>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                پایپ‌لاین ۱۲مرحله‌ای، پیگیری سرنخ‌ها، اشتراک‌گذاری خصوصی مشتری بین مشاوران و امتیازدهی تطبیق.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
              <Landmark className="mb-3 h-5 w-5 text-teal-700" />
              <h3 className="text-sm font-bold text-slate-900">حسابداری دوبل و خزانه‌داری</h3>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                کدینگ حساب‌ها، سند حسابداری متوازن با برگشت‌پذیری، مدیریت چک‌ها و محاسبه خودکار کمیسیون.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
              <CheckCircle2 className="mb-3 h-5 w-5 text-teal-700" />
              <h3 className="text-sm font-bold text-slate-900">تقویم شمسی و ریال/تومان</h3>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                نمایش شمسی و میلادی، تبدیل شفاف تومان و ریال (۱۰ ریال = ۱ تومان) و ساختار آماده بین‌المللی.
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-slate-50 py-8 text-center text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-4">
          پلتفرم سازمانی بنیان ملک — هسته Django ORM + لایه API با FastAPI + رابط کاربری Next.js
        </div>
      </footer>
    </div>
  );
}
