"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Globe2, Plug, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
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
    tile_url_template: string;
    default_center: { lat: number; lng: number; zoom: number };
  };
  available_adapters: {
    payment: { key: string; name: string }[];
    sms: { key: string; name: string }[];
    map: { key: string; name: string }[];
  };
}

interface ProviderConfigItem {
  id: string;
  agency_id: string | null;
  category: string;
  provider_key: string;
  display_name: string;
  is_active: boolean;
  is_sandbox: boolean;
  config_json: Record<string, unknown>;
  has_credentials: boolean;
}

export default function SettingsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    category: "PAYMENT",
    provider_key: "sandbox",
    display_name: "درگاه پرداخت آزمایشی",
    is_active: true,
    is_sandbox: true,
    api_key: "",
  });

  const locQ = useQuery({
    queryKey: ["settings-localization"],
    queryFn: async () => (await apiFetch<LocalizationResponse>("/api/v1/settings/localization")).data,
  });

  const provQ = useQuery({
    queryKey: ["settings-providers", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<ProviderConfigItem[]>("/api/v1/settings/providers", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const upsertMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/settings/providers", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          category: form.category,
          provider_key: form.provider_key,
          display_name: form.display_name,
          is_active: form.is_active,
          is_sandbox: form.is_sandbox,
          config_json: {},
          credentials: form.api_key.trim() ? { api_key: form.api_key.trim() } : undefined,
        }),
      }),
    onSuccess: () => {
      setModalOpen(false);
      setForm({
        category: "PAYMENT",
        provider_key: "sandbox",
        display_name: "درگاه پرداخت آزمایشی",
        is_active: true,
        is_sandbox: true,
        api_key: "",
      });
      setErrMsg(null);
      setNotice("پیکربندی آداپتر سرویس جانبی با رمزنگاری کلیدها ذخیره شد.");
      qc.invalidateQueries({ queryKey: ["settings-providers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="تنظیمات بومی‌سازی و آداپتر سرویس‌ها"
        subtitle="پیکربندی کشورها، ارزها، تقویم و اتصال آداپترهای قابل تعویض پرداخت، پیامک و نقشه"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "تنظیمات و آداپترها" }]}
        actions={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            تنظیم آداپتر جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {locQ.isLoading ? (
        <LoadingState />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
              <Globe2 className="h-5 w-5 text-teal-700" />
              <h2 className="text-sm font-bold text-slate-900">کشورها و تنظیمات منطقه‌ای</h2>
            </div>
            <div className="space-y-2.5">
              {(locQ.data?.countries || []).map((c) => (
                <div key={c.code} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                  <div>
                    <div className="font-bold text-slate-900">{c.name_fa} ({c.code})</div>
                    <div className="text-slate-500">منطقه زمانی: {c.timezone} | واحد مساحت: {c.area_unit}</div>
                  </div>
                  <div className="text-left font-mono text-slate-700">
                    <div>{c.default_currency}</div>
                    <div className="text-[11px] text-slate-500">{c.default_calendar}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
            <h2 className="border-b border-slate-200 pb-3 text-sm font-bold text-slate-900">
              ارزهای پشتیبانی‌شده و نرخ تبدیل (Decimal)
            </h2>
            <div className="space-y-2.5">
              {(locQ.data?.currencies || []).map((cur) => (
                <div key={cur.code} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                  <div>
                    <div className="font-bold text-slate-900">{cur.name_fa} ({cur.code})</div>
                    <div className="text-slate-500">نماد: {cur.symbol}</div>
                  </div>
                  <div className="font-mono text-slate-800">نرخ مبنا: {cur.exchange_rate_to_base}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
          <Plug className="h-5 w-5 text-teal-700" />
          <h2 className="text-sm font-bold text-slate-900">آداپترهای فعال پرداخت، پیامک و نقشه</h2>
        </div>
        {provQ.isLoading ? (
          <LoadingState />
        ) : (provQ.data || []).length === 0 ? (
          <p className="text-xs text-slate-500">هنوز آداپتر اختصاصی ثبت نشده و سیستم از حالت پیش‌فرض Sandbox استفاده می‌کند.</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {provQ.data?.map((p) => (
              <div key={p.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">{p.display_name}</span>
                  <StatusText status={p.is_active ? "ACTIVE" : "SUSPENDED"} />
                </div>
                <div className="font-mono text-slate-600">{p.category} — {p.provider_key}</div>
                <div className="text-slate-500">
                  محیط: {p.is_sandbox ? "آزمایشی (Sandbox)" : "عملیاتی"} | کلید رمزنگاری‌شده:{" "}
                  {p.has_credentials ? "ثبت‌شده" : "ندارد"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ModalDrawer open={modalOpen} onClose={() => setModalOpen(false)} title="پیکربندی آداپتر سرویس جانبی">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            upsertMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="PAYMENT">درگاه پرداخت (Payment)</option>
            <option value="SMS">سرویس پیامک (SMS)</option>
            <option value="MAP">سرویس نقشه (Map)</option>
          </select>
          <input
            required
            placeholder="کلید آداپتر (مثال: sandbox, zarinpal_ready, kavenegar_ready, osm_tile)"
            value={form.provider_key}
            onChange={(e) => setForm({ ...form, provider_key: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm"
          />
          <input
            required
            placeholder="نام نمایشی"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <input
            type="password"
            placeholder="کلید API / Merchant ID (به‌صورت رمزنگاری‌شده ذخیره می‌شود)"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm"
          />
          <div className="flex items-center gap-4 text-xs text-slate-700">
            <label className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                className="accent-teal-700"
              />
              فعال باشد
            </label>
            <label className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={form.is_sandbox}
                onChange={(e) => setForm({ ...form, is_sandbox: e.target.checked })}
                className="accent-teal-700"
              />
              حالت آزمایشی (Sandbox)
            </label>
          </div>
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ذخیره تنظیمات آداپتر
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
