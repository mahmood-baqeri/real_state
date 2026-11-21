"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Bath,
  BedDouble,
  Building2,
  Calendar,
  Check,
  Flag,
  History,
  MapPin,
  Maximize2,
  Shield,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatArea, formatMoney, formatNumberFa } from "@/lib/formatters";
import type { PropertyItem, PropertyTimelineEvent } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { PropertyGalleryLightbox } from "@/components/ui/PropertyGalleryLightbox";
import { InteractiveMap } from "@/components/ui/InteractiveMap";
import { TrendLineChart } from "@/components/ui/AnalyticsCharts";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";
import { JsonLd } from "@/components/seo/JsonLd";
import { buildResidenceJsonLd } from "@/lib/seo";

export default function PropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user, accessToken, activeAgencyId, currencyMode } = useAuth();
  const [visitStart, setVisitStart] = useState("2026-12-01T10:00");
  const [visitNotes, setVisitNotes] = useState("");
  const [bookingMsg, setBookingMsg] = useState<string | null>(null);
  const [bookingErr, setBookingErr] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [violationOpen, setViolationOpen] = useState(false);
  const [violationReason, setViolationReason] = useState("FAKE_PRICE");
  const [violationDetails, setViolationDetails] = useState("");
  const [violationMsg, setViolationMsg] = useState<string | null>(null);
  const [violationErr, setViolationErr] = useState<string | null>(null);
  const [violationSubmitting, setViolationSubmitting] = useState(false);

  const {
    data: property,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["property-detail", params.id, accessToken],
    queryFn: async () => {
      const env = await apiFetch<PropertyItem>(`/api/v1/properties/${params.id}`, {
        token: accessToken,
        agencyId: activeAgencyId,
      });
      return env.data;
    },
  });

  const timelineQ = useQuery({
    queryKey: ["property-timeline", params.id, accessToken],
    enabled: !!property,
    queryFn: async () =>
      (
        await apiFetch<PropertyTimelineEvent[]>(`/api/v1/properties/${params.id}/timeline`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const handleBookViewing = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken) {
      router.push("/login");
      return;
    }
    setSubmitting(true);
    setBookingErr(null);
    setBookingMsg(null);
    try {
      const startDt = new Date(visitStart);
      const endDt = new Date(startDt.getTime() + 60 * 60 * 1000);
      await apiFetch("/api/v1/appointments/request-public", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          property_id: params.id,
          scheduled_start: startDt.toISOString(),
          scheduled_end: endDt.toISOString(),
          notes: visitNotes,
        }),
      });
      setBookingMsg("درخواست بازدید شما با موفقیت ثبت و به مشاور مسئول ارسال شد.");
      setVisitNotes("");
    } catch (err) {
      setBookingErr(err instanceof Error ? err.message : "خطا در ثبت درخواست بازدید");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReportViolation = async (e: React.FormEvent) => {
    e.preventDefault();
    setViolationSubmitting(true);
    setViolationErr(null);
    setViolationMsg(null);
    try {
      await apiFetch(`/api/v1/properties/${params.id}/violations`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          reason_type: violationReason,
          details: violationDetails.trim(),
        }),
      });
      setViolationMsg("گزارش تخلف ثبت شد و به صف تیم بازرسی بنیان ملک ارسال گردید.");
      setViolationDetails("");
      setViolationOpen(false);
    } catch (err) {
      setViolationErr(err instanceof Error ? err.message : "خطا در ثبت گزارش تخلف");
    } finally {
      setViolationSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      {property && <JsonLd data={buildResidenceJsonLd(property)} />}
      <PublicHeader />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={() => router.back()}
          className="mb-5 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-teal-700 dark:text-slate-400 dark:hover:text-teal-400"
        >
          <ArrowRight className="h-4 w-4" />
          بازگشت به فهرست املاک
        </button>

        {isLoading ? (
          <LoadingState />
        ) : error || !property ? (
          <ErrorState
            message={error instanceof Error ? error.message : "ملک مورد نظر یافت نشد"}
            onRetry={() => refetch()}
          />
        ) : (
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
            {/* Main Details */}
            <div className="space-y-6 lg:col-span-8">
              <PropertyGalleryLightbox
                title={property.title}
                mediaItems={property.media_items || []}
              />

              <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4 dark:border-slate-800">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-semibold text-teal-700 dark:text-teal-400">
                      {property.deal_type.name_fa} · {property.property_type.name_fa}
                    </span>
                    <span className="font-mono text-slate-500 dark:text-slate-400">
                      ({property.property_code})
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                    <Building2 className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    {property.agency_name}
                  </div>
                </div>

                <h1 className="mt-4 text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {property.title}
                </h1>
                {property.location && (
                  <p className="mt-2 flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-300">
                    <MapPin className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    {property.location.province}، {property.location.city}
                    {property.location.district ? ` — منطقه ${property.location.district}` : ""}
                    {property.location.neighborhood ? ` (${property.location.neighborhood})` : ""}
                  </p>
                )}

                <div className="mt-6 grid grid-cols-2 gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/60 sm:grid-cols-4">
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">زیربنا</div>
                    <div className="mt-1 flex items-center gap-1.5 text-sm font-bold text-slate-900 tabular-nums dark:text-slate-100">
                      <Maximize2 className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      {formatArea(property.built_area_sqm)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">اتاق خواب</div>
                    <div className="mt-1 flex items-center gap-1.5 text-sm font-bold text-slate-900 tabular-nums dark:text-slate-100">
                      <BedDouble className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      {formatNumberFa(property.bedrooms)} خواب
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">سرویس</div>
                    <div className="mt-1 flex items-center gap-1.5 text-sm font-bold text-slate-900 tabular-nums dark:text-slate-100">
                      <Bath className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      {formatNumberFa(property.bathrooms)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">سند</div>
                    <div className="mt-1 text-sm font-bold text-slate-900 dark:text-slate-100">
                      {property.deed_type}
                    </div>
                  </div>
                </div>

                {property.description && (
                  <div className="mt-6">
                    <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      توضیحات ملک
                    </h2>
                    <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                      {property.description}
                    </p>
                  </div>
                )}

                {property.amenities && property.amenities.length > 0 && (
                  <div className="mt-6 border-t border-slate-100 pt-5 dark:border-slate-800 space-y-3">
                    <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      امکانات و تجهیزات دسته‌بندی‌شده
                    </h2>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {Array.from(
                        property.amenities.reduce((acc, am) => {
                          const cat = am.category_name_fa || "سایر امکانات";
                          const list = acc.get(cat) || [];
                          list.push(am);
                          acc.set(cat, list);
                          return acc;
                        }, new Map<string, typeof property.amenities>())
                      ).map(([catName, list]) => (
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
                                <div
                                  key={am.code}
                                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                >
                                  <Check className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                                  <span>{am.name_fa}</span>
                                  {extraVal && (
                                    <span className="font-mono text-[11px] font-bold text-teal-700 dark:text-teal-300">
                                      ({extraVal})
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {property.location?.latitude && property.location?.longitude && (
                <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                      <MapPin className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      موقعیت مکانی روی نقشه
                    </h2>
                    {property.location.hide_exact_address && (
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        نمایش محدوده تقریبی جهت حفظ حریم خصوصی
                      </span>
                    )}
                  </div>
                  <InteractiveMap
                    center={[Number(property.location.latitude), Number(property.location.longitude)]}
                    zoom={14}
                    heightClass="h-[280px]"
                    markers={[
                      {
                        id: property.id,
                        title: property.title,
                        subtitle: `${property.location.city}${
                          property.location.district ? `، ${property.location.district}` : ""
                        }`,
                        coverUrl: property.media_items?.[0]?.url || null,
                        priceText: property.deal_type.is_rental
                          ? `رهن ${formatMoney(property.deposit_amount, property.currency, currencyMode)}`
                          : formatMoney(property.total_price, property.currency, currencyMode),
                        lat: Number(property.location.latitude),
                        lng: Number(property.location.longitude),
                        hideExactAddress: property.location.hide_exact_address,
                      },
                    ]}
                  />
                </div>
              )}

              {property.price_history && property.price_history.length > 0 && (
                <TrendLineChart
                  title="تاریخچه تغییرات قیمت ملک"
                  subtitle="روند به‌روزرسانی قیمت ثبت‌شده در سیستم"
                  primaryLabel="قیمت ثبت‌شده"
                  valueFormatter={(v) => formatMoney(v, property.currency, currencyMode)}
                  points={property.price_history.map((ph, idx) => ({
                    label: `#${formatNumberFa(idx + 1)}`,
                    primary: Number(ph.new_price) || 0,
                  }))}
                />
              )}

              {timelineQ.data && timelineQ.data.length > 0 && (
                <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                  <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                    <History className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    خط زمانی وضعیت و رویدادهای ملک
                  </h2>
                  <div className="space-y-3 border-r-2 border-slate-200 pr-4 dark:border-slate-800">
                    {timelineQ.data.map((ev) => (
                      <div key={ev.id} className="space-y-0.5 text-xs">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-slate-900 dark:text-slate-100">
                            {ev.title}
                          </span>
                          <DateDisplay
                            value={ev.occurred_at}
                            className="text-[11px] text-slate-500 dark:text-slate-400"
                          />
                        </div>
                        {ev.detail && (
                          <p className="text-slate-600 dark:text-slate-400">{ev.detail}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {property.related_properties && property.related_properties.length > 0 && (
                <div className="space-y-4">
                  <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    فایل‌های مشابه پیشنهادی
                  </h2>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {property.related_properties.map((rp, idx) => (
                      <PropertyCard key={rp.id} property={rp} index={idx} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar Pricing & Viewing Booking */}
            <div className="space-y-6 lg:col-span-4">
              <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  شرایط مالی
                </div>
                {property.deal_type.is_rental ? (
                  <div className="mt-3 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2 dark:border-slate-800">
                      <span className="text-sm text-slate-600 dark:text-slate-400">ودیعه / رهن</span>
                      <span className="tabular-nums text-lg font-bold text-slate-900 dark:text-slate-100">
                        {formatMoney(property.deposit_amount, property.currency, currencyMode)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-600 dark:text-slate-400">اجاره ماهانه</span>
                      <span className="tabular-nums text-lg font-bold text-teal-800 dark:text-teal-300">
                        {formatMoney(property.rent_amount, property.currency, currencyMode)}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="mt-2 space-y-2">
                    <div className="tabular-nums text-2xl font-bold text-teal-800 dark:text-teal-300">
                      {formatMoney(property.total_price, property.currency, currencyMode)}
                    </div>
                    {Number(property.price_per_sqm) > 0 && (
                      <div className="tabular-nums text-xs text-slate-500 dark:text-slate-400">
                        متری {formatMoney(property.price_per_sqm, property.currency, currencyMode)}
                      </div>
                    )}
                  </div>
                )}

                {property.location?.hide_exact_address && (
                  <div className="mt-4 flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-300">
                    <Shield className="mt-0.5 h-4 w-4 shrink-0 text-teal-700 dark:text-teal-400" />
                    نشانی دقیق و اطلاعات مالک مطابق سیاست حریم خصوصی، پس از ثبت درخواست بازدید
                    ارائه می‌شود.
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <Calendar className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  درخواست زمان بازدید حضوری
                </h2>
                <form onSubmit={handleBookViewing} className="mt-4 space-y-3">
                  {bookingMsg && <SuccessBanner message={bookingMsg} />}
                  {bookingErr && <ErrorState message={bookingErr} />}

                  <div>
                    <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      تاریخ و ساعت پیشنهادی
                    </label>
                    <input
                      type="datetime-local"
                      value={visitStart}
                      onChange={(e) => setVisitStart(e.target.value)}
                      required
                      className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      توضیحات
                    </label>
                    <textarea
                      rows={3}
                      value={visitNotes}
                      onChange={(e) => setVisitNotes(e.target.value)}
                      placeholder="شماره تماس یا بازه زمانی ترجیحی..."
                      className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
                  >
                    {user
                      ? submitting
                        ? "در حال ارسال..."
                        : "ثبت درخواست بازدید"
                      : "ورود و ثبت درخواست بازدید"}
                  </button>
                </form>
              </div>

              {/* Public Violation Report Box */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                <button
                  type="button"
                  onClick={() => setViolationOpen((v) => !v)}
                  className="flex w-full items-center justify-between text-xs font-semibold text-rose-700 hover:text-rose-800 dark:text-rose-400"
                >
                  <span className="inline-flex items-center gap-1.5">
                    <Flag className="h-3.5 w-3.5" />
                    گزارش تخلف یا مغایرت آگهی
                  </span>
                  <span>{violationOpen ? "بستن" : "ثبت گزارش"}</span>
                </button>

                {violationMsg && <SuccessBanner message={violationMsg} />}
                {violationErr && <ErrorState message={violationErr} />}

                {violationOpen && (
                  <form onSubmit={handleReportViolation} className="space-y-2.5 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <select
                      value={violationReason}
                      onChange={(e) => setViolationReason(e.target.value)}
                      className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                    >
                      <option value="FAKE_PRICE">قیمت غیرواقعی / صوری</option>
                      <option value="DUPLICATE_LISTING">آگهی تکراری</option>
                      <option value="MISLEADING_INFO">اطلاعات گمراه‌کننده</option>
                      <option value="UNAVAILABLE_PROPERTY">ملک واگذار شده / ناموجود</option>
                      <option value="OTHER">سایر موارد</option>
                    </select>
                    <textarea
                      required
                      rows={3}
                      value={violationDetails}
                      onChange={(e) => setViolationDetails(e.target.value)}
                      placeholder="توضیحات دقیق مغایرت یا تخلف را بنویسید..."
                      className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                    />
                    <button
                      type="submit"
                      disabled={violationSubmitting}
                      className="h-9 w-full rounded-lg bg-rose-700 text-xs font-semibold text-white hover:bg-rose-800 disabled:opacity-50"
                    >
                      {violationSubmitting ? "در حال ارسال..." : "ارسال به تیم بازرسی"}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
