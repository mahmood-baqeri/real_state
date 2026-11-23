"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  Compass,
  Filter,
  Home,
  Map as MapIcon,
  RotateCcw,
  Search,
  Sparkles,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import type { PropertyCatalog, PropertyItem, PublicSearchProperty } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { formatNumberFa } from "@/lib/formatters";

function toCardItem(p: PropertyItem): PublicSearchProperty {
  const coverMedia = (p.media_items || []).find((m) => m.is_cover) || p.media_items?.[0];
  return {
    id: p.id,
    property_code: p.property_code,
    title: p.title,
    property_type_id: p.property_type?.code || p.property_type_id || "APARTMENT",
    property_type_name: p.property_type?.name_fa || "ملک",
    deal_type_id: p.deal_type?.code || p.deal_type_id || "SALE",
    deal_type_name: p.deal_type?.name_fa || "فروش",
    built_area_sqm: p.built_area_sqm,
    bedrooms: p.bedrooms,
    total_price: p.total_price,
    price_per_sqm: p.price_per_sqm,
    deposit_amount: p.deposit_amount,
    rent_amount: p.rent_amount,
    currency_id: p.currency || "IRT",
    is_featured: p.is_featured,
    province_id: p.location?.province_id,
    city_id: p.location?.city_id,
    district_id: p.location?.district_id,
    neighborhood_id: p.location?.neighborhood_id,
    province: p.location?.province,
    city: p.location?.city || "تهران",
    district: p.location?.district || "",
    neighborhood: p.location?.neighborhood || "",
    latitude: p.location?.latitude,
    longitude: p.location?.longitude,
    agency_name: p.agency_name,
    cover_url: coverMedia?.url || null,
  };
}

