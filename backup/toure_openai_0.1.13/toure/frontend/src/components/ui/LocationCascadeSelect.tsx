"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, MapPin, Search, X } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import type { CityItem, DistrictItem, NeighborhoodItem, ProvinceItem } from "@/lib/types";

export interface GeoCascadeValue {
  province_id: string | null;
  city_id: string | null;
  district_id: string | null;
  neighborhood_id: string | null;
  province_name?: string;
  city_name?: string;
  district_name?: string;
  neighborhood_name?: string;
  center_lat?: number | null;
  center_lng?: number | null;
}

interface GeoOption {
  id: string;
  label: string;
  sublabel?: string;
  lat?: string | null;
  lng?: string | null;
}

function SearchableGeoDropdown({
  label,
  placeholder,
  options,
  valueId,
  disabled = false,
  loading = false,
  required = false,
  onSelect,
}: {
  label: string;
  placeholder: string;
  options: GeoOption[];
  valueId: string | null;
  disabled?: boolean;
  loading?: boolean;
  required?: boolean;
  onSelect: (opt: GeoOption | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  const selected = useMemo(
    () => options.find((o) => o.id === valueId) || null,
    [options, valueId]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (o) => o.label.toLowerCase().includes(q) || (o.sublabel || "").toLowerCase().includes(q)
    );
  }, [options, query]);

  return (
    <div ref={containerRef} className="relative">
      <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
        {label}
        {required ? " *" : ""}
      </label>
      <div
        className={`flex h-10 w-full items-center justify-between gap-2 rounded-lg border px-3 text-sm transition-colors ${
          disabled
            ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-500"
            : "cursor-pointer border-slate-300 bg-white text-slate-900 hover:border-teal-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:hover:border-teal-500"
        }`}
        onClick={() => {
          if (!disabled) setOpen((v) => !v);
        }}
      >
        <div className="flex min-w-0 items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-teal-700 dark:text-teal-400" />
          <span className={`truncate ${selected ? "font-medium" : "text-slate-400 dark:text-slate-500"}`}>
            {loading ? "در حال بارگذاری..." : selected ? selected.label : placeholder}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {selected && !disabled && (
            <button
              type="button"
              aria-label={`پاک کردن ${label}`}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(null);
                setQuery("");
              }}
              className="rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </div>
      </div>

      {open && !disabled && (
        <div className="absolute right-0 top-[calc(100%+4px)] z-40 w-full min-w-[210px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900">
          <div className="border-b border-slate-100 p-2 dark:border-slate-800">
            <div className="relative">
              <Search className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={`جستجو در ${label}...`}
                className="h-8 w-full rounded-md border border-slate-200 bg-slate-50 pr-8 pl-2 text-xs text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>
          </div>
          <div className="max-h-56 overflow-y-auto p-1">
            <button
              type="button"
              onClick={() => {
                onSelect(null);
                setOpen(false);
                setQuery("");
              }}
              className="flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-right text-xs text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              همه / انتخاب نشده
            </button>
            {filtered.length === 0 ? (
              <div className="px-3 py-4 text-center text-xs text-slate-400">
                موردی یافت نشد
              </div>
            ) : (
              filtered.map((opt) => {
                const isActive = opt.id === valueId;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => {
                      onSelect(opt);
                      setOpen(false);
                      setQuery("");
                    }}
                    className={`flex w-full items-center justify-between rounded-md px-2.5 py-2 text-right text-xs transition-colors ${
                      isActive
                        ? "bg-teal-50 font-bold text-teal-800 dark:bg-teal-950/60 dark:text-teal-300"
                        : "text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                    }`}
                  >
                    <span>{opt.label}</span>
                    {opt.sublabel && (
                      <span className="font-mono text-[10px] text-slate-400">{opt.sublabel}</span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function LocationCascadeSelect({
  value,
  onChange,
  requiredCity = false,
  compact = false,
}: {
  value: GeoCascadeValue;
  onChange: (next: GeoCascadeValue) => void;
  requiredCity?: boolean;
  compact?: boolean;
}) {
  const provincesQ = useQuery({
    queryKey: ["geo-provinces"],
    queryFn: async () =>
      (await apiFetch<ProvinceItem[]>("/api/v1/locations/provinces?page_size=200")).data,
  });

  const citiesQ = useQuery({
    queryKey: ["geo-cities", value.province_id],
    enabled: !!value.province_id,
    queryFn: async () =>
      (
        await apiFetch<CityItem[]>(
          `/api/v1/locations/cities?province_id=${value.province_id}&page_size=200`
        )
      ).data,
  });

  const districtsQ = useQuery({
    queryKey: ["geo-districts", value.city_id],
    enabled: !!value.city_id,
    queryFn: async () =>
      (
        await apiFetch<DistrictItem[]>(
          `/api/v1/locations/districts?city_id=${value.city_id}&page_size=200`
        )
      ).data,
  });

  const neighborhoodsQ = useQuery({
    queryKey: ["geo-neighborhoods", value.district_id],
    enabled: !!value.district_id,
    queryFn: async () =>
      (
        await apiFetch<NeighborhoodItem[]>(
          `/api/v1/locations/neighborhoods?district_id=${value.district_id}&page_size=200`
        )
      ).data,
  });

  const provinceOptions: GeoOption[] = useMemo(
    () =>
      (provincesQ.data || []).map((p) => ({
        id: p.id,
        label: p.name_fa,
        sublabel: p.name_en,
        lat: p.center_lat,
        lng: p.center_lng,
      })),
    [provincesQ.data]
  );

  const cityOptions: GeoOption[] = useMemo(
    () =>
      (citiesQ.data || []).map((c) => ({
        id: c.id,
        label: c.name_fa,
        sublabel: c.name_en,
        lat: c.center_lat,
        lng: c.center_lng,
      })),
    [citiesQ.data]
  );

  const districtOptions: GeoOption[] = useMemo(
    () =>
      (districtsQ.data || []).map((d) => ({
        id: d.id,
        label: d.name_fa,
        sublabel: d.name_en,
        lat: d.center_lat,
        lng: d.center_lng,
      })),
    [districtsQ.data]
  );

  const neighborhoodOptions: GeoOption[] = useMemo(
    () =>
      (neighborhoodsQ.data || []).map((n) => ({
        id: n.id,
        label: n.name_fa,
        sublabel: n.name_en,
        lat: n.center_lat,
        lng: n.center_lng,
      })),
    [neighborhoodsQ.data]
  );

  return (
    <div
      className={`grid grid-cols-1 gap-3 ${
        compact ? "sm:grid-cols-2 lg:grid-cols-4" : "sm:grid-cols-2 lg:grid-cols-4"
      }`}
    >
      <SearchableGeoDropdown
        label="استان"
        placeholder="انتخاب استان..."
        options={provinceOptions}
        valueId={value.province_id}
        loading={provincesQ.isLoading}
        required={requiredCity}
        onSelect={(opt) =>
          onChange({
            province_id: opt?.id || null,
            province_name: opt?.label || "",
            city_id: null,
            city_name: "",
            district_id: null,
            district_name: "",
            neighborhood_id: null,
            neighborhood_name: "",
            center_lat: opt?.lat ? Number(opt.lat) : null,
            center_lng: opt?.lng ? Number(opt.lng) : null,
          })
        }
      />

      <SearchableGeoDropdown
        label="شهر"
        placeholder={value.province_id ? "انتخاب شهر..." : "ابتدا استان را انتخاب کنید"}
        options={cityOptions}
        valueId={value.city_id}
        disabled={!value.province_id}
        loading={citiesQ.isLoading}
        required={requiredCity}
        onSelect={(opt) =>
          onChange({
            province_id: value.province_id,
            province_name: value.province_name,
            city_id: opt?.id || null,
            city_name: opt?.label || "",
            district_id: null,
            district_name: "",
            neighborhood_id: null,
            neighborhood_name: "",
            center_lat: opt?.lat ? Number(opt.lat) : value.center_lat,
            center_lng: opt?.lng ? Number(opt.lng) : value.center_lng,
          })
        }
      />

      <SearchableGeoDropdown
        label="منطقه"
        placeholder={value.city_id ? "انتخاب منطقه..." : "ابتدا شهر را انتخاب کنید"}
        options={districtOptions}
        valueId={value.district_id}
        disabled={!value.city_id}
        loading={districtsQ.isLoading}
        onSelect={(opt) =>
          onChange({
            province_id: value.province_id,
            province_name: value.province_name,
            city_id: value.city_id,
            city_name: value.city_name,
            district_id: opt?.id || null,
            district_name: opt?.label || "",
            neighborhood_id: null,
            neighborhood_name: "",
            center_lat: opt?.lat ? Number(opt.lat) : value.center_lat,
            center_lng: opt?.lng ? Number(opt.lng) : value.center_lng,
          })
        }
      />

      <SearchableGeoDropdown
        label="محله"
        placeholder={value.district_id ? "انتخاب محله..." : "ابتدا منطقه را انتخاب کنید"}
        options={neighborhoodOptions}
        valueId={value.neighborhood_id}
        disabled={!value.district_id}
        loading={neighborhoodsQ.isLoading}
        onSelect={(opt) =>
          onChange({
            province_id: value.province_id,
            province_name: value.province_name,
            city_id: value.city_id,
            city_name: value.city_name,
            district_id: value.district_id,
            district_name: value.district_name,
            neighborhood_id: opt?.id || null,
            neighborhood_name: opt?.label || "",
            center_lat: opt?.lat ? Number(opt.lat) : value.center_lat,
            center_lng: opt?.lng ? Number(opt.lng) : value.center_lng,
          })
        }
      />
    </div>
  );
}
