"use client";

import React, { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Check, GitCompareArrows, Minus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatArea, formatMoney, formatNumberFa } from "@/lib/formatters";
import type { PropertyItem } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

function CompareContent() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") || "";
  const { accessToken, activeAgencyId, currencyMode } = useAuth();

  const compareQ = useQuery({
    queryKey: ["compare-properties", idsParam, accessToken],
    enabled: idsParam.trim().length > 0,
    queryFn: async () => {
      const env = await apiFetch<PropertyItem[]>(
        `/api/v1/properties/compare?ids=${encodeURIComponent(idsParam)}`,
        {
          token: accessToken,
          agencyId: activeAgencyId,
        }
      );
      return env.data;
    },
  });

  const items = compareQ.data || [];
  const allAmenities = Array.from(
    new Map(
      items.flatMap((p) => (p.amenities || []).map((a) => [a.code, a.name_fa]))
    ).entries()
  );

  return (
    <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
            <GitCompareArrows className="h-6 w-6 text-teal-700 dark:text-teal-400" />
            مقایسه تخصصی مشخصات املاک
          </h1>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            بررسی هم‌زمان قیمت کل، متری، متراژ، سن بنا، نوع سند و امکانات رفاهی فایل‌های انتخابی
          </p>
        </div>
        <Link
          href="/search"
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
        >
          <ArrowRight className="h-4 w-4" />
          بازگشت به جستجو
        </Link>
      </div>

      {!idsParam ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
          ملکی برای مقایسه انتخاب نشده است. از{" "}
          <Link href="/search" className="font-bold text-teal-700 underline dark:text-teal-400">
            صفحه جستجوی پیشرفته
          </Link>{" "}
          حداقل ۲ ملک انتخاب کنید.
        </div>
      ) : compareQ.isLoading ? (
        <LoadingState message="در حال آماده‌سازی جدول مقایسه..." />
      ) : compareQ.error ? (
        <ErrorState
          message={compareQ.error instanceof Error ? compareQ.error.message : "خطا در بارگذاری مقایسه"}
          onRetry={() => compareQ.refetch()}
        />
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
          فایل معتبری برای مقایسه یافت نشد.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <table className="w-full min-w-[680px] text-right text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950/60">
                <th className="w-44 p-4 font-bold text-slate-700 dark:text-slate-300">شاخص مقایسه</th>
                {items.map((p) => (
                  <th key={p.id} className="p-4 align-top">
                    <Link href={`/properties/${p.id}`} className="group block space-y-2">
                      <img
                        src={p.media_items?.[0]?.url || "/images/prop-zafaranieh.jpg"}
                        alt={p.title}
                        referrerPolicy="no-referrer"
                        className="aspect-[16/10] w-full rounded-lg object-cover"
                      />
                      <div className="text-sm font-bold text-slate-900 group-hover:text-teal-700 dark:text-slate-100 dark:group-hover:text-teal-400">
                        {p.title}
                      </div>
                      <div className="font-mono text-[11px] font-normal text-slate-500">
                        {p.property_code} · {p.agency_name}
                      </div>
                    </Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              <tr>
                <td className="p-3.5 font-semibold text-slate-600 dark:text-slate-400">نوع ملک و معامله</td>
                {items.map((p) => (
                  <td key={p.id} className="p-3.5 font-semibold text-slate-900 dark:text-slate-100">
                    {p.property_type.name_fa} · {p.deal_type.name_fa}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3.5 font-semibold text-slate-600 dark:text-slate-400">شهر و منطقه</td>
                {items.map((p) => (
                  <td key={p.id} className="p-3.5 text-slate-800 dark:text-slate-200">
                    {p.location ? `${p.location.city}${p.location.district ? `، ${p.location.district}` : ""}` : "—"}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3.5 font-semibold text-slate-600 dark:text-slate-400">قیمت کل / ودیعه</td>
                {items.map((p) => (
                  <td key={p.id} className="p-3.5 tabular-nums font-bold text-teal-800 dark:text-teal-300">
                    {p.deal_type.is_rental
                      ? `ودیعه: ${formatMoney(p.deposit_amount, p.currency, currencyMode)} / اجاره: ${formatMoney(
                          p.rent_amount,
                          p.currency,
                          currencyMode
                        )}`
                      : formatMoney(p.total_price, p.currency, currencyMode)}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3.5 font-semibold text-slate-600 dark:text-slate-400">قیمت هر مترمربع</td>
                {items.map((p) => (
                  <td key={p.id} className="p-3.5 tabular-nums text-slate-800 dark:text-slate-200">
                    {Number(p.price_per_sqm) > 0
                      ? formatMoney(p.price_per_sqm, p.currency, currencyMode)
                      : "—"}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3.5 font-semibold text-slate-600 dark:text-slate-400">زیربنا / زمین</td>
                {items.map((p) => (
                  <td key={p.id} className="p-3.5 tabular-nums text-slate-800 dark:text-slate-200">
                    {formatArea(p.built_area_sqm)}
                    {Number(p.land_area_sqm) > 0 ? ` (زمین ${formatArea(p.land_area_sqm)})` : ""}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3.5 font-semibold text-slate-600 dark:text-slate-400">اتاق خواب / سرویس</td>
                {items.map((p) => (
                  <td key={p.id} className="p-3.5 tabular-nums text-slate-800 dark:text-slate-200">
                    {formatNumberFa(p.bedrooms)} خواب · {formatNumberFa(p.bathrooms)} سرویس
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3.5 font-semibold text-slate-600 dark:text-slate-400">سن بنا و طبقه</td>
                {items.map((p) => (
                  <td key={p.id} className="p-3.5 tabular-nums text-slate-800 dark:text-slate-200">
                    {p.building_age != null ? `${formatNumberFa(p.building_age)} سال ساخت` : "نامشخص"}
                    {p.floor_number != null ? ` · طبقه ${formatNumberFa(p.floor_number)}` : ""}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3.5 font-semibold text-slate-600 dark:text-slate-400">وضعیت سند</td>
                {items.map((p) => (
                  <td key={p.id} className="p-3.5 text-slate-800 dark:text-slate-200">
                    {p.deed_type} ({p.is_negotiable ? "قابل مذاکره" : "مقطوع"})
                  </td>
                ))}
              </tr>
              {allAmenities.map(([code, label]) => (
                <tr key={code}>
                  <td className="p-3.5 font-medium text-slate-600 dark:text-slate-400">{label}</td>
                  {items.map((p) => {
                    const found = (p.amenities || []).find((a) => a.code === code);
                    const valText = found
                      ? found.value_number
                        ? `${formatNumberFa(found.value_number)} ${found.unit_label || ""}`.trim()
                        : found.value_text || ""
                      : "";
                    return (
                      <td key={p.id} className="p-3.5">
                        {found ? (
                          <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-700 dark:text-emerald-400">
                            <Check className="h-4 w-4" />
                            {valText && <span className="tabular-nums text-xs">{valText}</span>}
                          </span>
                        ) : (
                          <Minus className="h-4 w-4 text-slate-300 dark:text-slate-700" />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

export default function ComparePropertiesPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <Suspense fallback={<LoadingState message="در حال بارگذاری..." />}>
        <CompareContent />
      </Suspense>
      <PublicFooter />
    </div>
  );
}
