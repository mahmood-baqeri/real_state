"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, Calendar, Coins, Globe2, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type {
  CalendarSystemItem,
  CountryItem,
  CurrencyConfigItem,
  ExchangeRateHistoryItem,
  ExchangeRateItem,
} from "@/lib/types";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { LoadingState } from "@/components/ui/StateNotice";

interface Props {
  onNotice: (msg: string) => void;
  onError: (msg: string) => void;
}

export function CountriesCurrenciesTab({ onNotice, onError }: Props) {
  const { accessToken } = useAuth();
  const qc = useQueryClient();

  const [calForm, setCalForm] = useState({
    code: "",
    name_fa: "",
    name_en: "",
    date_format: "YYYY/MM/DD",
    datetime_format: "YYYY/MM/DD HH:mm",
    is_default: false,
    sort_order: 10,
  });

  const [countryForm, setCountryForm] = useState({
    code: "",
    alpha3_code: "",
    name_fa: "",
    name_en: "",
    phone_prefix: "+971",
    default_timezone: "Asia/Dubai",
    default_currency_code: "AED",
    default_calendar: "gregorian",
    supported_calendars: "gregorian,jalali",
    default_language: "fa",
    supported_languages: "fa,en",
    sort_order: 20,
  });

  const [currencyForm, setCurrencyForm] = useState({
    code: "",
    name_fa: "",
    name_en: "",
    symbol: "",
    decimal_places: 0,
    minor_unit: "",
    base_unit_factor: "1.000000",
    sort_order: 30,
  });

  const [fxForm, setFxForm] = useState({
    base_currency_code: "USD",
    quote_currency_code: "IRT",
    rate: "",
    source: "MANUAL",
    change_reason: "به‌روزرسانی نرخ مرجع پلتفرم",
  });

  const calendarsQ = useQuery({
    queryKey: ["admin-calendars"],
    queryFn: async () =>
      (await apiFetch<CalendarSystemItem[]>("/api/v1/settings/calendars?include_inactive=true")).data,
  });

  const countriesQ = useQuery({
    queryKey: ["admin-countries"],
    queryFn: async () =>
      (await apiFetch<CountryItem[]>("/api/v1/settings/countries?include_inactive=true")).data,
  });

  const currenciesQ = useQuery({
    queryKey: ["admin-currencies"],
    queryFn: async () =>
      (await apiFetch<CurrencyConfigItem[]>("/api/v1/settings/currencies?include_inactive=true")).data,
  });

  const fxQ = useQuery({
    queryKey: ["admin-exchange-rates"],
    queryFn: async () =>
      (await apiFetch<ExchangeRateItem[]>("/api/v1/settings/exchange-rates?include_inactive=true")).data,
  });

  const fxHistQ = useQuery({
    queryKey: ["admin-exchange-rate-history"],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<ExchangeRateHistoryItem[]>("/api/v1/settings/exchange-rates/history", {
          token: accessToken,
        })
      ).data,
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["admin-calendars"] });
    qc.invalidateQueries({ queryKey: ["admin-countries"] });
    qc.invalidateQueries({ queryKey: ["admin-currencies"] });
    qc.invalidateQueries({ queryKey: ["admin-exchange-rates"] });
    qc.invalidateQueries({ queryKey: ["admin-exchange-rate-history"] });
    qc.invalidateQueries({ queryKey: ["settings-localization"] });
    qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
  };

  const upsertCalendarMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/settings/calendars", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ ...calForm, code: calForm.code.trim().toLowerCase(), is_active: true }),
      }),
    onSuccess: () => {
      setCalForm({
        code: "",
        name_fa: "",
        name_en: "",
        date_format: "YYYY/MM/DD",
        datetime_format: "YYYY/MM/DD HH:mm",
        is_default: false,
        sort_order: 10,
      });
      onNotice("تقویم جدید ثبت/به‌روزرسانی شد.");
      invalidateAll();
    },
    onError: (e: Error) => onError(e.message),
  });

  const toggleCalendarMut = useMutation({
    mutationFn: async ({ code, is_active, is_default }: { code: string; is_active?: boolean; is_default?: boolean }) =>
      apiFetch(`/api/v1/settings/calendars/${encodeURIComponent(code)}/toggle`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ is_active, is_default }),
      }),
    onSuccess: () => {
      onNotice("وضعیت تقویم به‌روزرسانی شد.");
      invalidateAll();
    },
    onError: (e: Error) => onError(e.message),
  });

  const upsertCountryMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/settings/countries", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          code: countryForm.code.trim().toUpperCase(),
          alpha3_code: countryForm.alpha3_code.trim().toUpperCase(),
          name_fa: countryForm.name_fa.trim(),
          name_en: countryForm.name_en.trim(),
          phone_prefix: countryForm.phone_prefix.trim(),
          default_timezone: countryForm.default_timezone.trim(),
          default_currency_code: countryForm.default_currency_code.trim().toUpperCase(),
          default_calendar: countryForm.default_calendar.trim().toLowerCase(),
          supported_calendars: countryForm.supported_calendars
            .split(",")
            .map((s) => s.trim().toLowerCase())
            .filter(Boolean),
          default_language: countryForm.default_language.trim().toLowerCase(),
          supported_languages: countryForm.supported_languages
            .split(",")
            .map((s) => s.trim().toLowerCase())
            .filter(Boolean),
          sort_order: Number(countryForm.sort_order || 100),
          is_active: true,
        }),
      }),
    onSuccess: () => {
      setCountryForm({
        code: "",
        alpha3_code: "",
        name_fa: "",
        name_en: "",
        phone_prefix: "+971",
        default_timezone: "Asia/Dubai",
        default_currency_code: "AED",
        default_calendar: "gregorian",
        supported_calendars: "gregorian,jalali",
        default_language: "fa",
        supported_languages: "fa,en",
        sort_order: 20,
      });
      onNotice("کشور جدید در دیتابیس ذخیره شد.");
      invalidateAll();
    },
    onError: (e: Error) => onError(e.message),
  });

  const toggleCountryMut = useMutation({
    mutationFn: async ({ code, is_active }: { code: string; is_active: boolean }) =>
      apiFetch(`/api/v1/settings/countries/${encodeURIComponent(code)}/toggle`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: () => {
      onNotice("وضعیت کشور به‌روزرسانی شد.");
      invalidateAll();
    },
    onError: (e: Error) => onError(e.message),
  });

  const upsertCurrencyMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/settings/currencies", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          code: currencyForm.code.trim().toUpperCase(),
          name_fa: currencyForm.name_fa.trim(),
          name_en: currencyForm.name_en.trim(),
          symbol: currencyForm.symbol.trim(),
          decimal_places: Number(currencyForm.decimal_places || 0),
          minor_unit: currencyForm.minor_unit.trim(),
          base_unit_factor: currencyForm.base_unit_factor || "1.000000",
          sort_order: Number(currencyForm.sort_order || 100),
          is_active: true,
        }),
      }),
    onSuccess: () => {
      setCurrencyForm({
        code: "",
        name_fa: "",
        name_en: "",
        symbol: "",
        decimal_places: 0,
        minor_unit: "",
        base_unit_factor: "1.000000",
        sort_order: 30,
      });
      onNotice("ارز جدید در جدول ارزی ذخیره شد.");
      invalidateAll();
    },
    onError: (e: Error) => onError(e.message),
  });

  const toggleCurrencyMut = useMutation({
    mutationFn: async ({ code, is_active }: { code: string; is_active: boolean }) =>
      apiFetch(`/api/v1/settings/currencies/${encodeURIComponent(code)}/toggle`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: () => {
      onNotice("وضعیت ارز به‌روزرسانی شد.");
      invalidateAll();
    },
    onError: (e: Error) => onError(e.message),
  });

  const upsertFxMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/settings/exchange-rates", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          base_currency_code: fxForm.base_currency_code.trim().toUpperCase(),
          quote_currency_code: fxForm.quote_currency_code.trim().toUpperCase(),
          rate: fxForm.rate.trim(),
          source: fxForm.source.trim(),
          is_active: true,
          change_reason: fxForm.change_reason.trim(),
        }),
      }),
    onSuccess: () => {
      setFxForm((f) => ({ ...f, rate: "" }));
      onNotice("نرخ تبدیل Decimal ذخیره و در محاسبات زنده اعمال شد.");
      invalidateAll();
    },
    onError: (e: Error) => onError(e.message),
  });

  return (
    <div className="space-y-6">
      {/* 1. Calendars */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <Calendar className="h-5 w-5 text-teal-700 dark:text-teal-400" />
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            مدیریت نظام‌های تقویم (Gregorian / Jalali و قالب تاریخ)
          </h2>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            upsertCalendarMut.mutate();
          }}
          className="grid grid-cols-1 gap-2 sm:grid-cols-6"
        >
          <input
            required
            dir="ltr"
            placeholder="کد (jalali)"
            value={calForm.code}
            onChange={(e) => setCalForm({ ...calForm, code: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            required
            placeholder="نام فارسی"
            value={calForm.name_fa}
            onChange={(e) => setCalForm({ ...calForm, name_fa: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="نام انگلیسی"
            value={calForm.name_en}
            onChange={(e) => setCalForm({ ...calForm, name_en: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="قالب تاریخ"
            value={calForm.date_format}
            onChange={(e) => setCalForm({ ...calForm, date_format: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <label className="flex items-center gap-1.5 px-2 text-xs">
            <input
              type="checkbox"
              checked={calForm.is_default}
              onChange={(e) => setCalForm({ ...calForm, is_default: e.target.checked })}
              className="accent-teal-700"
            />
            پیش‌فرض
          </label>
          <button
            type="submit"
            disabled={upsertCalendarMut.isPending}
            className="inline-flex h-9 items-center justify-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-3.5 w-3.5" />
            ثبت تقویم
          </button>
        </form>

        {calendarsQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {(calendarsQ.data || []).map((cal) => (
              <div
                key={cal.code}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/40"
              >
                <div>
                  <div className="font-bold text-slate-900 dark:text-slate-100">
                    {cal.name_fa} ({cal.code})
                  </div>
                  <div className="font-mono text-[10px] text-slate-500">
                    {cal.date_format} | {cal.is_default ? "تقویم پیش‌فرض" : "ثانویه"}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {!cal.is_default && (
                    <button
                      type="button"
                      onClick={() => toggleCalendarMut.mutate({ code: cal.code, is_default: true })}
                      className="text-[11px] font-semibold text-amber-700 dark:text-amber-400"
                    >
                      پیش‌فرض کن
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() =>
                      toggleCalendarMut.mutate({ code: cal.code, is_active: cal.is_active === false })
                    }
                    className="text-[11px] font-semibold text-teal-700 dark:text-teal-400"
                  >
                    {cal.is_active === false ? "فعال کردن" : "غیرفعال کردن"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. Countries */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <Globe2 className="h-5 w-5 text-teal-700 dark:text-teal-400" />
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            مدیریت پویای کشورها، پیش‌شماره‌ها و منطقه زمانی
          </h2>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            upsertCountryMut.mutate();
          }}
          className="grid grid-cols-1 gap-2 sm:grid-cols-6"
        >
          <input
            required
            dir="ltr"
            maxLength={2}
            placeholder="ISO-2 (مثال: AE)"
            value={countryForm.code}
            onChange={(e) => setCountryForm({ ...countryForm, code: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            required
            placeholder="نام فارسی کشور"
            value={countryForm.name_fa}
            onChange={(e) => setCountryForm({ ...countryForm, name_fa: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            required
            dir="ltr"
            placeholder="نام انگلیسی"
            value={countryForm.name_en}
            onChange={(e) => setCountryForm({ ...countryForm, name_en: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="پیش‌شماره (+971)"
            value={countryForm.phone_prefix}
            onChange={(e) => setCountryForm({ ...countryForm, phone_prefix: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="Timezone (Asia/Dubai)"
            value={countryForm.default_timezone}
            onChange={(e) => setCountryForm({ ...countryForm, default_timezone: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="ارز پیش‌فرض (AED)"
            value={countryForm.default_currency_code}
            onChange={(e) =>
              setCountryForm({ ...countryForm, default_currency_code: e.target.value })
            }
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="تقویم پیش‌فرض"
            value={countryForm.default_calendar}
            onChange={(e) => setCountryForm({ ...countryForm, default_calendar: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="تقویم‌های مجاز (csv)"
            value={countryForm.supported_calendars}
            onChange={(e) => setCountryForm({ ...countryForm, supported_calendars: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="زبان پیش‌فرض (fa)"
            value={countryForm.default_language}
            onChange={(e) => setCountryForm({ ...countryForm, default_language: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            dir="ltr"
            placeholder="ISO-3 (ARE)"
            value={countryForm.alpha3_code}
            onChange={(e) => setCountryForm({ ...countryForm, alpha3_code: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            type="number"
            placeholder="ترتیب"
            value={countryForm.sort_order}
            onChange={(e) => setCountryForm({ ...countryForm, sort_order: Number(e.target.value) })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
          />
          <button
            type="submit"
            disabled={upsertCountryMut.isPending}
            className="inline-flex h-9 items-center justify-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-3.5 w-3.5" />
            ذخیره کشور
          </button>
        </form>

        {countriesQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-right text-xs">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                <tr>
                  <th className="py-2 px-2">کشور</th>
                  <th className="py-2 px-2">کد ISO</th>
                  <th className="py-2 px-2">پیش‌شماره</th>
                  <th className="py-2 px-2">منطقه زمانی</th>
                  <th className="py-2 px-2">تقویم / ارز</th>
                  <th className="py-2 px-2">وضعیت</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(countriesQ.data || []).map((c) => (
                  <tr key={c.code}>
                    <td className="py-2.5 px-2 font-bold text-slate-900 dark:text-slate-100">
                      {c.name_fa} <span className="font-normal text-slate-400">({c.name_en})</span>
                    </td>
                    <td className="py-2.5 px-2 font-mono">{c.code}</td>
                    <td className="py-2.5 px-2 font-mono tabular-nums" dir="ltr">
                      {c.phone_prefix}
                    </td>
                    <td className="py-2.5 px-2 font-mono text-slate-600 dark:text-slate-300">
                      {c.default_timezone || c.timezone}
                    </td>
                    <td className="py-2.5 px-2 font-mono">
                      {c.default_calendar} / {c.default_currency_code || c.default_currency}
                    </td>
                    <td className="py-2.5 px-2">
                      <button
                        type="button"
                        onClick={() =>
                          toggleCountryMut.mutate({ code: c.code, is_active: c.is_active === false })
                        }
                        className={`font-semibold ${
                          c.is_active === false
                            ? "text-rose-600 dark:text-rose-400"
                            : "text-emerald-700 dark:text-emerald-400"
                        }`}
                      >
                        {c.is_active === false ? "غیرفعال (فعال کن)" : "فعال"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 3. Currencies + Decimal FX Rates */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="surface-card rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
            <Coins className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              ارزهای سیستم (دقت Decimal)
            </h2>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              upsertCurrencyMut.mutate();
            }}
            className="grid grid-cols-2 gap-2 sm:grid-cols-4"
          >
            <input
              required
              dir="ltr"
              placeholder="کد (AED)"
              value={currencyForm.code}
              onChange={(e) => setCurrencyForm({ ...currencyForm, code: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              required
              placeholder="نام فارسی"
              value={currencyForm.name_fa}
              onChange={(e) => setCurrencyForm({ ...currencyForm, name_fa: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              placeholder="نماد (د.إ)"
              value={currencyForm.symbol}
              onChange={(e) => setCurrencyForm({ ...currencyForm, symbol: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              dir="ltr"
              placeholder="ضریب پایه Decimal"
              value={currencyForm.base_unit_factor}
              onChange={(e) =>
                setCurrencyForm({ ...currencyForm, base_unit_factor: e.target.value })
              }
              className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              dir="ltr"
              placeholder="نام انگلیسی"
              value={currencyForm.name_en}
              onChange={(e) => setCurrencyForm({ ...currencyForm, name_en: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              type="number"
              min={0}
              max={6}
              placeholder="رقم اعشار"
              value={currencyForm.decimal_places}
              onChange={(e) =>
                setCurrencyForm({ ...currencyForm, decimal_places: Number(e.target.value) })
              }
              className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              placeholder="واحد جزء"
              value={currencyForm.minor_unit}
              onChange={(e) => setCurrencyForm({ ...currencyForm, minor_unit: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <button
              type="submit"
              disabled={upsertCurrencyMut.isPending}
              className="inline-flex h-9 items-center justify-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Plus className="h-3.5 w-3.5" />
              ثبت ارز
            </button>
          </form>

          {currenciesQ.isLoading ? (
            <LoadingState />
          ) : (
            <div className="space-y-2">
              {(currenciesQ.data || []).map((cur) => (
                <div
                  key={cur.code}
                  className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2.5 text-xs dark:border-slate-800 dark:bg-slate-800/40"
                >
                  <div>
                    <div className="font-bold text-slate-900 dark:text-slate-100">
                      {cur.name_fa} ({cur.code}) — نماد: {cur.symbol || cur.code}
                    </div>
                    <div className="font-mono text-[11px] text-slate-500 tabular-nums">
                      ضریب پایه: {cur.base_unit_factor || cur.exchange_rate_to_base} | اعشار:{" "}
                      {cur.decimal_places}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      toggleCurrencyMut.mutate({ code: cur.code, is_active: cur.is_active === false })
                    }
                    className={`font-semibold ${
                      cur.is_active === false
                        ? "text-rose-600 dark:text-rose-400"
                        : "text-emerald-700 dark:text-emerald-400"
                    }`}
                  >
                    {cur.is_active === false ? "غیرفعال" : "فعال"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Exchange Rates & History */}
        <div className="surface-card rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
            <ArrowLeftRight className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              نرخ‌های تبدیل ارز (Decimal Only) و تاریخچه
            </h2>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              upsertFxMut.mutate();
            }}
            className="grid grid-cols-2 gap-2 sm:grid-cols-5"
          >
            <input
              required
              dir="ltr"
              placeholder="مبدأ (USD)"
              value={fxForm.base_currency_code}
              onChange={(e) => setFxForm({ ...fxForm, base_currency_code: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              required
              dir="ltr"
              placeholder="مقصد (IRT)"
              value={fxForm.quote_currency_code}
              onChange={(e) => setFxForm({ ...fxForm, quote_currency_code: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              required
              dir="ltr"
              placeholder="نرخ دقیق (مثلاً 65000)"
              value={fxForm.rate}
              onChange={(e) => setFxForm({ ...fxForm, rate: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
            />
            <input
              placeholder="علت تغییر نرخ"
              value={fxForm.change_reason}
              onChange={(e) => setFxForm({ ...fxForm, change_reason: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <button
              type="submit"
              disabled={upsertFxMut.isPending}
              className="inline-flex h-9 items-center justify-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
            >
              ثبت نرخ
            </button>
          </form>

          {fxQ.isLoading ? (
            <LoadingState />
          ) : (
            <div className="space-y-2 max-h-52 overflow-y-auto">
              {(fxQ.data || []).map((fx) => (
                <div
                  key={fx.id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-xs dark:border-slate-800 dark:bg-slate-800/40"
                >
                  <div className="font-mono font-bold text-slate-900 dark:text-slate-100" dir="ltr">
                    1 {fx.base_currency_code} = {fx.rate} {fx.quote_currency_code}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {fx.source} · <DateDisplay value={fx.effective_at} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {fxHistQ.data && fxHistQ.data.length > 0 && (
            <div className="border-t border-slate-200 pt-3 dark:border-slate-800 space-y-2">
              <div className="text-xs font-bold text-slate-700 dark:text-slate-300">
                تاریخچه اخیر تغییرات نرخ تبدیل
              </div>
              <div className="max-h-40 space-y-1.5 overflow-y-auto text-[11px]">
                {fxHistQ.data.slice(0, 12).map((h) => (
                  <div
                    key={h.id}
                    className="flex items-center justify-between rounded border border-slate-200 px-2.5 py-1.5 dark:border-slate-800"
                  >
                    <span className="font-mono tabular-nums" dir="ltr">
                      {h.base_currency_code}→{h.quote_currency_code}: {h.previous_rate ?? "—"} ➔{" "}
                      {h.new_rate}
                    </span>
                    <span className="text-slate-500">
                      {h.changed_by_name} · <DateDisplay value={h.created_at} />
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
