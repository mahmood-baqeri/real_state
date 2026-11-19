import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { MapPin } from "lucide-react";
import { getApiOrigin } from "@/lib/seo";
import type { PublicSearchProperty } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { formatMoney, formatNumberFa } from "@/lib/formatters";

export const dynamic = "force-dynamic";

const SLUG_MAP: Record<string, string> = {
  tehran: "تهران",
  zafaranieh: "زعفرانیه",
  fereshteh: "فرشته",
  niavaran: "نیاوران",
  "saadat-abad": "سعادت‌آباد",
  lavasan: "لواسان",
  shiraz: "شیراز",
  isfahan: "اصفهان",
};

function mapLocationLabel(slugSegment?: string): string {
  if (!slugSegment) return "";
  const lower = decodeURIComponent(slugSegment).toLowerCase();
  return SLUG_MAP[lower] || decodeURIComponent(slugSegment);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const city = mapLocationLabel(slug?.[0]) || "تهران";
  const district = mapLocationLabel(slug?.[1]);
  const locTitle = district ? `${district}، ${city}` : city;
  return {
    title: `خرید و اجاره املاک در ${locTitle}`,
    description: `فهرست فایل‌های ملکی تاییدشده و شاخص میانگین قیمت هر متر مربع در ${locTitle} در پلتفرم بنیان ملک`,
  };
}

export default async function ExploreLocationPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug } = await params;
  const city = mapLocationLabel(slug?.[0]) || "تهران";
  const district = mapLocationLabel(slug?.[1]);
  const locTitle = district ? `${district} (${city})` : city;

  let properties: PublicSearchProperty[] = [];
  let trends: { district: string; listing_count: number; avg_price_per_sqm: string }[] = [];

  try {
    const qs = new URLSearchParams({ city });
    if (district) qs.set("district", district);
    const [propRes, trendRes] = await Promise.all([
      fetch(`${getApiOrigin()}/api/v1/search/properties?${qs.toString()}`, { cache: "no-store" }),
      fetch(`${getApiOrigin()}/api/v1/matching/analytics/price-trends?city=${encodeURIComponent(city)}`, {
        cache: "no-store",
      }),
    ]);
    if (propRes.ok) {
      const pj = await propRes.json();
      properties = Array.isArray(pj?.data) ? pj.data : [];
    }
    if (trendRes.ok) {
      const tj = await trendRes.json();
      trends = Array.isArray(tj?.data) ? tj.data : [];
    }
  } catch {
    // Graceful fallback if backend is offline during static check
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-10 sm:px-6 lg:px-8 space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-6">
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-teal-700 dark:text-teal-400">
              <MapPin className="h-4 w-4" />
              کاوش منطقه‌ای املاک
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100">
              فایل‌های تاییدشده و تحلیل قیمت در {locTitle}
            </h1>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <Link href="/explore/tehran" className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 font-semibold">
              کل تهران
            </Link>
            <Link href="/explore/tehran/zafaranieh" className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 font-semibold">
              زعفرانیه
            </Link>
            <Link href="/explore/tehran/fereshteh" className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 font-semibold">
              فرشته
            </Link>
            <Link href="/explore/tehran/saadat-abad" className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 font-semibold">
              سعادت‌آباد
            </Link>
          </div>
        </div>

        {trends.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {trends.slice(0, 3).map((t) => (
              <div
                key={t.district}
                className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4"
              >
                <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">منطقه {t.district}</div>
                <div className="mt-1 tabular-nums text-base font-bold text-teal-800 dark:text-teal-300">
                  متری {formatMoney(t.avg_price_per_sqm, "IRT", "IRT")}
                </div>
                <div className="mt-1 text-[11px] text-slate-500">{formatNumberFa(t.listing_count)} فایل فعال</div>
              </div>
            ))}
          </div>
        )}

        {properties.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-10 text-center text-sm text-slate-600 dark:text-slate-400">
            در حال حاضر فایل عمومی فعالی برای «{locTitle}» ثبت نشده است.{" "}
            <Link href="/requests/new" className="font-bold text-teal-700 dark:text-teal-400 underline">
              ثبت درخواست جستجوی اختصاصی
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {properties.map((p, idx) => (
              <PropertyCard key={p.id} property={p} index={idx} />
            ))}
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
