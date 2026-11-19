// Path: frontend/src/app/search/page.tsx

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { MapPin, Search, SlidersHorizontal } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import type { PublicSearchProperty } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { formatNumberFa } from "@/lib/formatters";

export default function AdvancedSearchPage() {
  const [filters, setFilters] = useState({
    q: "",
    city: "تهران",
    district: "",
    deal_type: "",
    property_type: "",
    min_price: "",
    max_price: "",
    min_area: "",
    min_bedrooms: "",
  });
  const [applied, setApplied] = useState(filters);

  const searchQ = useQuery({
    queryKey: ["advanced-public-search", applied],
    queryFn: async () => {
      const p = new URLSearchParams();
      Object.entries(applied).forEach(([k, v]) => {
        if (v) p.set(k, v);
      });
      return (await apiFetch<PublicSearchProperty[]>(`/api/v1/search/properties?${p.toString()}`)).data;
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setApplied(filters);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">جستجوی پیشرفته املاک</h1>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              فیلتر دقیق بر اساس شهر، محله، بودجه، متراژ و تعداد اتاق خواب در فایل‌های تاییدشده شبکه بنیان ملک
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <Link
              href="/explore/tehran/zafaranieh"
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-1.5 font-medium text-slate-700 dark:text-slate-300 hover:border-teal-600"
            >
              <MapPin className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
              زعفرانیه تهران
            </Link>
            <Link
              href="/explore/tehran/fereshteh"
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-1.5 font-medium text-slate-700 dark:text-slate-300 hover:border-teal-600"
            >
              <MapPin className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
              فرشته تهران
            </Link>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4"
        >
          <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-200">
            <SlidersHorizontal className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            فیلترهای تخصصی جستجو
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <input
              placeholder="کلیدواژه یا کد ملک..."
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            />
            <input
              placeholder="شهر (تهران)"
              value={filters.city}
              onChange={(e) => setFilters({ ...filters, city: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            />
            <input
              placeholder="منطقه یا محله (مثلاً زعفرانیه)"
              value={filters.district}
              onChange={(e) => setFilters({ ...filters, district: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            />
            <select
              value={filters.deal_type}
              onChange={(e) => setFilters({ ...filters, deal_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            >
              <option value="">همه انواع معامله</option>
              <option value="SALE">فروش</option>
              <option value="MORTGAGE_RENT">رهن و اجاره</option>
            </select>
            <select
              value={filters.property_type}
              onChange={(e) => setFilters({ ...filters, property_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            >
              <option value="">همه کاربری‌ها</option>
              <option value="APARTMENT">آپارتمان</option>
              <option value="VILLA">ویلا</option>
              <option value="OFFICE">اداری</option>
              <option value="LAND">زمین</option>
            </select>
            <input
              type="number"
              placeholder="حداقل متراژ (مترمربع)"
              value={filters.min_area}
              onChange={(e) => setFilters({ ...filters, min_area: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
            />
            <input
              type="number"
              placeholder="حداقل تعداد خواب"
              value={filters.min_bedrooms}
              onChange={(e) => setFilters({ ...filters, min_bedrooms: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
            />
            <button
              type="submit"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
            >
              <Search className="h-4 w-4" />
              اعمال فیلتر و جستجو
            </button>
          </div>
        </form>

        <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
          <span>نتایج مطابق با فیلترهای شما</span>
          <span className="font-mono font-bold">{formatNumberFa((searchQ.data || []).length)} ملک</span>
        </div>

        {searchQ.isLoading ? (
          <LoadingState message="در حال جستجوی پیشرفته..." />
        ) : searchQ.error ? (
          <ErrorState
            message={searchQ.error instanceof Error ? searchQ.error.message : "خطا در جستجو"}
            onRetry={() => searchQ.refetch()}
          />
        ) : (searchQ.data || []).length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-10 text-center text-sm text-slate-600 dark:text-slate-400">
            ملکی با این مشخصات یافت نشد. فیلترها را ساده‌تر کنید یا{" "}
            <Link href="/requests/new" className="font-bold text-teal-700 dark:text-teal-400 underline">
              درخواست خرید اختصاصی ثبت کنید
            </Link>
            .
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {(searchQ.data || []).map((p, idx) => (
              <PropertyCard key={p.id} property={p} index={idx} />
            ))}
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
