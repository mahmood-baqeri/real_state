"use client";

import React from "react";
import Link from "next/link";
import { BedDouble, MapPin, Maximize2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { formatArea, formatMoney, formatNumberFa } from "@/lib/formatters";
import type { CurrencyCode, PublicSearchProperty } from "@/lib/types";

const FALLBACK_IMAGES = [
  "/images/prop-zafaranieh.jpg",
  "/images/prop-fereshteh.jpg",
  "/images/prop-office.jpg",
  "/images/prop-villa.jpg",
];

function pickImage(item: PublicSearchProperty, idx: number): string {
  if (item.cover_url) {
    if (item.cover_url.startsWith("/images/prop-") && item.cover_url.endsWith(".svg")) {
      return item.cover_url.replace(/\.svg$/, ".jpg");
    }
    return item.cover_url;
  }
  if (item.property_type_id === "OFFICE") return "/images/prop-office.jpg";
  if (item.property_type_id === "VILLA") return "/images/prop-villa.jpg";
  return FALLBACK_IMAGES[idx % FALLBACK_IMAGES.length];
}

export function PropertyCard({
  property,
  index = 0,
}: {
  property: PublicSearchProperty;
  index?: number;
}) {
  const { currencyMode } = useAuth();
  const displayCur: CurrencyCode =
    currencyMode === "IRR" || currencyMode === "IRT" ? currencyMode : property.currency_id;
  const isRental = property.deal_type_id === "MORTGAGE_RENT";

  return (
    <Link
      href={`/properties/${property.id}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white transition-colors hover:border-teal-600"
    >
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-slate-100">
        <img
          src={pickImage(property, index)}
          alt={property.title}
          onError={(e) => {
            const target = e.currentTarget;
            if (!target.dataset.fallbackApplied) {
              target.dataset.fallbackApplied = "1";
              target.src = FALLBACK_IMAGES[index % FALLBACK_IMAGES.length];
            }
          }}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
        />
        <div className="absolute top-3 right-3 flex items-center gap-1.5">
          <span className="rounded-md bg-slate-900/85 px-2.5 py-1 text-[11px] font-semibold text-white">
            {property.deal_type_name}
          </span>
          <span className="rounded-md bg-white/95 px-2.5 py-1 text-[11px] font-semibold text-slate-800">
            {property.property_type_name}
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col justify-between p-4">
        <div>
          <div className="mb-1 flex items-center justify-between gap-2 text-xs text-slate-500">
            <span className="flex items-center gap-1 truncate">
              <MapPin className="h-3.5 w-3.5 shrink-0 text-teal-700" />
              {property.city}
              {property.district ? `، ${property.district}` : ""}
            </span>
            <span className="font-mono text-[11px] text-slate-400">{property.property_code}</span>
          </div>

          <h3 className="line-clamp-1 text-sm font-bold text-slate-900 group-hover:text-teal-800">
            {property.title}
          </h3>

          <div className="mt-3 flex items-center gap-4 border-t border-slate-100 pt-3 text-xs text-slate-600">
            <span className="flex items-center gap-1 tabular-nums">
              <Maximize2 className="h-3.5 w-3.5 text-slate-400" />
              {formatArea(property.built_area_sqm)}
            </span>
            <span className="flex items-center gap-1 tabular-nums">
              <BedDouble className="h-3.5 w-3.5 text-slate-400" />
              {formatNumberFa(property.bedrooms)} خواب
            </span>
          </div>
        </div>

        <div className="mt-4 border-t border-slate-100 pt-3">
          {isRental ? (
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">ودیعه / رهن:</span>
                <span className="tabular-nums font-bold text-slate-900">
                  {formatMoney(property.deposit_amount, property.currency_id, displayCur)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">اجاره ماهانه:</span>
                <span className="tabular-nums font-semibold text-teal-800">
                  {formatMoney(property.rent_amount, property.currency_id, displayCur)}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">قیمت کل:</span>
              <span className="tabular-nums text-sm font-bold text-teal-800">
                {formatMoney(property.total_price, property.currency_id, displayCur)}
              </span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
