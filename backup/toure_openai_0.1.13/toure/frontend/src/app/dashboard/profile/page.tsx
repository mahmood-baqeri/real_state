"use client";

import React, { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Laptop, Save, ShieldCheck, Trash2, UserCheck } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { usePublicConfig } from "@/lib/public-config-context";
import type { CalendarMode, CurrencyCode } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

interface SessionItem {
  id: string;
  device_name: string;
  ip_address: string | null;
  user_agent: string;
  last_active_at: string;
  is_current: boolean;
}

interface MfaSetupPayload {
  secret: string;
  otpauth_uri: string;
}

export default function ProfilePage() {
  const { user, accessToken, refreshUser } = useAuth();
  const { currencies, calendars, countries } = usePublicConfig();
  const activeCurrencies =
    currencies.length > 0
      ? currencies
      : [
          { code: "IRT", name_fa: "تومان" },
          { code: "IRR", name_fa: "ریال" },
          { code: "USD", name_fa: "دلار" },
          { code: "EUR", name_fa: "یورو" },
          { code: "AED", name_fa: "درهم" },
        ];
  const activeCalendars =
    calendars.length > 0
      ? calendars
      : [
          { code: "jalali", name_fa: "شمسی (جلالی)" },
          { code: "gregorian", name_fa: "میلادی (Gregorian)" },
        ];
  const qc = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [mfaSetup, setMfaSetup] = useState<MfaSetupPayload | null>(null);
  const [mfaCode, setMfaCode] = useState("");

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    preferred_currency: "IRT" as CurrencyCode,
    preferred_calendar: "jalali" as CalendarMode,
    timezone: "Asia/Tehran",
  });

  useEffect(() => {
    if (user) {
      setForm({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        email: user.email || "",
        preferred_currency: user.preferred_currency || "IRT",
        preferred_calendar: user.preferred_calendar || "jalali",
        timezone: user.timezone || "Asia/Tehran",
      });
    }
  }, [user]);

  const sessionsQ = useQuery({
    queryKey: ["auth-sessions"],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<SessionItem[]>("/api/v1/auth/sessions", { token: accessToken })).data,
  });

  const saveMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/auth/me", {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify(form),
      }),
    onSuccess: async () => {
      await refreshUser();
      setErrMsg(null);
      setNotice("مشخصات فردی و تنظیمات نمایش با موفقیت ذخیره شد.");
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const mfaSetupMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<MfaSetupPayload>("/api/v1/auth/mfa/setup", {
          method: "POST",
          token: accessToken,
        })
      ).data,
    onSuccess: (d) => {
      setMfaSetup(d);
      setErrMsg(null);
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const mfaEnableMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/auth/mfa/enable", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ code: mfaCode }),
      }),
    onSuccess: async () => {
      await refreshUser();
      setMfaSetup(null);
      setMfaCode("");
      setErrMsg(null);
      setNotice("احراز هویت دو مرحله‌ای (TOTP) با موفقیت فعال شد.");
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const mfaDisableMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/auth/mfa/disable", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ code: mfaCode }),
      }),
    onSuccess: async () => {
      await refreshUser();
      setMfaCode("");
      setErrMsg(null);
      setNotice("احراز هویت دو مرحله‌ای غیرفعال شد.");
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const revokeMut = useMutation({
    mutationFn: async (sessionId: string) =>
      apiFetch(`/api/v1/auth/sessions/${sessionId}`, {
        method: "DELETE",
        token: accessToken,
      }),
    onSuccess: () => {
      setNotice("نشست انتخاب‌شده با موفقیت لغو شد.");
      qc.invalidateQueries({ queryKey: ["auth-sessions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="پروفایل کاربری، امنیت و نشست‌های فعال"
        subtitle="ویرایش اطلاعات فردی، تنظیم تقویم، فعال‌سازی TOTP MFA و مدیریت دستگاه‌های متصل"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "پروفایل کاربری" }]}
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveMut.mutate();
          }}
          className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4"
        >
          <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
            <UserCheck className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">مشخصات حساب و ترجیحات</h2>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">نام</label>
              <input
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">نام خانوادگی</label>
              <input
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">ایمیل</label>
            <input
              type="email"
              dir="ltr"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">واحد پول نمایشی</label>
              <select
                value={form.preferred_currency}
                onChange={(e) => setForm({ ...form, preferred_currency: e.target.value as CurrencyCode })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
              >
                {activeCurrencies.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name_fa} ({c.code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">تقویم پیش‌فرض</label>
              <select
                value={form.preferred_calendar}
                onChange={(e) => setForm({ ...form, preferred_calendar: e.target.value as CalendarMode })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
              >
                {activeCalendars.map((cal) => (
                  <option key={cal.code} value={cal.code}>
                    {cal.name_fa}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-300">منطقه زمانی</label>
            <input
              dir="ltr"
              list="country-timezone-options"
              value={form.timezone}
              onChange={(e) => setForm({ ...form, timezone: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
            />
            <datalist id="country-timezone-options">
              {countries.map((c) => (
                <option key={c.code} value={c.timezone}>
                  {c.name_fa} ({c.timezone})
                </option>
              ))}
            </datalist>
          </div>

          <button
            type="submit"
            disabled={saveMut.isPending}
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800"
          >
            <Save className="h-4 w-4" />
            ذخیره تغییرات پروفایل
          </button>
        </form>

        <div className="space-y-6">
          {/* TOTP MFA Security Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-teal-700 dark:text-teal-400" />
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  احراز هویت دو مرحله‌ای (TOTP MFA)
                </h2>
              </div>
              <span
                className={`text-xs font-bold ${
                  user?.is_mfa_enabled
                    ? "text-emerald-700 dark:text-emerald-400"
                    : "text-slate-500 dark:text-slate-400"
                }`}
              >
                {user?.is_mfa_enabled ? "فعال" : "غیرفعال"}
              </span>
            </div>

            {user?.is_mfa_enabled ? (
              <div className="space-y-3 text-xs">
                <p className="text-slate-600 dark:text-slate-400">
                  ورود به حساب کاربری شما با کد ۶ رقمی Authenticator محافظت می‌شود. برای غیرفعال‌سازی،
                  کد فعلی برنامه Authenticator را وارد کنید:
                </p>
                <div className="flex gap-2">
                  <input
                    dir="ltr"
                    maxLength={8}
                    placeholder="کد ۶ رقمی (مثال: 123456)"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value)}
                    className="h-10 flex-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-center font-mono text-sm"
                  />
                  <button
                    type="button"
                    disabled={mfaCode.trim().length < 6 || mfaDisableMut.isPending}
                    onClick={() => mfaDisableMut.mutate()}
                    className="h-10 rounded-lg border border-rose-300 bg-rose-50 px-4 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                  >
                    غیرفعال‌سازی MFA
                  </button>
                </div>
              </div>
            ) : mfaSetup ? (
              <div className="space-y-3 text-xs">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/60 space-y-2">
                  <div className="font-semibold text-slate-700 dark:text-slate-300">
                    کلید مخفی (Secret Key) را در برنامه Google Authenticator یا 1Password وارد کنید:
                  </div>
                  <div
                    dir="ltr"
                    className="select-all rounded bg-white px-3 py-2 text-center font-mono text-sm font-bold text-teal-800 dark:bg-slate-950 dark:text-teal-300"
                  >
                    {mfaSetup.secret}
                  </div>
                  <div dir="ltr" className="truncate font-mono text-[11px] text-slate-500">
                    {mfaSetup.otpauth_uri}
                  </div>
                </div>
                <div className="flex gap-2">
                  <input
                    dir="ltr"
                    maxLength={8}
                    placeholder="کد تایید ۶ رقمی"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value)}
                    className="h-10 flex-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-center font-mono text-sm"
                  />
                  <button
                    type="button"
                    disabled={mfaCode.trim().length < 6 || mfaEnableMut.isPending}
                    onClick={() => mfaEnableMut.mutate()}
                    className="h-10 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                  >
                    تایید و فعال‌سازی
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3 text-xs">
                <p className="text-slate-600 dark:text-slate-400">
                  با فعال‌سازی ورود دو مرحله‌ای (TOTP)، امنیت دسترسی به اطلاعات مالی و مشتریان
                  آژانس افزایش می‌یابد.
                </p>
                <button
                  type="button"
                  disabled={mfaSetupMut.isPending}
                  onClick={() => mfaSetupMut.mutate()}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-4 font-semibold text-white hover:bg-teal-800"
                >
                  <KeyRound className="h-4 w-4" />
                  راه‌اندازی احراز هویت دو مرحله‌ای
                </button>
              </div>
            )}
          </div>

          {/* Active Sessions */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
              <Laptop className="h-5 w-5 text-teal-700 dark:text-teal-400" />
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">نشست‌های فعال (Active Sessions)</h2>
            </div>

            {sessionsQ.isLoading ? (
              <LoadingState />
            ) : sessionsQ.error instanceof Error ? (
              <ErrorState message={sessionsQ.error.message} onRetry={() => sessionsQ.refetch()} />
            ) : (sessionsQ.data || []).length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">نشست فعالی یافت نشد.</p>
            ) : (
              <div className="space-y-2.5">
                {sessionsQ.data?.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 p-3.5 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 dark:text-slate-100">
                          {s.device_name || "مرورگر وب"}
                        </span>
                        {s.is_current && (
                          <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800">
                            نشست فعلی
                          </span>
                        )}
                      </div>
                      <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                        IP: {s.ip_address || "—"} | آخرین فعالیت:{" "}
                        <DateDisplay value={s.last_active_at} withTime />
                      </div>
                    </div>
                    {!s.is_current && (
                      <button
                        type="button"
                        onClick={() => revokeMut.mutate(s.id)}
                        className="inline-flex items-center gap-1 rounded border border-rose-200 bg-white dark:bg-slate-900 px-2.5 py-1.5 font-semibold text-rose-700 hover:bg-rose-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        خروج نشست
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