export default function PublicPropertiesPage() {
  const [page, setPage] = useState(1);
  const [formState, setFormState] = useState({
    q: "",
    deal_type: "",
    property_type: "",
    city: "",
    min_price: "",
    max_price: "",
    min_area: "",
    max_area: "",
    featured: false,
  });
  const [applied, setApplied] = useState(formState);

  const catalogQ = useQuery({
    queryKey: ["property-catalog"],
    queryFn: async () => (await apiFetch<PropertyCatalog>("/api/v1/properties/catalog")).data,
  });

  const listQ = useQuery({
    queryKey: ["public-properties-catalog", applied, page],
    queryFn: async () => {
      const p = new URLSearchParams();
      p.set("page", String(page));
      p.set("page_size", "12");
      if (applied.q) p.set("q", applied.q);
      if (applied.deal_type) p.set("deal_type", applied.deal_type);
      if (applied.property_type) p.set("property_type", applied.property_type);
      if (applied.city) p.set("city", applied.city);
      if (applied.min_price) p.set("min_price", applied.min_price);
      if (applied.max_price) p.set("max_price", applied.max_price);
      if (applied.min_area) p.set("min_area", applied.min_area);
      if (applied.max_area) p.set("max_area", applied.max_area);
      if (applied.featured) p.set("featured", "true");
      return apiFetch<PropertyItem[]>(`/api/v1/properties/public?${p.toString()}`);
    },
  });

  const items = useMemo(() => listQ.data?.data || [], [listQ.data]);
  const pagination = listQ.data?.meta?.pagination;

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setApplied(formState);
  };

  const handleReset = () => {
    const empty = {
      q: "",
      deal_type: "",
      property_type: "",
      city: "",
      min_price: "",
      max_price: "",
      min_area: "",
      max_area: "",
      featured: false,
    };
    setFormState(empty);
    setApplied(empty);
    setPage(1);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        {/* Hero Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <div>
            <div className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-700 dark:text-teal-400">
              <Building2 className="h-4 w-4" />
              پورتال جامع املاک تأییدشده بنیان ملک
            </div>
            <h1 className="mt-1.5 text-2xl font-extrabold text-slate-900 dark:text-slate-100">
              بانک فایل‌های ملکی عمومی
            </h1>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              تمامی آگهی‌های منتشرشده پس از احراز اصالت توسط آژانس‌های عضو و با حفظ کامل حریم خصوصی مالکین نمایش داده می‌شوند.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/search"
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <MapIcon className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              جستجوی نقشه تعاملی
            </Link>
            <Link
              href="/requests/new"
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
            >
              <Home className="h-4 w-4" />
              ثبت درخواست ملک
            </Link>
          </div>
        </div>

        {/* Filter Bar */}
        <form
          onSubmit={handleApply}
          className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-200">
              <Filter className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              فیلتر و جستجوی سریع فایل‌ها
            </div>
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-rose-600 dark:text-slate-400"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              پاک کردن فیلترها
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <input
              type="text"
              placeholder="جستجو در عنوان، محله یا کد ملک..."
              value={formState.q}
              onChange={(e) => setFormState({ ...formState, q: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
            <select
              value={formState.deal_type}
              onChange={(e) => setFormState({ ...formState, deal_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            >
              <option value="">همه انواع معامله</option>
              {(catalogQ.data?.deal_types || []).map((dt) => (
                <option key={dt.code} value={dt.code}>
                  {dt.name_fa}
                </option>
              ))}
            </select>
            <select
              value={formState.property_type}
              onChange={(e) => setFormState({ ...formState, property_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            >
              <option value="">همه انواع ملک</option>
              {(catalogQ.data?.property_types || []).map((pt) => (
                <option key={pt.code} value={pt.code}>
                  {pt.name_fa}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="شهر (مثلاً تهران، شیراز...)"
              value={formState.city}
              onChange={(e) => setFormState({ ...formState, city: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
            <input
              type="number"
              placeholder="حداقل قیمت (تومان)"
              value={formState.min_price}
              onChange={(e) => setFormState({ ...formState, min_price: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 font-mono text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
            <input
              type="number"
              placeholder="حداکثر قیمت (تومان)"
              value={formState.max_price}
              onChange={(e) => setFormState({ ...formState, max_price: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 font-mono text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                placeholder="از متراژ"
                value={formState.min_area}
                onChange={(e) => setFormState({ ...formState, min_area: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 bg-white px-3 font-mono text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
              <input
                type="number"
                placeholder="تا متراژ"
                value={formState.max_area}
                onChange={(e) => setFormState({ ...formState, max_area: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 bg-white px-3 font-mono text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={formState.featured}
                  onChange={(e) => setFormState({ ...formState, featured: e.target.checked })}
                  className="h-4 w-4 accent-teal-700"
                />
                فقط فایل‌های ویژه
              </label>
              <button
                type="submit"
                className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
              >
                <Search className="h-4 w-4" />
                جستجو
              </button>
            </div>
          </div>
        </form>

        {/* Results Meta */}
        <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
          <span>نمایش فایل‌های منتشرشده عمومی</span>
          <span className="font-mono font-bold tabular-nums">
            {formatNumberFa(pagination?.total_count ?? items.length)} فایل موجود
          </span>
        </div>

        {/* Grid */}
        {listQ.isLoading ? (
          <LoadingState message="در حال دریافت فایل‌های ملکی عمومی..." />
        ) : listQ.error ? (
          <ErrorState
            message={listQ.error instanceof Error ? listQ.error.message : "خطا در دریافت املاک عمومی"}
            onRetry={() => listQ.refetch()}
          />
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
            فایل ملکی با فیلترهای انتخاب‌شده یافت نشد. فیلترها را تغییر دهید یا از جستجوی پیشرفته روی نقشه استفاده کنید.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((prop, idx) => (
              <div key={prop.id} className="relative">
                <PropertyCard property={toCardItem(prop)} index={idx} />
                {prop.has_virtual_tour && (
                  <span className="pointer-events-none absolute top-11 right-2.5 inline-flex items-center gap-1 rounded-md bg-amber-600/95 px-2 py-0.5 text-[10px] font-bold text-white shadow-xs">
                    <Compass className="h-3 w-3" />
                    تور مجازی ۳۶۰°
                  </span>
                )}
                {prop.is_featured && (
                  <span className="pointer-events-none absolute top-2.5 left-2.5 inline-flex items-center gap-1 rounded-md bg-teal-700/95 px-2 py-0.5 text-[10px] font-bold text-white shadow-xs">
                    <Sparkles className="h-3 w-3" />
                    ویژه
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {pagination && pagination.total_pages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-4">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="h-9 rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              صفحه قبل
            </button>
            <span className="px-3 font-mono text-xs font-bold tabular-nums text-slate-700 dark:text-slate-300">
              صفحه {formatNumberFa(page)} از {formatNumberFa(pagination.total_pages)}
            </span>
            <button
              type="button"
              disabled={page >= pagination.total_pages}
              onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
              className="h-9 rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              صفحه بعد
            </button>
          </div>
        )}
      </main>

      <PublicFooter />
    </div>
  );
}
