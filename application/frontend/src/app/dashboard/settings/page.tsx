"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  CreditCard,
  Globe2,
  ListChecks,
  MapPin,
  Plug,
  Plus,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type {
  AmenityValueType,
  CityItem,
  DistrictItem,
  ManagedGatewayConfig,
  NeighborhoodItem,
  PropertyCatalog,
  ProvinceItem,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

interface LocalizationResponse {
  countries: {
    code: string;
    name_fa: string;
    name_en: string;
    default_language: string;
    default_calendar: string;
    default_currency: string;
    timezone: string;
    phone_prefix: string;
    area_unit: string;
  }[];
  currencies: {
    code: string;
    name_fa: string;
    name_en: string;
    symbol: string;
    decimal_places: number;
    exchange_rate_to_base: string;
  }[];
  map_provider: {
    provider_key: string;
    display_name: string;
    tile_url: string;
    dark_tile_url: string;
    attribution: string;
    max_zoom: number;
    requires_api_key: boolean;
  };
  available_adapters: {
    payment: { key: string; name: string; supports_sandbox: boolean; required_fields: string[] }[];
    map: { key: string; name: string }[];
    ai: { key: string; name: string }[];
    sms: { key: string; name: string }[];
  };
}

interface ProviderConfigItem {
  id: string;
  agency_id: string | null;
  category: string;
  provider_key: string;
  display_name: string;
  description: string;
  priority: number;
  is_active: boolean;
  is_sandbox: boolean;
  config_json: Record<string, unknown>;
  has_credentials: boolean;
  masked_credentials: Record<string, string>;
  last_checked_at: string | null;
  last_check_status: string;
  last_check_message: string;
}

const GATEWAY_CRED_FIELD_MAP: Record<string, { field: string; label: string; placeholder: string }[]> = {
  zarinpal: [{ field: "merchant_id", label: "Merchant ID زرین‌پال (۳۶ کاراکتری)", placeholder: "00000000-0000-0000-0000-000000000000" }],
  zibal: [{ field: "merchant", label: "کد پذیرنده زیبال (merchant)", placeholder: "zibal" }],
  idpay: [{ field: "api_key", label: "کلید X-API-KEY آیدی‌پی", placeholder: "6a7f99eb-7c20-4412-a972-6dfb7cd253a4" }],
  sandbox: [],
};

export default function SettingsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"gateways" | "providers" | "geography" | "amenities">(
    "gateways"
  );
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  // Modals
  const [gatewayModalOpen, setGatewayModalOpen] = useState(false);
  const [providerModalOpen, setProviderModalOpen] = useState(false);

  // Gateway form
  const [gwForm, setGwForm] = useState({
    provider_key: "zarinpal",
    display_name: "زرین‌پال (Zarinpal v4)",
    description: "درگاه رسمی زرین‌پال با پشتیبانی از محیط تست و عملیاتی",
    priority: 10,
    is_active: true,
    is_sandbox: true,
    cred_value: "",
  });

  // General provider form (AI / MAP / SMS)
  const [provForm, setProvForm] = useState({
    category: "AI",
    provider_key: "gapgpt",
    display_name: "هوش مصنوعی GapGPT",
    is_active: true,
    is_sandbox: false,
    api_key: "",
    base_url: "https://api.gapgpt.app/v1",
    default_model: "gpt-4o",
    custom_tile_url: "",
  });

  // Geography selection & forms
  const [selProvinceId, setSelProvinceId] = useState("");
  const [selCityId, setSelCityId] = useState("");
  const [selDistrictId, setSelDistrictId] = useState("");
  const [newProvName, setNewProvName] = useState("");
  const [newProvEn, setNewProvEn] = useState("");
  const [newCityName, setNewCityName] = useState("");
  const [newDistName, setNewDistName] = useState("");
  const [newNbrName, setNewNbrName] = useState("");

  // Amenity forms
  const [catForm, setCatForm] = useState({ code: "", name_fa: "", name_en: "", sort_order: 80 });
  const [amForm, setAmForm] = useState<{
    code: string;
    category_code: string;
    name_fa: string;
    name_en: string;
    value_type: AmenityValueType;
    unit_label: string;
    options_text: string;
  }>({
    code: "",
    category_code: "INTERIOR_COMFORT",
    name_fa: "",
    name_en: "",
    value_type: "BOOLEAN",
    unit_label: "",
    options_text: "",
  });

  // Queries
  const locQ = useQuery({
    queryKey: ["settings-localization"],
    queryFn: async () => (await apiFetch<LocalizationResponse>("/api/v1/settings/localization")).data,
  });

  const gatewaysQ = useQuery({
    queryKey: ["managed-payment-gateways", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<ManagedGatewayConfig[]>("/api/v1/payments/gateways", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const provQ = useQuery({
    queryKey: ["settings-providers", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<ProviderConfigItem[]>("/api/v1/settings/providers", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const provincesQ = useQuery({
    queryKey: ["admin-geo-provinces"],
    enabled: activeTab === "geography",
    queryFn: async () =>
      (await apiFetch<ProvinceItem[]>("/api/v1/locations/provinces?active_only=false&page_size=100")).data,
  });

  const citiesQ = useQuery({
    queryKey: ["admin-geo-cities", selProvinceId],
    enabled: activeTab === "geography" && !!selProvinceId,
    queryFn: async () =>
      (
        await apiFetch<CityItem[]>(
          `/api/v1/locations/cities?province_id=${selProvinceId}&active_only=false&page_size=200`
        )
      ).data,
  });

  const districtsQ = useQuery({
    queryKey: ["admin-geo-districts", selCityId],
    enabled: activeTab === "geography" && !!selCityId,
    queryFn: async () =>
      (
        await apiFetch<DistrictItem[]>(
          `/api/v1/locations/districts?city_id=${selCityId}&active_only=false&page_size=200`
        )
      ).data,
  });

  const neighborhoodsQ = useQuery({
    queryKey: ["admin-geo-neighborhoods", selDistrictId],
    enabled: activeTab === "geography" && !!selDistrictId,
    queryFn: async () =>
      (
        await apiFetch<NeighborhoodItem[]>(
          `/api/v1/locations/neighborhoods?district_id=${selDistrictId}&active_only=false&page_size=200`
        )
      ).data,
  });

  const catalogQ = useQuery({
    queryKey: ["admin-amenities-catalog"],
    enabled: activeTab === "amenities",
    queryFn: async () =>
      (await apiFetch<PropertyCatalog>("/api/v1/properties/catalog?include_inactive=true")).data,
  });

  // Mutations
  const saveGatewayMut = useMutation({
    mutationFn: async (override?: Partial<ManagedGatewayConfig>) => {
      const key = override?.provider_key || gwForm.provider_key;
      const fields = GATEWAY_CRED_FIELD_MAP[key] || [];
      const credKey = fields[0]?.field || "api_key";
      const payload: Record<string, unknown> = {
        provider_key: key,
        display_name: override?.display_name ?? gwForm.display_name,
        description: override?.description ?? gwForm.description,
        priority: override?.priority ?? Number(gwForm.priority || 10),
        is_active: override?.is_active ?? gwForm.is_active,
        is_sandbox: override?.is_sandbox ?? gwForm.is_sandbox,
        config_json: override?.config_json ?? {},
      };
      if (!override && gwForm.cred_value.trim()) {
        payload.credentials = { [credKey]: gwForm.cred_value.trim() };
      }
      return apiFetch("/api/v1/payments/gateways", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      setGatewayModalOpen(false);
      setGwForm((f) => ({ ...f, cred_value: "" }));
      setErrMsg(null);
      setNotice("پیکربندی درگاه پرداخت با رمزنگاری Fernet ذخیره شد.");
      qc.invalidateQueries({ queryKey: ["managed-payment-gateways"] });
      qc.invalidateQueries({ queryKey: ["active-payment-gateways"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const testGatewayMut = useMutation({
    mutationFn: async (configId: string) =>
      (
        await apiFetch<{ ok: boolean; status: string; message: string }>(
          `/api/v1/payments/gateways/${configId}/test`,
          { method: "POST", token: accessToken, agencyId: activeAgencyId }
        )
      ).data,
    onSuccess: (res) => {
      setErrMsg(res.ok ? null : res.message);
      if (res.ok) setNotice(res.message);
      qc.invalidateQueries({ queryKey: ["managed-payment-gateways"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const upsertProviderMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/settings/providers", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          category: provForm.category,
          provider_key: provForm.provider_key,
          display_name: provForm.display_name,
          is_active: provForm.is_active,
          is_sandbox: provForm.is_sandbox,
          config_json:
            provForm.category === "AI"
              ? { base_url: provForm.base_url, default_model: provForm.default_model }
              : provForm.category === "MAP" && provForm.custom_tile_url
              ? { custom_tile_url: provForm.custom_tile_url }
              : {},
          credentials: provForm.api_key.trim() ? { api_key: provForm.api_key.trim() } : undefined,
        }),
      }),
    onSuccess: () => {
      setProviderModalOpen(false);
      setProvForm((p) => ({ ...p, api_key: "" }));
      setErrMsg(null);
      setNotice("تنظیمات سرویس جانبی ذخیره شد.");
      qc.invalidateQueries({ queryKey: ["settings-providers"] });
      qc.invalidateQueries({ queryKey: ["settings-localization"] });
      qc.invalidateQueries({ queryKey: ["ai-status"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const testProviderMut = useMutation({
    mutationFn: async (configId: string) =>
      (
        await apiFetch<{ ok: boolean; status: string; message: string }>(
          `/api/v1/settings/providers/${configId}/test`,
          { method: "POST", token: accessToken, agencyId: activeAgencyId }
        )
      ).data,
    onSuccess: (res) => {
      setNotice(res.message);
      setErrMsg(null);
      qc.invalidateQueries({ queryKey: ["settings-providers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const toggleGeoMut = useMutation({
    mutationFn: async ({ level, id, is_active }: { level: string; id: string; is_active: boolean }) =>
      apiFetch(`/api/v1/locations/${level}/${id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: () => {
      setNotice("وضعیت موقعیت جغرافیایی به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["admin-geo-provinces"] });
      qc.invalidateQueries({ queryKey: ["admin-geo-cities"] });
      qc.invalidateQueries({ queryKey: ["admin-geo-districts"] });
      qc.invalidateQueries({ queryKey: ["admin-geo-neighborhoods"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createGeoMut = useMutation({
    mutationFn: async ({ level, body }: { level: string; body: Record<string, unknown> }) =>
      apiFetch(`/api/v1/locations/${level}`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      setNewProvName("");
      setNewProvEn("");
      setNewCityName("");
      setNewDistName("");
      setNewNbrName("");
      setErrMsg(null);
      setNotice("موقعیت جغرافیایی جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["admin-geo-provinces"] });
      qc.invalidateQueries({ queryKey: ["admin-geo-cities"] });
      qc.invalidateQueries({ queryKey: ["admin-geo-districts"] });
      qc.invalidateQueries({ queryKey: ["admin-geo-neighborhoods"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createCatMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/properties/amenity-categories", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ ...catForm, code: catForm.code.toUpperCase() }),
      }),
    onSuccess: () => {
      setCatForm({ code: "", name_fa: "", name_en: "", sort_order: 80 });
      setNotice("دسته‌بندی جدید امکانات ثبت شد.");
      qc.invalidateQueries({ queryKey: ["admin-amenities-catalog"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const upsertAmenityMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/properties/amenities", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          code: amForm.code.toUpperCase(),
          category_code: amForm.category_code || null,
          name_fa: amForm.name_fa,
          name_en: amForm.name_en,
          value_type: amForm.value_type,
          unit_label: amForm.unit_label,
          options_json: amForm.options_text
            ? amForm.options_text.split(",").map((s) => s.trim()).filter(Boolean)
            : [],
          is_active: true,
        }),
      }),
    onSuccess: () => {
      setAmForm({
        code: "",
        category_code: "INTERIOR_COMFORT",
        name_fa: "",
        name_en: "",
        value_type: "BOOLEAN",
        unit_label: "",
        options_text: "",
      });
      setNotice("امکان جدید ثبت و در فرم‌های ملک و جستجو فعال شد.");
      qc.invalidateQueries({ queryKey: ["admin-amenities-catalog"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const toggleAmenityMut = useMutation({
    mutationFn: async ({ code, is_active }: { code: string; is_active: boolean }) =>
      apiFetch(`/api/v1/properties/amenities/${code}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: () => {
      setNotice("وضعیت امکان به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["admin-amenities-catalog"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const openGatewayEditor = (existing?: ManagedGatewayConfig, quickKey?: string) => {
    const key = existing?.provider_key || quickKey || "zarinpal";
    const defaultNames: Record<string, string> = {
      zarinpal: "زرین‌پال (Zarinpal v4)",
      zibal: "زیبال (Zibal v1)",
      idpay: "آیدی‌پی (IDPay v1.1)",
      sandbox: "درگاه آزمایشی داخلی (Sandbox)",
    };
    setGwForm({
      provider_key: key,
      display_name: existing?.display_name || defaultNames[key] || key,
      description: existing?.description || "",
      priority: existing?.priority ?? 10,
      is_active: existing?.is_active ?? true,
      is_sandbox: existing?.is_sandbox ?? true,
      cred_value: "",
    });
    setGatewayModalOpen(true);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="مرکز کنترل تنظیمات، درگاه‌ها، جغرافیا و امکانات"
        subtitle="مدیریت درگاه‌های پرداخت ایرانی، اتصال GapGPT و سرویس نقشه، سلسله‌مراتب جغرافیا و کاتالوگ امکانات"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "تنظیمات سازمانی" }]}
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
        {[
          { key: "gateways", label: "درگاه‌های پرداخت ایرانی", icon: <CreditCard className="h-4 w-4" /> },
          { key: "providers", label: "هوش مصنوعی، نقشه و بومی‌سازی", icon: <Plug className="h-4 w-4" /> },
          { key: "geography", label: "مدیریت استان / شهر / منطقه / محله", icon: <MapPin className="h-4 w-4" /> },
          { key: "amenities", label: "امکانات دسته‌بندی‌شده ملک", icon: <ListChecks className="h-4 w-4" /> },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setActiveTab(t.key as typeof activeTab)}
            className={`inline-flex h-10 items-center gap-2 rounded-lg border px-4 text-xs font-semibold transition-colors ${
              activeTab === t.key
                ? "border-teal-700 bg-teal-700 text-white dark:border-teal-500 dark:bg-teal-600"
                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB 1: IRANIAN PAYMENT GATEWAYS */}
      {activeTab === "gateways" && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              {["zarinpal", "zibal", "idpay", "sandbox"].map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() =>
                    openGatewayEditor(
                      (gatewaysQ.data || []).find((g) => g.provider_key === k),
                      k
                    )
                  }
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  <Plus className="h-3.5 w-3.5 text-teal-600" />
                  تنظیم {k === "zarinpal" ? "زرین‌پال" : k === "zibal" ? "زیبال" : k === "idpay" ? "آیدی‌پی" : "Sandbox"}
                </button>
              ))}
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <ShieldCheck className="h-4 w-4 text-teal-600" />
              تمام کلیدهای پذیرنده با رمزنگاری Fernet ذخیره و در خروجی ماسک می‌شوند.
            </span>
          </div>

          {gatewaysQ.isLoading ? (
            <LoadingState />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {(gatewaysQ.data || []).map((gw) => (
                <div
                  key={gw.id}
                  className="surface-card flex flex-col justify-between rounded-xl p-5 space-y-4"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                          {gw.display_name}
                        </h3>
                        <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                          {gw.provider_key} | اولویت {gw.priority}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded px-2 py-0.5 font-mono text-[10px] font-semibold ${
                            gw.is_sandbox
                              ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                              : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                          }`}
                        >
                          {gw.is_sandbox ? "Sandbox" : "Production"}
                        </span>
                        <StatusText status={gw.is_active ? "ACTIVE" : "SUSPENDED"} />
                      </div>
                    </div>

                    {gw.description && (
                      <p className="text-xs text-slate-600 dark:text-slate-400">{gw.description}</p>
                    )}

                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/50">
                      <div className="font-semibold text-slate-700 dark:text-slate-300">
                        اطلاعات پذیرنده (ماسک‌شده):
                      </div>
                      {Object.keys(gw.masked_credentials || {}).length === 0 ? (
                        <div className="mt-1 text-slate-400">کلید اختصاصی ثبت نشده (حالت تست پیش‌فرض)</div>
                      ) : (
                        <div className="mt-1 space-y-1 font-mono text-[11px]">
                          {Object.entries(gw.masked_credentials).map(([k, v]) => (
                            <div key={k} className="flex items-center justify-between">
                              <span className="text-slate-500">{k}:</span>
                              <span className="text-slate-800 dark:text-slate-200">{v}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {gw.last_check_status && (
                      <div className="text-[11px] text-slate-500 dark:text-slate-400">
                        آخرین بررسی: <span className="font-mono font-semibold">{gw.last_check_status}</span>
                        {gw.last_check_message ? ` — ${gw.last_check_message}` : ""}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                    <button
                      type="button"
                      onClick={() => openGatewayEditor(gw)}
                      className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                    >
                      ویرایش کلید و محیط
                    </button>
                    <button
                      type="button"
                      disabled={testGatewayMut.isPending}
                      onClick={() => testGatewayMut.mutate(gw.id)}
                      className="inline-flex h-8 items-center gap-1 rounded-lg border border-teal-300 bg-teal-50 px-3 text-xs font-semibold text-teal-800 hover:bg-teal-100 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-300"
                    >
                      <Activity className="h-3.5 w-3.5" />
                      تست اتصال
                    </button>
                    <button
                      type="button"
                      disabled={saveGatewayMut.isPending}
                      onClick={() =>
                        saveGatewayMut.mutate({
                          provider_key: gw.provider_key,
                          display_name: gw.display_name,
                          description: gw.description,
                          priority: gw.priority,
                          is_active: !gw.is_active,
                          is_sandbox: gw.is_sandbox,
                          config_json: gw.config_json,
                        })
                      }
                      className="mr-auto inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      {gw.is_active ? (
                        <>
                          <ToggleRight className="h-4 w-4 text-emerald-600" />
                          غیرفعال‌سازی
                        </>
                      ) : (
                        <>
                          <ToggleLeft className="h-4 w-4 text-slate-400" />
                          فعال‌سازی
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: AI, MAP, SMS & LOCALIZATION */}
      {activeTab === "providers" && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setProviderModalOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Plus className="h-4 w-4" />
              تنظیم آداپتر GapGPT / نقشه / پیامک
            </button>
          </div>

          {locQ.isLoading ? (
            <LoadingState />
          ) : (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="surface-card rounded-xl p-5 space-y-3">
                <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
                  <Globe2 className="h-5 w-5 text-teal-700 dark:text-teal-400" />
                  <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">کشورها و تقویم</h2>
                </div>
                <div className="space-y-2">
                  {(locQ.data?.countries || []).map((c) => (
                    <div
                      key={c.code}
                      className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/60"
                    >
                      <div>
                        <div className="font-bold text-slate-900 dark:text-slate-100">
                          {c.name_fa} ({c.code})
                        </div>
                        <div className="text-slate-500 dark:text-slate-400">
                          {c.timezone} | پیش‌شماره {c.phone_prefix}
                        </div>
                      </div>
                      <div className="text-left font-mono text-slate-700 dark:text-slate-300">
                        <div>{c.default_currency}</div>
                        <div className="text-[10px] text-slate-500">{c.default_calendar}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="surface-card rounded-xl p-5 space-y-3">
                <h2 className="border-b border-slate-200 pb-3 text-sm font-bold text-slate-900 dark:border-slate-800 dark:text-slate-100">
                  ارزها و نرخ تبدیل (Decimal)
                </h2>
                <div className="space-y-2">
                  {(locQ.data?.currencies || []).map((cur) => (
                    <div
                      key={cur.code}
                      className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/60"
                    >
                      <div>
                        <div className="font-bold text-slate-900 dark:text-slate-100">
                          {cur.name_fa} ({cur.code})
                        </div>
                        <div className="text-slate-500 dark:text-slate-400">نماد: {cur.symbol}</div>
                      </div>
                      <div className="font-mono text-slate-800 dark:text-slate-200 tabular-nums">
                        نرخ: {cur.exchange_rate_to_base}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="surface-card rounded-xl p-5 space-y-3">
                <h2 className="border-b border-slate-200 pb-3 text-sm font-bold text-slate-900 dark:border-slate-800 dark:text-slate-100">
                  سرویس نقشه فعال
                </h2>
                {locQ.data?.map_provider && (
                  <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-xs dark:border-slate-800 dark:bg-slate-800/60">
                    <div className="flex items-center justify-between font-bold text-slate-900 dark:text-slate-100">
                      <span>{locQ.data.map_provider.display_name}</span>
                      <span className="font-mono text-[11px] text-teal-700 dark:text-teal-400">
                        {locQ.data.map_provider.provider_key}
                      </span>
                    </div>
                    <div className="break-all font-mono text-[10px] text-slate-500 dark:text-slate-400">
                      {locQ.data.map_provider.tile_url}
                    </div>
                    <div className="text-[11px] text-slate-600 dark:text-slate-400 tabular-nums">
                      حداکثر بزرگنمایی: {locQ.data.map_provider.max_zoom}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="surface-card rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
              <Plug className="h-5 w-5 text-teal-700 dark:text-teal-400" />
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                آداپترهای ثبت‌شده (AI / Map / SMS)
              </h2>
            </div>
            {provQ.isLoading ? (
              <LoadingState />
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                {(provQ.data || [])
                  .filter((p) => p.category !== "PAYMENT")
                  .map((p) => (
                    <div
                      key={p.id}
                      className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs space-y-2 dark:border-slate-800 dark:bg-slate-800/60"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 dark:text-slate-100">
                          {p.display_name}
                        </span>
                        <StatusText status={p.is_active ? "ACTIVE" : "SUSPENDED"} />
                      </div>
                      <div className="font-mono text-slate-600 dark:text-slate-400">
                        {p.category} — {p.provider_key}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400">
                        کلید رمزنگاری‌شده:{" "}
                        {p.has_credentials
                          ? Object.values(p.masked_credentials || {})[0] || "ثبت‌شده"
                          : "تنظیم نشده"}
                      </div>
                      {p.last_check_message && (
                        <div className="text-[11px] text-teal-700 dark:text-teal-400">
                          {p.last_check_message}
                        </div>
                      )}
                      <button
                        type="button"
                        onClick={() => testProviderMut.mutate(p.id)}
                        className="mt-1 inline-flex h-7 items-center gap-1 rounded border border-slate-300 bg-white px-2.5 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                      >
                        <Activity className="h-3 w-3" />
                        تست وضعیت
                      </button>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: HIERARCHICAL GEOGRAPHY MANAGER */}
      {activeTab === "geography" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          {/* Provinces */}
          <div className="surface-card rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">۱. استان‌ها</h3>
            <div className="flex gap-1.5">
              <input
                value={newProvName}
                onChange={(e) => setNewProvName(e.target.value)}
                placeholder="نام استان جدید..."
                className="h-8 flex-1 rounded border border-slate-300 px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
              />
              <button
                type="button"
                disabled={!newProvName.trim()}
                onClick={() =>
                  createGeoMut.mutate({
                    level: "provinces",
                    body: { name_fa: newProvName.trim(), name_en: newProvEn.trim() },
                  })
                }
                className="h-8 rounded bg-teal-700 px-2.5 text-xs font-semibold text-white disabled:opacity-40"
              >
                ثبت
              </button>
            </div>
            <div className="max-h-96 space-y-1.5 overflow-y-auto">
              {(provincesQ.data || []).map((p) => (
                <div
                  key={p.id}
                  onClick={() => {
                    setSelProvinceId(p.id);
                    setSelCityId("");
                    setSelDistrictId("");
                  }}
                  className={`flex cursor-pointer items-center justify-between rounded-lg border px-2.5 py-2 text-xs ${
                    selProvinceId === p.id
                      ? "border-teal-600 bg-teal-50/70 font-bold dark:border-teal-500 dark:bg-teal-950/40"
                      : "border-slate-200 dark:border-slate-800"
                  }`}
                >
                  <span className={!p.is_active ? "line-through opacity-50" : ""}>{p.name_fa}</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleGeoMut.mutate({ level: "province", id: p.id, is_active: !p.is_active });
                    }}
                    className="text-[10px] font-mono text-teal-700 dark:text-teal-400"
                  >
                    {p.is_active ? "فعال" : "غیرفعال"}
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Cities */}
          <div className="surface-card rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">۲. شهرها</h3>
            {selProvinceId ? (
              <>
                <div className="flex gap-1.5">
                  <input
                    value={newCityName}
                    onChange={(e) => setNewCityName(e.target.value)}
                    placeholder="نام شهر جدید..."
                    className="h-8 flex-1 rounded border border-slate-300 px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <button
                    type="button"
                    disabled={!newCityName.trim()}
                    onClick={() =>
                      createGeoMut.mutate({
                        level: "cities",
                        body: { province_id: selProvinceId, name_fa: newCityName.trim() },
                      })
                    }
                    className="h-8 rounded bg-teal-700 px-2.5 text-xs font-semibold text-white disabled:opacity-40"
                  >
                    ثبت
                  </button>
                </div>
                <div className="max-h-96 space-y-1.5 overflow-y-auto">
                  {(citiesQ.data || []).map((c) => (
                    <div
                      key={c.id}
                      onClick={() => {
                        setSelCityId(c.id);
                        setSelDistrictId("");
                      }}
                      className={`flex cursor-pointer items-center justify-between rounded-lg border px-2.5 py-2 text-xs ${
                        selCityId === c.id
                          ? "border-teal-600 bg-teal-50/70 font-bold dark:border-teal-500 dark:bg-teal-950/40"
                          : "border-slate-200 dark:border-slate-800"
                      }`}
                    >
                      <span className={!c.is_active ? "line-through opacity-50" : ""}>{c.name_fa}</span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleGeoMut.mutate({ level: "city", id: c.id, is_active: !c.is_active });
                        }}
                        className="text-[10px] font-mono text-teal-700 dark:text-teal-400"
                      >
                        {c.is_active ? "فعال" : "غیرفعال"}
                      </button>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-slate-400">ابتدا یک استان را انتخاب کنید.</p>
            )}
          </div>

          {/* Districts */}
          <div className="surface-card rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">۳. مناطق</h3>
            {selCityId ? (
              <>
                <div className="flex gap-1.5">
                  <input
                    value={newDistName}
                    onChange={(e) => setNewDistName(e.target.value)}
                    placeholder="نام منطقه جدید..."
                    className="h-8 flex-1 rounded border border-slate-300 px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <button
                    type="button"
                    disabled={!newDistName.trim()}
                    onClick={() =>
                      createGeoMut.mutate({
                        level: "districts",
                        body: { city_id: selCityId, name_fa: newDistName.trim() },
                      })
                    }
                    className="h-8 rounded bg-teal-700 px-2.5 text-xs font-semibold text-white disabled:opacity-40"
                  >
                    ثبت
                  </button>
                </div>
                <div className="max-h-96 space-y-1.5 overflow-y-auto">
                  {(districtsQ.data || []).map((d) => (
                    <div
                      key={d.id}
                      onClick={() => setSelDistrictId(d.id)}
                      className={`flex cursor-pointer items-center justify-between rounded-lg border px-2.5 py-2 text-xs ${
                        selDistrictId === d.id
                          ? "border-teal-600 bg-teal-50/70 font-bold dark:border-teal-500 dark:bg-teal-950/40"
                          : "border-slate-200 dark:border-slate-800"
                      }`}
                    >
                      <span className={!d.is_active ? "line-through opacity-50" : ""}>{d.name_fa}</span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleGeoMut.mutate({ level: "district", id: d.id, is_active: !d.is_active });
                        }}
                        className="text-[10px] font-mono text-teal-700 dark:text-teal-400"
                      >
                        {d.is_active ? "فعال" : "غیرفعال"}
                      </button>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-slate-400">ابتدا یک شهر را انتخاب کنید.</p>
            )}
          </div>

          {/* Neighborhoods */}
          <div className="surface-card rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">۴. محله‌ها</h3>
            {selDistrictId ? (
              <>
                <div className="flex gap-1.5">
                  <input
                    value={newNbrName}
                    onChange={(e) => setNewNbrName(e.target.value)}
                    placeholder="نام محله جدید..."
                    className="h-8 flex-1 rounded border border-slate-300 px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <button
                    type="button"
                    disabled={!newNbrName.trim()}
                    onClick={() =>
                      createGeoMut.mutate({
                        level: "neighborhoods",
                        body: { district_id: selDistrictId, name_fa: newNbrName.trim() },
                      })
                    }
                    className="h-8 rounded bg-teal-700 px-2.5 text-xs font-semibold text-white disabled:opacity-40"
                  >
                    ثبت
                  </button>
                </div>
                <div className="max-h-96 space-y-1.5 overflow-y-auto">
                  {(neighborhoodsQ.data || []).map((n) => (
                    <div
                      key={n.id}
                      className="flex items-center justify-between rounded-lg border border-slate-200 px-2.5 py-2 text-xs dark:border-slate-800"
                    >
                      <span className={!n.is_active ? "line-through opacity-50" : ""}>{n.name_fa}</span>
                      <button
                        type="button"
                        onClick={() =>
                          toggleGeoMut.mutate({
                            level: "neighborhood",
                            id: n.id,
                            is_active: !n.is_active,
                          })
                        }
                        className="text-[10px] font-mono text-teal-700 dark:text-teal-400"
                      >
                        {n.is_active ? "فعال" : "غیرفعال"}
                      </button>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-slate-400">ابتدا یک منطقه را انتخاب کنید.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: EXTENSIBLE CATEGORIZED AMENITIES */}
      {activeTab === "amenities" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Create Category */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createCatMut.mutate();
              }}
              className="surface-card rounded-xl p-5 space-y-3"
            >
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                افزودن دسته‌بندی امکانات
              </h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <input
                  required
                  placeholder="کد لاتین (مثال: WELLNESS)"
                  value={catForm.code}
                  onChange={(e) => setCatForm({ ...catForm, code: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                />
                <input
                  required
                  placeholder="عنوان فارسی"
                  value={catForm.name_fa}
                  onChange={(e) => setCatForm({ ...catForm, name_fa: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                />
                <input
                  placeholder="عنوان انگلیسی"
                  value={catForm.name_en}
                  onChange={(e) => setCatForm({ ...catForm, name_en: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                />
              </div>
              <button
                type="submit"
                className="h-9 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800"
              >
                ثبت دسته‌بندی
              </button>
            </form>

            {/* Create Typed Amenity */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                upsertAmenityMut.mutate();
              }}
              className="surface-card rounded-xl p-5 space-y-3"
            >
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                افزودن / ویرایش امکان ملکی جدید
              </h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <input
                  required
                  placeholder="کد (مثال: EV_CHARGER)"
                  value={amForm.code}
                  onChange={(e) => setAmForm({ ...amForm, code: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                />
                <input
                  required
                  placeholder="نام فارسی (شارژر خودرو برقی)"
                  value={amForm.name_fa}
                  onChange={(e) => setAmForm({ ...amForm, name_fa: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                />
                <select
                  value={amForm.category_code}
                  onChange={(e) => setAmForm({ ...amForm, category_code: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                >
                  {(catalogQ.data?.amenity_categories || []).map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name_fa}
                    </option>
                  ))}
                </select>
                <select
                  value={amForm.value_type}
                  onChange={(e) =>
                    setAmForm({ ...amForm, value_type: e.target.value as AmenityValueType })
                  }
                  className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                >
                  <option value="BOOLEAN">بلی / خیر (Boolean)</option>
                  <option value="INTEGER">عددی صحیح (Integer)</option>
                  <option value="DECIMAL">اعشاری (Decimal)</option>
                  <option value="TEXT">متنی (Text)</option>
                  <option value="CHOICE">انتخاب از گزینه‌ها (Choice)</option>
                </select>
                <input
                  placeholder="واحد اندازه‌گیری (عدد، متر...)"
                  value={amForm.unit_label}
                  onChange={(e) => setAmForm({ ...amForm, unit_label: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                />
                <input
                  placeholder="گزینه‌ها (با کاما جدا شود)"
                  value={amForm.options_text}
                  onChange={(e) => setAmForm({ ...amForm, options_text: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                />
              </div>
              <button
                type="submit"
                className="h-9 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800"
              >
                ذخیره امکان در کاتالوگ
              </button>
            </form>
          </div>

          {catalogQ.isLoading ? (
            <LoadingState />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {(catalogQ.data?.amenity_categories || []).map((cat) => {
                const items = (catalogQ.data?.amenities || []).filter(
                  (a) => a.category_code === cat.code
                );
                return (
                  <div key={cat.code} className="surface-card rounded-xl p-4 space-y-2.5">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2 dark:border-slate-800">
                      <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                        {cat.name_fa}
                      </span>
                      <span className="font-mono text-[11px] text-slate-500">{items.length} مورد</span>
                    </div>
                    <div className="space-y-1.5">
                      {items.map((am) => (
                        <div
                          key={am.code}
                          className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-slate-800 dark:bg-slate-800/50"
                        >
                          <div>
                            <span
                              className={`font-semibold ${
                                am.is_active === false ? "line-through opacity-50" : ""
                              }`}
                            >
                              {am.name_fa}
                            </span>
                            <span className="mr-2 font-mono text-[10px] text-slate-400">
                              [{am.value_type || "BOOLEAN"}
                              {am.unit_label ? ` / ${am.unit_label}` : ""}]
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={() =>
                              toggleAmenityMut.mutate({
                                code: am.code,
                                is_active: am.is_active === false,
                              })
                            }
                            className="text-[11px] font-semibold text-teal-700 dark:text-teal-400"
                          >
                            {am.is_active === false ? "فعال کردن" : "غیرفعال کردن"}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Gateway Modal */}
      <ModalDrawer
        open={gatewayModalOpen}
        onClose={() => setGatewayModalOpen(false)}
        title="پیکربندی درگاه پرداخت ایرانی"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveGatewayMut.mutate(undefined);
          }}
          className="space-y-3"
        >
          <select
            value={gwForm.provider_key}
            onChange={(e) => setGwForm({ ...gwForm, provider_key: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="zarinpal">زرین‌پال (Zarinpal v4)</option>
            <option value="zibal">زیبال (Zibal v1)</option>
            <option value="idpay">آیدی‌پی (IDPay v1.1)</option>
            <option value="sandbox">درگاه آزمایشی داخلی (Sandbox)</option>
          </select>
          <input
            required
            placeholder="نام نمایشی درگاه"
            value={gwForm.display_name}
            onChange={(e) => setGwForm({ ...gwForm, display_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            placeholder="توضیح کوتاه"
            value={gwForm.description}
            onChange={(e) => setGwForm({ ...gwForm, description: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          {(GATEWAY_CRED_FIELD_MAP[gwForm.provider_key] || []).map((f) => (
            <div key={f.field} className="space-y-1">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
                {f.label}
              </label>
              <input
                type="password"
                placeholder={f.placeholder}
                value={gwForm.cred_value}
                onChange={(e) => setGwForm({ ...gwForm, cred_value: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              />
            </div>
          ))}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-slate-500">اولویت نمایش</label>
              <input
                type="number"
                value={gwForm.priority}
                onChange={(e) => setGwForm({ ...gwForm, priority: Number(e.target.value) })}
                className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums dark:border-slate-700 dark:bg-slate-950"
              />
            </div>
            <div className="flex flex-col justify-center gap-2 text-xs text-slate-700 dark:text-slate-300">
              <label className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={gwForm.is_active}
                  onChange={(e) => setGwForm({ ...gwForm, is_active: e.target.checked })}
                  className="accent-teal-700"
                />
                درگاه فعال باشد
              </label>
              <label className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={gwForm.is_sandbox}
                  onChange={(e) => setGwForm({ ...gwForm, is_sandbox: e.target.checked })}
                  className="accent-teal-700"
                />
                محیط آزمایشی (Sandbox)
              </label>
            </div>
          </div>
          <button
            type="submit"
            disabled={saveGatewayMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800"
          >
            ذخیره امن تنظیمات درگاه
          </button>
        </form>
      </ModalDrawer>

      {/* General Provider Modal */}
      <ModalDrawer
        open={providerModalOpen}
        onClose={() => setProviderModalOpen(false)}
        title="تنظیم آداپتر هوش مصنوعی / نقشه / پیامک"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            upsertProviderMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            value={provForm.category}
            onChange={(e) => {
              const cat = e.target.value;
              setProvForm({
                ...provForm,
                category: cat,
                provider_key: cat === "AI" ? "gapgpt" : cat === "MAP" ? "osm" : "kavenegar_ready",
                display_name:
                  cat === "AI" ? "GapGPT AI" : cat === "MAP" ? "نقشه OpenStreetMap" : "کاوه‌نگار",
              });
            }}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="AI">هوش مصنوعی (GapGPT)</option>
            <option value="MAP">سرویس نقشه (OSM / Carto / Neshan)</option>
            <option value="SMS">سرویس پیامک (SMS)</option>
          </select>
          <input
            required
            placeholder="کلید آداپتر (gapgpt, osm, carto_positron, neshan, kavenegar_ready)"
            value={provForm.provider_key}
            onChange={(e) => setProvForm({ ...provForm, provider_key: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            required
            placeholder="نام نمایشی"
            value={provForm.display_name}
            onChange={(e) => setProvForm({ ...provForm, display_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          {provForm.category === "AI" && (
            <div className="grid grid-cols-2 gap-2">
              <input
                placeholder="Base URL"
                value={provForm.base_url}
                onChange={(e) => setProvForm({ ...provForm, base_url: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
              />
              <input
                placeholder="مدل پیش‌فرض (gpt-4o)"
                value={provForm.default_model}
                onChange={(e) => setProvForm({ ...provForm, default_model: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
              />
            </div>
          )}
          {provForm.category === "MAP" && (
            <input
              placeholder="آدرس Tile سفارشی (اختیاری)"
              value={provForm.custom_tile_url}
              onChange={(e) => setProvForm({ ...provForm, custom_tile_url: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
            />
          )}
          <input
            type="password"
            placeholder="کلید API (رمزنگاری Fernet می‌شود)"
            value={provForm.api_key}
            onChange={(e) => setProvForm({ ...provForm, api_key: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          <button
            type="submit"
            disabled={upsertProviderMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800"
          >
            ذخیره تنظیمات آداپتر
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
