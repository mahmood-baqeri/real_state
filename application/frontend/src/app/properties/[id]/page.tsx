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
  MapPin,
  Maximize2,
  Shield,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatArea, formatMoney, formatNumberFa } from "@/lib/formatters";
import type { PropertyItem } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

export default function PropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user, accessToken, activeAgencyId, currencyMode } = useAuth();
  const [visitStart, setVisitStart] = useState("2026-12-01T10:00");
  const [visitNotes, setVisitNotes] = useState("");
  const [bookingMsg, setBookingMsg] = useState<string | null>(null);
  const [bookingErr, setBookingErr] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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

  return (
    <div className="min-h-screen bg-slate-50">
      <PublicHeader />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={() => router.back()}
          className="mb-5 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-teal-700"
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
              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                <img
                  src={property.media_items?.[0]?.url || "/images/prop-zafaranieh.jpg"}
                  alt={property.title}
                  className="aspect-[16/9] w-full object-cover"
                />
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-6">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="rounded-md bg-teal-50 px-2.5 py-1 font-semibold text-teal-800 border border-teal-200">
                      {property.deal_type.name_fa}
                    </span>
                    <span className="rounded-md bg-slate-100 px-2.5 py-1 font-semibold text-slate-700">
                      {property.property_type.name_fa}
                    </span>
                    <span className="font-mono text-slate-500">{property.property_code}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-600">
                    <Building2 className="h-4 w-4 text-teal-700" />
                    {property.agency_name}
                  </div>
                </div>

                <h1 className="mt-4 text-2xl font-bold text-slate-900">{property.title}</h1>
                {property.location && (
                  <p className="mt-2 flex items-center gap-1.5 text-sm text-slate-600">
                    <MapPin className="h-4 w-4 text-teal-700" />
                    {property.location.province}، {property.location.city}
                    {property.location.district ? ` — منطقه ${property.location.district}` : ""}
                    {property.location.neighborhood ? ` (${property.location.neighborhood})` : ""}
                  </p>
                )}

                <div className="mt-6 grid grid-cols-2 gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-4">
                  <div>
                    <div className="text-xs text-slate-500">زیربنا</div>
                    <div className="mt-1 flex items-center gap-1.5 text-sm font-bold text-slate-900 tabular-nums">
                      <Maximize2 className="h-4 w-4 text-teal-700" />
                      {formatArea(property.built_area_sqm)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">اتاق خواب</div>
                    <div className="mt-1 flex items-center gap-1.5 text-sm font-bold text-slate-900 tabular-nums">
                      <BedDouble className="h-4 w-4 text-teal-700" />
                      {formatNumberFa(property.bedrooms)} خواب
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">سرویس</div>
                    <div className="mt-1 flex items-center gap-1.5 text-sm font-bold text-slate-900 tabular-nums">
                      <Bath className="h-4 w-4 text-teal-700" />
                      {formatNumberFa(property.bathrooms)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">سند</div>
                    <div className="mt-1 text-sm font-bold text-slate-900">{property.deed_type}</div>
                  </div>
                </div>

                {property.description && (
                  <div className="mt-6">
                    <h2 className="text-sm font-bold text-slate-900">توضیحات ملک</h2>
                    <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-600">
                      {property.description}
                    </p>
                  </div>
                )}

                {property.amenities && property.amenities.length > 0 && (
                  <div className="mt-6 border-t border-slate-100 pt-5">
                    <h2 className="mb-3 text-sm font-bold text-slate-900">امکانات و تجهیزات</h2>
                    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                      {property.amenities.map((am) => (
                        <div
                          key={am.code}
                          className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-800"
                        >
                          <Check className="h-3.5 w-3.5 text-teal-700" />
                          {am.name_fa}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Sidebar Pricing & Viewing Booking */}
            <div className="space-y-6 lg:col-span-4">
              <div className="rounded-xl border border-slate-200 bg-white p-6">
                <div className="text-xs font-medium text-slate-500">شرایط مالی</div>
                {property.deal_type.is_rental ? (
                  <div className="mt-3 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <span className="text-sm text-slate-600">ودیعه / رهن</span>
                      <span className="tabular-nums text-lg font-bold text-slate-900">
                        {formatMoney(property.deposit_amount, property.currency, currencyMode)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-600">اجاره ماهانه</span>
                      <span className="tabular-nums text-lg font-bold text-teal-800">
                        {formatMoney(property.rent_amount, property.currency, currencyMode)}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="mt-2 space-y-2">
                    <div className="tabular-nums text-2xl font-bold text-teal-800">
                      {formatMoney(property.total_price, property.currency, currencyMode)}
                    </div>
                    {Number(property.price_per_sqm) > 0 && (
                      <div className="tabular-nums text-xs text-slate-500">
                        متری {formatMoney(property.price_per_sqm, property.currency, currencyMode)}
                      </div>
                    )}
                  </div>
                )}

                {property.location?.hide_exact_address && (
                  <div className="mt-4 flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                    <Shield className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
                    نشانی دقیق و اطلاعات مالک مطابق سیاست حریم خصوصی، پس از ثبت درخواست بازدید ارائه می‌شود.
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-6">
                <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                  <Calendar className="h-4 w-4 text-teal-700" />
                  درخواست زمان بازدید حضوری
                </h2>
                <form onSubmit={handleBookViewing} className="mt-4 space-y-3">
                  {bookingMsg && <SuccessBanner message={bookingMsg} />}
                  {bookingErr && <ErrorState message={bookingErr} />}

                  <div>
                    <label className="mb-1 block text-xs font-semibold text-slate-700">
                      تاریخ و ساعت پیشنهادی
                    </label>
                    <input
                      type="datetime-local"
                      value={visitStart}
                      onChange={(e) => setVisitStart(e.target.value)}
                      required
                      className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-semibold text-slate-700">توضیحات</label>
                    <textarea
                      rows={3}
                      value={visitNotes}
                      onChange={(e) => setVisitNotes(e.target.value)}
                      placeholder="شماره تماس یا بازه زمانی ترجیحی..."
                      className="w-full rounded-lg border border-slate-300 p-2.5 text-sm focus:border-teal-600 focus:outline-none"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                  >
                    {user
                      ? submitting
                        ? "در حال ارسال..."
                        : "ثبت درخواست بازدید"
                      : "ورود و ثبت درخواست بازدید"}
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
