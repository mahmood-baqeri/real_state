"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { PropertyCatalog, PropertyItem } from "@/lib/types";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

const propertySchema = z.object({
  property_code: z.string().min(2, "کد ملک الزامی است"),
  title: z.string().min(3, "عنوان ملک حداقل ۳ کاراکتر باشد"),
  description: z.string().optional().default(""),
  property_type_id: z.string().min(1, "نوع ملک را انتخاب کنید"),
  deal_type_id: z.string().min(1, "نوع معامله را انتخاب کنید"),
  usage_type: z.string().default("مسکونی"),
  visibility: z.string().default("PUBLIC_PORTAL"),
  is_featured: z.boolean().default(false),
  is_negotiable: z.boolean().default(true),
  is_exclusive: z.boolean().default(false),
  land_area_sqm: z.coerce.number().min(0).default(0),
  built_area_sqm: z.coerce.number().min(1, "متراژ بنا الزامی است"),
  bedrooms: z.coerce.number().int().min(0).default(0),
  bathrooms: z.coerce.number().int().min(0).default(1),
  floor_number: z.coerce.number().int().optional(),
  total_floors: z.coerce.number().int().optional(),
  building_age: z.coerce.number().int().min(0).optional(),
  deed_type: z.string().default("تک‌برگ"),
  currency_id: z.string().default("IRT"),
  total_price: z.coerce.number().min(0).default(0),
  deposit_amount: z.coerce.number().min(0).default(0),
  rent_amount: z.coerce.number().min(0).default(0),
  initial_media_url: z.string().optional().default("/images/prop-zafaranieh.jpg"),
  city: z.string().min(2, "نام شهر الزامی است"),
  province: z.string().default("تهران"),
  district: z.string().default(""),
  neighborhood: z.string().default(""),
  full_address: z.string().default(""),
  hide_exact_address: z.boolean().default(true),
  amenity_codes: z.array(z.string()).default([]),
});

type PropertyFormValues = z.infer<typeof propertySchema>;

