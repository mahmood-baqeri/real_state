// Path: frontend/src/app/dashboard/properties/[id]/page.tsx

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bath,
  BedDouble,
  Check,
  Edit3,
  ExternalLink,
  MapPin,
  Maximize2,
  UserCheck,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatArea, formatNumberFa } from "@/lib/formatters";
import type { PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

export default function DashboardPropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { accessToken, activeAgencyId, effectiveRole, hasPermission } = useAuth();
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const propQ = useQuery({
    queryKey: ["dashboard-property-detail", params.id, activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<PropertyItem>(`/api/v1/properties/${params.id}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const actionMut = useMutation({
    mutationFn: async (action: "submit" | "publish") =>
      apiFetch(`/api/v1/properties/${params.id}/${action}`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setNotice("وضعیت ملک با موفقیت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const property = propQ.data;
  const canPublish =
    effectiveRole === "SUPER_ADMIN" ||
    effectiveRole === "AGENCY_MANAGER" ||
    hasPermission("property.publish");

  return (
    <div className="space-y-6">
      <PageHeader
        title={property ? `${property.title}` : "جزئیات فایل ملکی"}
        subtitle={
          property ? `کد ملک: ${property.property_code} — ${property.agency_name}` : undefined
        }
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "فهرست املاک", href: "/dashboard/properties" },
          { label: property?.property_code || "جزئیات" },
        ]}
        actions={
          property ? (
            <div className="flex flex-wrap gap-2">
              <Link
                href={`/dashboard/properties/${property.id}/edit`}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                <Edit3 className="h-3.5 w-3.5" />
                ویرایش مشخصات
              </Link>
              {property.status === "DRAFT" && (
                <button
                  type="button"
                  onClick={() => actionMut.mutate("submit")}
                  className="h-9 rounded-lg bg-amber-600 px-3.5 text-xs font-semibold text-white hover:bg-amber-700"
                >
                  ارسال برای تأیید
                </button>
              )}
              {property.status !== "PUBLISHED" && canPublish && (
                <button
                  type="button"
                  onClick={() => actionMut.mutate("publish")}
                  className="h-9 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
                >
                  انتشار در پورتال
                </button>
              )}
              <Link
                href={`/properties/${property.id}`}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                نمای عمومی
              </Link>
            </div>
          ) : null
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {propQ.isLoading ? (
        <LoadingState />
      ) : propQ.error instanceof Error ? (
        <ErrorState message={propQ.error.message} onRetry={() => propQ.refetch()} />
      ) : property ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-8">
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <img
                src={property.media_items?.[0]?.url || "/images/prop-zafaranieh.jpg"}
                alt={property.title}
                className="aspect-[16/9] w-full object-cover"
              />
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4 dark:border-slate-800">
                <div className="flex items-center gap-2 text-xs">
                  <StatusText status={property.status} />
                  <span className="font-semibold text-teal-700 dark:text-teal-400">
                    {property.deal_type.name_fa} · {property.property_type.name_fa}
                  </span>
                </div>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  ثبت‌شده در <DateDisplay value={property.created_at} />
                </span>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/60 sm:grid-cols-4">
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">زیربنا</div>
                  <div className="mt-1 flex items-center gap-1.5 text-sm font-bold tabular-nums">
                    <Maximize2 className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    {formatArea(property.built_area_sqm)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">خواب</div>
                  <div className="mt-1 flex items-center gap-1.5 text-sm font-bold tabular-nums">
                    <BedDouble className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    {formatNumberFa(property.bedrooms)} خواب
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">سرویس</div>
                  <div className="mt-1 flex items-center gap-1.5 text-sm font-bold tabular-nums">
                    <Bath className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    {formatNumberFa(property.bathrooms)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">سند</div>
                  <div className="mt-1 text-sm font-bold">{property.deed_type}</div>
                </div>
              </div>

              {property.location && (
                <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-800/60">
                  <div className="flex items-center gap-1.5 font-bold text-slate-900 dark:text-slate-100">
                    <MapPin className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    موقعیت مکانی و آدرس داخلی
                  </div>
                  <p className="mt-1.5 text-slate-600 dark:text-slate-300">
                    {property.location.province}، {property.location.city}
                    {property.location.district ? ` — منطقه ${property.location.district}` : ""}
                    {property.location.neighborhood ? ` (${property.location.neighborhood})` : ""}
                  </p>
                  {property.location.full_address && (
                    <p className="mt-1 font-medium text-slate-800 dark:text-slate-200">
                      نشانی دقیق: {property.location.full_address}
                    </p>
                  )}
                </div>
              )}

              {property.description && (
                <div className="mt-5">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">توضیحات</h3>
                  <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                    {property.description}
                  </p>
                </div>
              )}

              {property.amenities && property.amenities.length > 0 && (
                <div className="mt-5 border-t border-slate-100 pt-4 dark:border-slate-800">
                  <h3 className="mb-3 text-sm font-bold text-slate-900 dark:text-slate-100">
                    امکانات
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {property.amenities.map((am) => (
                      <span
                        key={am.code}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium dark:border-slate-700 dark:bg-slate-800"
                      >
                        <Check className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                        {am.name_fa}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6 lg:col-span-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                ارزش‌گذاری و شرایط مالی
              </h3>
              <div className="mt-3">
                {property.deal_type.is_rental ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>ودیعه:</span>
                      <MoneyDisplay
                        amount={property.deposit_amount}
                        sourceCurrency={property.currency}
                        className="font-bold"
                      />
                    </div>
                    <div className="flex justify-between">
                      <span>اجاره ماهانه:</span>
                      <MoneyDisplay
                        amount={property.rent_amount}
                        sourceCurrency={property.currency}
                        className="font-bold text-teal-700 dark:text-teal-300"
                      />
                    </div>
                  </div>
                ) : (
                  <MoneyDisplay
                    amount={property.total_price}
                    sourceCurrency={property.currency}
                    className="text-xl font-bold text-teal-800 dark:text-teal-300"
                  />
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <UserCheck className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                مشاوران و مالکین مرتبط
              </h3>
              <div className="space-y-3 text-xs">
                <div>
                  <div className="mb-1 text-slate-500 dark:text-slate-400">مشاوران مسئول:</div>
                  {property.assigned_agents && property.assigned_agents.length > 0 ? (
                    property.assigned_agents.map((a) => (
                      <div key={a.membership_id} className="font-semibold">
                        {a.full_name} ({a.role})
                      </div>
                    ))
                  ) : (
                    <span className="text-slate-400">تخصیص نیافته</span>
                  )}
                </div>
                <div className="border-t border-slate-100 pt-2 dark:border-slate-800">
                  <div className="mb-1 text-slate-500 dark:text-slate-400">مالکین (مطابق سیاست دسترسی):</div>
                  {property.owners && property.owners.length > 0 ? (
                    property.owners.map((o) => (
                      <div key={o.id} className="flex justify-between py-1">
                        <span className="font-semibold">{o.full_name}</span>
                        <span className="font-mono text-slate-500">{o.phone_number || "محفوظ"}</span>
                      </div>
                    ))
                  ) : (
                    <span className="text-slate-400">مخفی یا ثبت‌نشده</span>
                  )}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => router.push("/dashboard/properties")}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              بازگشت به فهرست املاک
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
