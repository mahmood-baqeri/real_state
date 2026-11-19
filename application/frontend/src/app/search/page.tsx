"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronUp,
  GitCompareArrows,
  LayoutGrid,
  Map as MapIcon,
  MapPin,
  RotateCcw,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import type { PropertyCatalog, PublicSearchProperty } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { PropertyCard } from "@/components/properties/PropertyCard";
import {
  InteractiveMap,
  buildPropertyPriceLabel,
  type GeoBounds,
  type MapMarkerItem,
} from "@/components/ui/InteractiveMap";
import { LocationCascadeSelect, type GeoCascadeValue } from "@/components/ui/LocationCascadeSelect";
import { CategorizedAmenitySelector } from "@/components/ui/CategorizedAmenitySelector";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { formatNumberFa } from "@/lib/formatters";

export default function AdvancedSearchPage() {
  const [viewMode, setViewMode] = useState<"list" | "split">("split");
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [showAmenitiesFilter, setShowAmenitiesFilter] = useState(false);

  const [pendingBounds, setPendingBounds] = useState<GeoBounds | null>(null);
  const [appliedBounds, setAppliedBounds] = useState<GeoBounds | null>(null);
  const [appliedPolygon, setAppliedPolygon] = useState<[number, number][] | null>(null);

  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null);
  const [hoveredPropertyId, setHoveredPropertyId] = useState<string | null>(null);

  const [geo, setGeo] = useState<GeoCascadeValue>({
    province_id: null,
    city_id: null,
    district_id: null,
    neighborhood_id: null,
  });

  const [selectedAmenities, setSelectedAmenities] = useState<string[]>([]);
  const [filters, setFilters] = useState({
    q: "",
    deal_type: "",
    property_type: "",
    min_price: "",
    max_price: "",
    min_area: "",
    max_area: "",
    min_bedrooms: "",
  });

  const [applied, setApplied] = useState({
    ...filters,
    province_id: "" as string,
    city_id: "" as string,
    district_id: "" as string,
    neighborhood_id: "" as string,
    amenities: [] as string[],
  });

  const catalogQ = useQuery({
    queryKey: ["property-catalog"],
    queryFn: async () => (await apiFetch<PropertyCatalog>("/api/v1/properties/catalog")).data,
  });

  const searchQ = useQuery({
    queryKey: ["advanced-public-search", applied, appliedBounds, appliedPolygon],
    queryFn: async () => {
      const p = new URLSearchParams();
      if (applied.q) p.set("q", applied.q);
      if (applied.province_id) p.set("province_id", applied.province_id);
      if (applied.city_id) p.set("city_id", applied.city_id);
      if (applied.district_id) p.set("district_id", applied.district_id);
      if (applied.neighborhood_id) p.set("neighborhood_id", applied.neighborhood_id);
      if (applied.deal_type) p.set("deal_type", applied.deal_type);
      if (applied.property_type) p.set("property_type", applied.property_type);
      if (applied.min_price) p.set("min_price", applied.min_price);
      if (applied.max_price) p.set("max_price", applied.max_price);
      if (applied.min_area) p.set("min_area", applied.min_area);
      if (applied.max_area) p.set("max_area", applied.max_area);
      if (applied.min_bedrooms) p.set("min_bedrooms", applied.min_bedrooms);
      if (applied.amenities.length > 0) p.set("amenities", applied.amenities.join(","));

      if (appliedPolygon && appliedPolygon.length >= 3) {
        p.set("polygon", JSON.stringify(appliedPolygon));
      } else if (appliedBounds) {
        p.set("min_lat", String(appliedBounds.min_lat));
        p.set("max_lat", String(appliedBounds.max_lat));
        p.set("min_lng", String(appliedBounds.min_lng));
        p.set("max_lng", String(appliedBounds.max_lng));
      }

      const env = await apiFetch<PublicSearchProperty[]>(
        `/api/v1/search/properties?${p.toString()}`
      );
      return env;
    },
  });

  const applyCurrentFilters = (nextGeo: GeoCascadeValue = geo, nextAmenities: string[] = selectedAmenities) => {
    setApplied({
      ...filters,
      province_id: nextGeo.province_id || "",
      city_id: nextGeo.city_id || "",
      district_id: nextGeo.district_id || "",
      neighborhood_id: nextGeo.neighborhood_id || "",
      amenities: nextAmenities,
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    applyCurrentFilters();
  };

  const handleResetAll = () => {
    const emptyGeo: GeoCascadeValue = {
      province_id: null,
      city_id: null,
      district_id: null,
      neighborhood_id: null,
    };
    const emptyFilters = {
      q: "",
      deal_type: "",
      property_type: "",
      min_price: "",
      max_price: "",
      min_area: "",
      max_area: "",
      min_bedrooms: "",
    };
    setGeo(emptyGeo);
    setSelectedAmenities([]);
    setFilters(emptyFilters);
    setAppliedBounds(null);
    setAppliedPolygon(null);
    setApplied({
      ...emptyFilters,
      province_id: "",
      city_id: "",
      district_id: "",
      neighborhood_id: "",
      amenities: [],
    });
  };

  const toggleCompare = (id: string) => {
    setCompareIds((prev) => {
      if (prev.includes(id)) return prev.filter((item) => item !== id);
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
  };

  const items = useMemo(() => searchQ.data?.data || [], [searchQ.data]);
  const totalHits = searchQ.data?.meta?.pagination?.total_count ?? items.length;

  const mapMarkers: MapMarkerItem[] = useMemo(() => {
    return items
      .filter((p) => p.latitude && p.longitude)
      .map((p) => ({
        id: p.id,
        title: p.title,
        subtitle: `${p.city}${p.district ? `، ${p.district}` : ""}`,
        lat: Number(p.latitude),
        lng: Number(p.longitude),
        coverUrl: p.cover_url,
        priceText: buildPropertyPriceLabel(
          p.total_price,
          p.deposit_amount,
          p.rent_amount,
          p.deal_type_id,
          p.currency_id
        ),
        hideExactAddress: true,
        href: `/properties/${p.id}`,
      }));
  }, [items]);

  const activeSpatialLabel = appliedPolygon?.length
    ? `فیلتر محدوده چندضلعی/مستطیلی (${formatNumberFa(appliedPolygon.length)} رأس)`
    : appliedBounds
    ? "فیلتر محدوده دید نقشه فعال است"
    : null;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              جستجوی پیشرفته و نقشه تعاملی املاک
            </h1>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              انتخاب سلسله‌مراتبی استان تا محله، امکانات دسته‌بندی‌شده و رسم محدوده مستطیلی یا چندضلعی روی نقشه
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
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

            <div className="inline-flex items-center rounded-lg border border-slate-200 bg-white p-0.5 dark:border-slate-800 dark:bg-slate-900">
              <button
                type="button"
                onClick={() => setViewMode("split")}
                className={`inline-flex h-8 items-center gap-1.5 rounded-md px-3 font-semibold transition-colors ${
                  viewMode === "split"
                    ? "bg-teal-700 text-white"
                    : "text-slate-600 dark:text-slate-300"
                }`}
              >
                <MapIcon className="h-3.5 w-3.5" />
                نقشه + فهرست
              </button>
              <button
                type="button"
                onClick={() => setViewMode("list")}
                className={`inline-flex h-8 items-center gap-1.5 rounded-md px-3 font-semibold transition-colors ${
                  viewMode === "list"
                    ? "bg-teal-700 text-white"
                    : "text-slate-600 dark:text-slate-300"
                }`}
              >
                <LayoutGrid className="h-3.5 w-3.5" />
                شبکه‌ای
              </button>
            </div>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-200">
              <SlidersHorizontal className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              موقعیت مکانی سلسله‌مراتبی و فیلترهای تخصصی
            </div>
            <button
              type="button"
              onClick={handleResetAll}
              className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-rose-600 dark:text-slate-400"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              پاک کردن همه فیلترها
            </button>
          </div>

          <LocationCascadeSelect
            value={geo}
            compact
            onChange={(nextGeo) => {
              setGeo(nextGeo);
              applyCurrentFilters(nextGeo, selectedAmenities);
            }}
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <input
              placeholder="کلیدواژه یا کد ملک..."
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            />
            <select
              value={filters.deal_type}
              onChange={(e) => setFilters({ ...filters, deal_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            >
              <option value="">همه انواع معامله</option>
              {(catalogQ.data?.deal_types || []).map((dt) => (
                <option key={dt.code} value={dt.code}>
                  {dt.name_fa}
                </option>
              ))}
            </select>
            <select
              value={filters.property_type}
              onChange={(e) => setFilters({ ...filters, property_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            >
              <option value="">همه انواع ملک</option>
              {(catalogQ.data?.property_types || []).map((pt) => (
                <option key={pt.code} value={pt.code}>
                  {pt.name_fa}
                </option>
              ))}
            </select>
            <input
              type="number"
              placeholder="حداقل تعداد خواب"
              value={filters.min_bedrooms}
              onChange={(e) => setFilters({ ...filters, min_bedrooms: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
            />
            <input
              type="number"
              placeholder="حداقل قیمت (تومان)"
              value={filters.min_price}
              onChange={(e) => setFilters({ ...filters, min_price: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
            />
            <input
              type="number"
              placeholder="حداکثر قیمت (تومان)"
              value={filters.max_price}
              onChange={(e) => setFilters({ ...filters, max_price: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                placeholder="از متراژ"
                value={filters.min_area}
                onChange={(e) => setFilters({ ...filters, min_area: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
              />
              <input
                type="number"
                placeholder="تا متراژ"
                value={filters.max_area}
                onChange={(e) => setFilters({ ...filters, max_area: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
              />
            </div>
            <button
              type="submit"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
            >
              <Search className="h-4 w-4" />
              اعمال فیلتر و جستجو
            </button>
          </div>

          {/* Categorized Amenities Filter Drawer */}
          <div className="border-t border-slate-100 pt-3 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setShowAmenitiesFilter((v) => !v)}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-700 hover:text-teal-800 dark:text-teal-400"
            >
              {showAmenitiesFilter ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              فیلتر پیشرفته بر اساس امکانات ملک ({formatNumberFa(selectedAmenities.length)} مورد انتخاب شده)
            </button>

            {showAmenitiesFilter && catalogQ.data?.amenities && (
              <div className="mt-3">
                <CategorizedAmenitySelector
                  categories={catalogQ.data.amenity_categories || []}
                  amenities={catalogQ.data.amenities}
                  selectedCodes={selectedAmenities}
                  showTypedInputs={false}
                  compact
                  onToggleCode={(code) => {
                    const next = selectedAmenities.includes(code)
                      ? selectedAmenities.filter((c) => c !== code)
                      : [...selectedAmenities, code];
                    setSelectedAmenities(next);
                    applyCurrentFilters(geo, next);
                  }}
                />
              </div>
            )}
          </div>
        </form>

        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600 dark:text-slate-400">
          <div className="flex flex-wrap items-center gap-2">
            <span>
              نتایج مطابق با فیلترهای شما (روی کارت هاور کنید تا روی نقشه مشخص شود، یا روی مارکر نقشه کلیک کنید)
            </span>
            {activeSpatialLabel && (
              <span className="rounded-md border border-amber-300 bg-amber-50 px-2 py-0.5 font-semibold text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
                {activeSpatialLabel}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {(appliedBounds || appliedPolygon) && (
              <button
                type="button"
                onClick={() => {
                  setAppliedBounds(null);
                  setAppliedPolygon(null);
                }}
                className="inline-flex items-center gap-1 font-semibold text-amber-700 hover:underline dark:text-amber-400"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                حذف محدوده جغرافیایی نقشه
              </button>
            )}
            <span className="font-mono font-bold tabular-nums">{formatNumberFa(totalHits)} ملک</span>
          </div>
        </div>

        {searchQ.isLoading ? (
          <LoadingState message="در حال جستجوی مکانی و پیشرفته..." />
        ) : searchQ.error ? (
          <ErrorState
            message={searchQ.error instanceof Error ? searchQ.error.message : "خطا در جستجو"}
            onRetry={() => searchQ.refetch()}
          />
        ) : viewMode === "split" ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <div className="lg:col-span-5 lg:sticky lg:top-20 lg:self-start space-y-3">
              <InteractiveMap
                markers={mapMarkers}
                heightClass="h-[490px]"
                enableDrawing
                selectedId={selectedPropertyId}
                highlightedId={hoveredPropertyId}
                activePolygon={appliedPolygon}
                onBoundsChange={(b) => setPendingBounds(b)}
                onApplyVisibleBounds={(b) => {
                  setAppliedPolygon(null);
                  setAppliedBounds(b);
                }}
                onPolygonChange={(poly) => {
                  setAppliedBounds(null);
                  setAppliedPolygon(poly);
                }}
                onSelectMarker={(id) => {
                  setSelectedPropertyId(id);
                  const el = document.getElementById(`search-card-${id}`);
                  el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }}
              />
              {pendingBounds && !appliedPolygon && (
                <button
                  type="button"
                  onClick={() => setAppliedBounds(pendingBounds)}
                  className="inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg border border-teal-700 bg-teal-50 text-xs font-semibold text-teal-800 hover:bg-teal-100 dark:border-teal-500 dark:bg-teal-950/60 dark:text-teal-300"
                >
                  <MapPin className="h-3.5 w-3.5" />
                  جستجو در محدوده دید فعلی نقشه
                </button>
              )}
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                دایره‌های سبز حدود تقریبی ملک را با حفظ حریم مالک و خوشه‌های عددی تراکم املاک را نشان می‌دهند.
              </p>
            </div>

            <div className="lg:col-span-7">
              {items.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-10 text-center text-sm text-slate-600 dark:text-slate-400">
                  ملکی با این مشخصات یا محدوده مکانی یافت نشد. فیلترها یا محدوده رسم‌شده روی نقشه را بازتر کنید یا{" "}
                  <Link href="/requests/new" className="font-bold text-teal-700 dark:text-teal-400 underline">
                    درخواست خرید اختصاصی ثبت کنید
                  </Link>
                  .
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                  {items.map((p, idx) => (
                    <div
                      key={p.id}
                      id={`search-card-${p.id}`}
                      onMouseEnter={() => setHoveredPropertyId(p.id)}
                      onMouseLeave={() => setHoveredPropertyId(null)}
                      className={`rounded-xl transition-all ${
                        selectedPropertyId === p.id
                          ? "ring-2 ring-amber-500 ring-offset-2 dark:ring-offset-slate-950"
                          : ""
                      }`}
                    >
                      <PropertyCard
                        property={p}
                        index={idx}
                        isSelectedForCompare={compareIds.includes(p.id)}
                        onToggleCompare={toggleCompare}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-10 text-center text-sm text-slate-600 dark:text-slate-400">
            ملکی با این مشخصات یافت نشد. فیلترها را ساده‌تر کنید یا{" "}
            <Link href="/requests/new" className="font-bold text-teal-700 dark:text-teal-400 underline">
              درخواست خرید اختصاصی ثبت کنید
            </Link>
            .
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((p, idx) => (
              <PropertyCard
                key={p.id}
                property={p}
                index={idx}
                isSelectedForCompare={compareIds.includes(p.id)}
                onToggleCompare={toggleCompare}
              />
            ))}
          </div>
        )}
      </main>

      {compareIds.length > 0 && (
        <div className="sticky bottom-4 z-40 mx-auto w-full max-w-2xl px-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-700 bg-slate-900 px-4 py-3 text-white shadow-xl">
            <div className="flex items-center gap-2 text-xs">
              <GitCompareArrows className="h-4 w-4 text-teal-400" />
              <span className="font-semibold">
                {formatNumberFa(compareIds.length)} ملک برای مقایسه انتخاب شده (حداکثر ۴ ملک)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCompareIds([])}
                className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-700 px-2.5 text-xs text-slate-300 hover:bg-slate-800"
              >
                <X className="h-3.5 w-3.5" />
                پاک کردن
              </button>
              {compareIds.length >= 2 ? (
                <Link
                  href={`/properties/compare?ids=${compareIds.join(",")}`}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-teal-600 px-3.5 text-xs font-semibold text-white hover:bg-teal-500"
                >
                  مشاهده جدول مقایسه
                </Link>
              ) : (
                <span className="text-[11px] text-slate-400">حداقل ۱ ملک دیگر انتخاب کنید</span>
              )}
            </div>
          </div>
        </div>
      )}

      <PublicFooter />
    </div>
  );
}
