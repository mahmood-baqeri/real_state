"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Bath,
  BedDouble,
  Check,
  Edit3,
  ExternalLink,
  MapPin,
  Maximize2,
  Star,
  Trash2,
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
import { PropertyGalleryLightbox } from "@/components/ui/PropertyGalleryLightbox";
import { SecureFileUploader, type QueuedUploadFile } from "@/components/ui/SecureFileUploader";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

export default function DashboardPropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { accessToken, activeAgencyId, effectiveRole, hasPermission } = useAuth();
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [uploadQueue, setUploadQueue] = useState<QueuedUploadFile[]>([]);

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

  const uploadSingleMedia = async (item: QueuedUploadFile) => {
    setUploadQueue((prev) =>
      prev.map((q) => (q.id === item.id ? { ...q, status: "UPLOADING", progress: 45, error: undefined } : q))
    );
    try {
      const form = new FormData();
      form.append("file", item.file);
      form.append("title", item.title || item.file.name);
      form.append("is_cover", item.isCover ? "true" : "false");
      form.append("is_public", "true");
      await apiFetch(`/api/v1/properties/${params.id}/media/upload`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: form,
      });
      setUploadQueue((prev) =>
        prev.map((q) => (q.id === item.id ? { ...q, status: "DONE", progress: 100 } : q))
      );
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "خطا در آپلود";
      setUploadQueue((prev) =>
        prev.map((q) => (q.id === item.id ? { ...q, status: "ERROR", error: msg } : q))
      );
      setErrMsg(msg);
    }
  };

  const handleUploadAll = async () => {
    setErrMsg(null);
    const pending = uploadQueue.filter((q) => q.status === "READY" || q.status === "ERROR");
    for (const item of pending) {
      await uploadSingleMedia(item);
    }
    setNotice("تصاویر انتخاب‌شده با موفقیت در گالری ملک ذخیره شدند.");
  };

  const reorderMut = useMutation({
    mutationFn: async ({ orderedIds, coverId }: { orderedIds: string[]; coverId?: string }) =>
      apiFetch(`/api/v1/properties/${params.id}/media/reorder`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          ordered_media_ids: orderedIds,
          cover_media_id: coverId || null,
        }),
      }),
    onSuccess: () => {
      setNotice("ترتیب تصاویر و کاور اصلی ملک به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteMediaMut = useMutation({
    mutationFn: async (mediaId: string) =>
      apiFetch(`/api/v1/properties/${params.id}/media/${mediaId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setNotice("تصویر از گالری ملک حذف شد.");
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const property = propQ.data;
  const canPublish =
    effectiveRole === "SUPER_ADMIN" ||
    effectiveRole === "AGENCY_MANAGER" ||
    hasPermission("property.publish");

  const groupedAmenities = useMemo(() => {
    if (!property?.amenities?.length) return [];
    const map = new Map<string, typeof property.amenities>();
    for (const am of property.amenities) {
      const grp = am.category_name_fa || "سایر امکانات";
      const list = map.get(grp) || [];
      list.push(am);
      map.set(grp, list);
    }
    return Array.from(map.entries());
  }, [property?.amenities]);

  const moveMedia = (idx: number, dir: -1 | 1) => {
    if (!property?.media_items) return;
    const list = [...property.media_items];
    const target = idx + dir;
    if (target < 0 || target >= list.length) return;
    const [moved] = list.splice(idx, 1);
    list.splice(target, 0, moved);
    reorderMut.mutate({ orderedIds: list.map((m) => m.id) });
  };

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
            <PropertyGalleryLightbox
              title={property.title}
              mediaItems={property.media_items || []}
            />

            {/* Existing Gallery Reorder & Cover Manager */}
            {property.media_items && property.media_items.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                  مدیریت ترتیب و تصویر کاور گالری
                </h3>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {property.media_items.map((m, idx) => (
                    <div
                      key={m.id}
                      className={`overflow-hidden rounded-lg border p-1.5 text-[11px] ${
                        m.is_cover
                          ? "border-amber-500 bg-amber-50/40 dark:border-amber-500 dark:bg-amber-950/20"
                          : "border-slate-200 dark:border-slate-800"
                      }`}
                    >
                      <img
                        src={m.url}
                        alt={m.title || property.title}
                        className="aspect-[16/10] w-full rounded object-cover"
                      />
                      <div className="mt-1.5 flex items-center justify-between gap-1">
                        <button
                          type="button"
                          onClick={() =>
                            reorderMut.mutate({
                              orderedIds: property.media_items.map((x) => x.id),
                              coverId: m.id,
                            })
                          }
                          className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-semibold ${
                            m.is_cover
                              ? "bg-amber-500 text-white"
                              : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                          }`}
                        >
                          <Star className="h-2.5 w-2.5" />
                          {m.is_cover ? "کاور" : "کاور کن"}
                        </button>
                        <div className="flex items-center gap-0.5">
                          <button
                            type="button"
                            disabled={idx === 0}
                            onClick={() => moveMedia(idx, -1)}
                            className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:hover:bg-slate-800"
                          >
                            <ArrowRight className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            disabled={idx === property.media_items.length - 1}
                            onClick={() => moveMedia(idx, 1)}
                            className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:hover:bg-slate-800"
                          >
                            <ArrowLeft className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteMediaMut.mutate(m.id)}
                            className="rounded p-1 text-rose-600 hover:bg-rose-50 dark:text-rose-400"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Secure Multi-File Uploader with Live Pre-Upload Preview */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                آپلود تصاویر جدید با پیش‌نمایش و بزرگنمایی قبل از ارسال
              </h3>
              <SecureFileUploader
                accept="image/jpeg,image/png,image/webp"
                allowedExtensions={["jpg", "jpeg", "png", "webp"]}
                multiple
                allowCoverSelect
                queue={uploadQueue}
                onQueueChange={setUploadQueue}
                onUploadSingle={uploadSingleMedia}
                onUploadAll={handleUploadAll}
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

              {groupedAmenities.length > 0 && (
                <div className="mt-5 border-t border-slate-100 pt-4 dark:border-slate-800 space-y-3">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    امکانات و تجهیزات دسته‌بندی‌شده
                  </h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {groupedAmenities.map(([catName, list]) => (
                      <div
                        key={catName}
                        className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-slate-800/40"
                      >
                        <div className="mb-2 text-xs font-bold text-teal-700 dark:text-teal-400">
                          {catName}
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {list.map((am) => {
                            const extraVal = am.value_number
                              ? `${formatNumberFa(am.value_number)} ${am.unit_label || ""}`.trim()
                              : am.value_text;
                            return (
                              <span
                                key={am.code}
                                className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium dark:border-slate-700 dark:bg-slate-900"
                              >
                                <Check className="h-3 w-3 text-teal-700 dark:text-teal-400" />
                                <span>{am.name_fa}</span>
                                {extraVal && (
                                  <span className="font-mono text-[11px] font-bold text-teal-700 dark:text-teal-300">
                                    ({extraVal})
                                  </span>
                                )}
                              </span>
                            );
                          })}
                        </div>
                      </div>
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
