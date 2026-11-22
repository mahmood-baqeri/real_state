"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Box, Compass, ExternalLink, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { PropertyItem, VirtualTourDetail } from "@/lib/types";
import { StatusText } from "@/components/ui/StatusText";

interface PropertyVirtualTourCardProps {
  property: PropertyItem;
  onCreated?: () => void;
}

export function PropertyVirtualTourCard({ property, onCreated }: PropertyVirtualTourCardProps) {
  const router = useRouter();
  const { accessToken, activeAgencyId } = useAuth();
  const [creating, setCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSetupTour = async () => {
    setCreating(true);
    setErrorMsg(null);
    try {
      await apiFetch<VirtualTourDetail>(`/api/v1/properties/${property.id}/virtual-tour`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          title: `تور مجازی ${property.title}`,
          create_default_floor: true,
        }),
      });
      onCreated?.();
      router.push(`/dashboard/properties/${property.id}/virtual-tour`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "خطا در راه‌اندازی تور مجازی");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2.5 dark:border-slate-800">
        <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-900 dark:text-slate-100">
          <Compass className="h-4 w-4 text-teal-700 dark:text-teal-400" />
          تور مجازی ۳۶۰° و مدل سه‌بعدی
        </h3>
        {property.virtual_tour_status && <StatusText status={property.virtual_tour_status} />}
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
          {errorMsg}
        </div>
      )}

      {property.virtual_tour_id ? (
        <div className="space-y-2.5 text-xs">
          <p className="text-slate-600 dark:text-slate-400">
            مدیریت طبقات، اتاق‌ها، عکاسی ۳۶۰ درجه با گوشی، نقاط تعاملی و انتشار تور برای این ملک فعال است.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/dashboard/properties/${property.id}/virtual-tour`}
              className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Box className="h-3.5 w-3.5" />
              ورود به استودیوی تور مجازی
            </Link>
            {property.virtual_tour_status === "published" && property.status === "PUBLISHED" && (
              <Link
                href={`/properties/${property.id}#virtual-tour`}
                className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-300 px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                مشاهده عمومی
              </Link>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-2.5 text-xs">
          <p className="text-slate-600 dark:text-slate-400">
            هنوز تور مجازی برای این ملک ایجاد نشده است. با دوربین موبایل یا تصاویر ۳۶۰° یک تور حرفه‌ای بسازید.
          </p>
          <button
            type="button"
            disabled={creating}
            onClick={handleSetupTour}
            className="inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            <Plus className="h-3.5 w-3.5" />
            {creating ? "در حال ایجاد..." : "راه‌اندازی تور مجازی ۳۶۰ درجه"}
          </button>
        </div>
      )}
    </div>
  );
}