export function PropertyForm({
  propertyId,
  initialData,
}: {
  propertyId?: string;
  initialData?: PropertyItem;
}) {
  const router = useRouter();
  const { accessToken, activeAgencyId } = useAuth();
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [savedOk, setSavedOk] = React.useState(false);

  const { data: catalog, isLoading: loadingCatalog } = useQuery({
    queryKey: ["property-catalog"],
    queryFn: async () => (await apiFetch<PropertyCatalog>("/api/v1/properties/catalog")).data,
  });

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PropertyFormValues>({
    resolver: zodResolver(propertySchema),
    defaultValues: {
      property_code: `PN-${Math.floor(1000 + Math.random() * 9000)}`,
      title: "",
      description: "",
      property_type_id: "APARTMENT",
      deal_type_id: "SALE",
      usage_type: "مسکونی",
      visibility: "PUBLIC_PORTAL",
      is_featured: false,
      is_negotiable: true,
      is_exclusive: false,
      land_area_sqm: 0,
      built_area_sqm: 120,
      bedrooms: 2,
      bathrooms: 2,
      deed_type: "تک‌برگ",
      currency_id: "IRT",
      total_price: 15000000000,
      deposit_amount: 0,
      rent_amount: 0,
      initial_media_url: "/images/prop-zafaranieh.jpg",
      city: "تهران",
      province: "تهران",
      district: "",
      neighborhood: "",
      full_address: "",
      hide_exact_address: true,
      amenity_codes: [],
    },
  });

  useEffect(() => {
    if (initialData) {
      reset({
        property_code: initialData.property_code,
        title: initialData.title,
        description: initialData.description || "",
        property_type_id: initialData.property_type?.code || initialData.property_type_id || "APARTMENT",
        deal_type_id: initialData.deal_type?.code || initialData.deal_type_id || "SALE",
        usage_type: initialData.usage_type || "مسکونی",
        visibility: initialData.visibility || "PUBLIC_PORTAL",
        is_featured: initialData.is_featured,
        is_negotiable: initialData.is_negotiable,
        is_exclusive: Boolean(initialData.is_exclusive),
        land_area_sqm: Number(initialData.land_area_sqm || 0),
        built_area_sqm: Number(initialData.built_area_sqm || 0),
        bedrooms: initialData.bedrooms,
        bathrooms: initialData.bathrooms,
        floor_number: initialData.floor_number ?? undefined,
        total_floors: initialData.total_floors ?? undefined,
        building_age: initialData.building_age ?? undefined,
        deed_type: initialData.deed_type || "تک‌برگ",
        currency_id: initialData.currency || "IRT",
        total_price: Number(initialData.total_price || 0),
        deposit_amount: Number(initialData.deposit_amount || 0),
        rent_amount: Number(initialData.rent_amount || 0),
        initial_media_url: initialData.media_items?.[0]?.url || "/images/prop-zafaranieh.jpg",
        city: initialData.location?.city || "تهران",
        province: initialData.location?.province || "تهران",
        district: initialData.location?.district || "",
        neighborhood: initialData.location?.neighborhood || "",
        full_address: initialData.location?.full_address || "",
        hide_exact_address: initialData.location?.hide_exact_address ?? true,
        amenity_codes: initialData.amenities?.map((a) => a.code) || [],
      });
    }
  }, [initialData, reset]);

  const selectedAmenities = watch("amenity_codes");
  const dealType = watch("deal_type_id");

  const toggleAmenity = (code: string) => {
    const next = selectedAmenities.includes(code)
      ? selectedAmenities.filter((c) => c !== code)
      : [...selectedAmenities, code];
    setValue("amenity_codes", next);
  };

  const onSubmit = async (values: PropertyFormValues) => {
    setSubmitError(null);
    setSavedOk(false);
    try {
      const payload = {
        property_code: values.property_code,
        title: values.title,
        description: values.description,
        property_type_id: values.property_type_id,
        deal_type_id: values.deal_type_id,
        usage_type: values.usage_type,
        visibility: values.visibility,
        is_featured: values.is_featured,
        is_negotiable: values.is_negotiable,
        is_exclusive: values.is_exclusive,
        land_area_sqm: String(values.land_area_sqm),
        built_area_sqm: String(values.built_area_sqm),
        bedrooms: values.bedrooms,
        bathrooms: values.bathrooms,
        floor_number: values.floor_number ?? null,
        total_floors: values.total_floors ?? null,
        building_age: values.building_age ?? null,
        deed_type: values.deed_type,
        currency_id: values.currency_id,
        total_price: String(values.total_price),
        deposit_amount: String(values.deposit_amount),
        rent_amount: String(values.rent_amount),
        initial_media_url: values.initial_media_url,
        amenity_codes: values.amenity_codes,
        location: {
          country_id: "IR",
          province: values.province,
          city: values.city,
          district: values.district,
          neighborhood: values.neighborhood,
          full_address: values.full_address,
          hide_exact_address: values.hide_exact_address,
        },
      };

      if (propertyId) {
        await apiFetch(`/api/v1/properties/${propertyId}`, {
          method: "PATCH",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("/api/v1/properties", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify(payload),
        });
      }
      setSavedOk(true);
      setTimeout(() => router.push("/dashboard/properties"), 700);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "خطا در ذخیره ملک");
    }
  };

  if (loadingCatalog) return <LoadingState />;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {submitError && <ErrorState message={submitError} />}
      {savedOk && <SuccessBanner message="اطلاعات ملک با موفقیت ثبت شد. در حال بازگشت به فهرست..." />}

      {/* Section 1: Basic Info */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="mb-4 text-sm font-bold text-slate-900">۱. مشخصات پایه و دسته‌بندی</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">کد ملک *</label>
            <input
              {...register("property_code")}
              disabled={Boolean(propertyId)}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm focus:border-teal-600 focus:outline-none disabled:bg-slate-100"
            />
            {errors.property_code && (
              <p className="mt-1 text-xs text-rose-600">{errors.property_code.message}</p>
            )}
          </div>

          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-semibold text-slate-700">عنوان آگهی / ملک *</label>
            <input
              {...register("title")}
              placeholder="مثال: آپارتمان نوساز ۱۸۵ متری زعفرانیه"
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
            {errors.title && <p className="mt-1 text-xs text-rose-600">{errors.title.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">نوع ملک</label>
            <select
              {...register("property_type_id")}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-teal-600 focus:outline-none"
            >
              {catalog?.property_types.map((pt) => (
                <option key={pt.code} value={pt.code}>
                  {pt.name_fa}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">نوع معامله</label>
            <select
              {...register("deal_type_id")}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-teal-600 focus:outline-none"
            >
              {catalog?.deal_types.map((dt) => (
                <option key={dt.code} value={dt.code}>
                  {dt.name_fa}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">سطح انتشار</label>
            <select
              {...register("visibility")}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-teal-600 focus:outline-none"
            >
              <option value="PUBLIC_PORTAL">انتشار عمومی در پورتال</option>
              <option value="COOP_NETWORK">شبکه همکاری آژانس‌ها</option>
              <option value="PRIVATE_AGENCY">فقط داخلی آژانس</option>
            </select>
          </div>

          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-semibold text-slate-700">توضیحات تکمیلی</label>
            <textarea
              {...register("description")}
              rows={3}
              className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-teal-600 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Section 2: Specs & Pricing */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="mb-4 text-sm font-bold text-slate-900">۲. مشخصات فنی و قیمت‌گذاری</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">زیربنا (مترمربع) *</label>
            <input
              type="number"
              {...register("built_area_sqm")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums focus:border-teal-600 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">مساحت زمین</label>
            <input
              type="number"
              {...register("land_area_sqm")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums focus:border-teal-600 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">تعداد خواب</label>
            <input
              type="number"
              {...register("bedrooms")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums focus:border-teal-600 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">سرویس بهداشتی</label>
            <input
              type="number"
              {...register("bathrooms")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums focus:border-teal-600 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">ارز</label>
            <select
              {...register("currency_id")}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-teal-600 focus:outline-none"
            >
              <option value="IRT">تومان (IRT)</option>
              <option value="IRR">ریال (IRR)</option>
              <option value="USD">دلار (USD)</option>
            </select>
          </div>

          {dealType === "MORTGAGE_RENT" ? (
            <>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700">ودیعه / رهن</label>
                <input
                  type="number"
                  {...register("deposit_amount")}
                  className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums focus:border-teal-600 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700">اجاره ماهانه</label>
                <input
                  type="number"
                  {...register("rent_amount")}
                  className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums focus:border-teal-600 focus:outline-none"
                />
              </div>
            </>
          ) : (
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs font-semibold text-slate-700">قیمت کل</label>
              <input
                type="number"
                {...register("total_price")}
                className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums focus:border-teal-600 focus:outline-none"
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">نوع سند</label>
            <input
              {...register("deed_type")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-5 border-t border-slate-100 pt-4 text-xs font-medium text-slate-700">
          <label className="flex items-center gap-2">
            <input type="checkbox" {...register("is_negotiable")} className="h-4 w-4 accent-teal-700" />
            قابل مذاکره
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" {...register("is_featured")} className="h-4 w-4 accent-teal-700" />
            آگهی ویژه پورتال
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" {...register("is_exclusive")} className="h-4 w-4 accent-teal-700" />
            فایل انحصاری آژانس
          </label>
        </div>

        {catalog?.amenities && (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <p className="mb-2 text-xs font-semibold text-slate-700">امکانات ملک</p>
            <div className="flex flex-wrap gap-2">
              {catalog.amenities.map((am) => {
                const active = selectedAmenities.includes(am.code);
                return (
                  <button
                    key={am.code}
                    type="button"
                    onClick={() => toggleAmenity(am.code)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                      active
                        ? "border-teal-700 bg-teal-50 text-teal-800"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {am.name_fa}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Section 3: Location & Media */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="mb-4 text-sm font-bold text-slate-900">۳. موقعیت مکانی و تصویر کاور</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">استان</label>
            <input
              {...register("province")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">شهر *</label>
            <input
              {...register("city")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">منطقه</label>
            <input
              {...register("district")}
              placeholder="مثال: زعفرانیه"
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">محله</label>
            <input
              {...register("neighborhood")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-semibold text-slate-700">نشانی کامل (محرمانه داخلی)</label>
            <input
              {...register("full_address")}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-teal-600 focus:outline-none"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-semibold text-slate-700">تصویر کاور</label>
            <select
              {...register("initial_media_url")}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-teal-600 focus:outline-none"
            >
              <option value="/images/prop-zafaranieh.jpg">آپارتمان لوکس مدرن</option>
              <option value="/images/prop-fereshteh.jpg">پنت‌هاوس فرشته</option>
              <option value="/images/prop-office.jpg">دفتر کار اداری</option>
              <option value="/images/prop-villa.jpg">ویلای استخردار</option>
            </select>
          </div>
        </div>
        <label className="mt-4 flex items-center gap-2 text-xs font-medium text-slate-700">
          <input type="checkbox" {...register("hide_exact_address")} className="h-4 w-4 accent-teal-700" />
          مخفی‌سازی نشانی دقیق و رند کردن مختصات در پورتال عمومی (حفاظت از حریم مالک)
        </label>
      </div>

      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={() => router.back()}
          className="h-10 rounded-lg border border-slate-300 bg-white px-5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          انصراف
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-teal-700 px-6 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {isSubmitting ? "در حال ذخیره..." : propertyId ? "به‌روزرسانی ملک" : "ثبت ملک جدید"}
        </button>
      </div>
    </form>
  );
}
