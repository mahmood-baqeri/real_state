"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Plus, Send, ShieldCheck } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa } from "@/lib/formatters";
import type {
  SmsDeliveryLogItem,
  SmsSettingsStats,
  SmsTemplateItem,
  SystemSettingItem,
} from "@/lib/types";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { StatusText } from "@/components/ui/StatusText";
import { LoadingState } from "@/components/ui/StateNotice";

interface Props {
  onNotice: (msg: string) => void;
  onError: (msg: string) => void;
}

export function SmsCenterTab({ onNotice, onError }: Props) {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();

  const [tplForm, setTplForm] = useState({
    key: "",
    event_type: "OTP",
    name_fa: "",
    body_template: "کد تایید شما در بنیان ملک: {code}",
    sample_tokens: "code",
    provider_template_id: "",
    is_active: true,
  });

  const [testForm, setTestForm] = useState({
    phone_number: "",
    template_key: "",
    message: "پیامک آزمایشی مرکز مدیریت بنیان ملک",
  });

  const statsQ = useQuery({
    queryKey: ["sms-settings-stats", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SmsSettingsStats>("/api/v1/notifications/sms/settings", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const smsRegQ = useQuery({
    queryKey: ["sms-registry-settings", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SystemSettingItem[]>("/api/v1/settings/registry?category=SMS", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const templatesQ = useQuery({
    queryKey: ["sms-templates"],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SmsTemplateItem[]>("/api/v1/notifications/sms/templates", {
          token: accessToken,
        })
      ).data,
  });

  const logsQ = useQuery({
    queryKey: ["sms-logs", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SmsDeliveryLogItem[]>("/api/v1/notifications/sms/logs?page_size=25", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const toggleSettingMut = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: unknown }) =>
      apiFetch("/api/v1/settings/registry", {
        method: "PUT",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          updates: [{ key, value }],
          change_reason: "تغییر وضعیت رویداد یا سیاست پیامکی",
        }),
      }),
    onSuccess: () => {
      onNotice("تنظیم پیامکی ذخیره و بلافاصله اعمال شد.");
      qc.invalidateQueries({ queryKey: ["sms-settings-stats"] });
      qc.invalidateQueries({ queryKey: ["sms-registry-settings"] });
      qc.invalidateQueries({ queryKey: ["settings-registry"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const upsertTemplateMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/notifications/sms/templates", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          key: tplForm.key.trim().toLowerCase(),
          event_type: tplForm.event_type,
          name_fa: tplForm.name_fa.trim(),
          body_template: tplForm.body_template,
          sample_tokens: tplForm.sample_tokens
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          provider_template_id: tplForm.provider_template_id.trim(),
          is_active: tplForm.is_active,
        }),
      }),
    onSuccess: () => {
      setTplForm({
        key: "",
        event_type: "OTP",
        name_fa: "",
        body_template: "کد تایید شما در بنیان ملک: {code}",
        sample_tokens: "code",
        provider_template_id: "",
        is_active: true,
      });
      onNotice("قالب پیامک با موفقیت ذخیره شد.");
      qc.invalidateQueries({ queryKey: ["sms-templates"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const sendTestMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/notifications/sms/test", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          phone_number: testForm.phone_number.trim(),
          template_key: testForm.template_key || undefined,
          message: testForm.message,
        }),
      }),
    onSuccess: () => {
      onNotice("درخواست ارسال پیامک آزمایشی پردازش و در گزارش ارسال ثبت شد.");
      qc.invalidateQueries({ queryKey: ["sms-logs"] });
      qc.invalidateQueries({ queryKey: ["sms-settings-stats"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  return (
    <div className="space-y-6">
      {/* Stats Strip */}
      {statsQ.data && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="surface-card rounded-xl p-4">
            <div className="text-xs text-slate-500">وضعیت کلی سرویس</div>
            <div className="mt-1">
              <StatusText status={statsQ.data.enabled ? "ACTIVE" : "INACTIVE"} />
            </div>
          </div>
          <div className="surface-card rounded-xl p-4">
            <div className="text-xs text-slate-500">ارسال امروز / سقف روزانه</div>
            <div className="mt-1 text-base font-bold tabular-nums text-slate-900 dark:text-slate-100">
              {formatNumberFa(statsQ.data.stats.today_sent)} / {formatNumberFa(statsQ.data.daily_cap)}
            </div>
          </div>
          <div className="surface-card rounded-xl p-4">
            <div className="text-xs text-slate-500">تعرفه هر پیامک (تومان)</div>
            <div className="mt-1 text-base font-bold tabular-nums text-slate-900 dark:text-slate-100">
              {formatNumberFa(statsQ.data.cost_per_segment)}
            </div>
          </div>
          <div className="surface-card rounded-xl p-4">
            <div className="text-xs text-slate-500">ارسال موفق ماه / ناموفق</div>
            <div className="mt-1 text-base font-bold tabular-nums text-slate-900 dark:text-slate-100">
              {formatNumberFa(statsQ.data.stats.month_sent)} / {formatNumberFa(statsQ.data.stats.month_failed)}
            </div>
          </div>
        </div>
      )}

      {/* Event Toggles & Test Dispatch */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="surface-card rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
            <ShieldCheck className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              کلیدهای فعال‌سازی رویدادهای پیامکی (DB Registry)
            </h2>
          </div>
          {smsRegQ.isLoading ? (
            <LoadingState />
          ) : (
            <div className="space-y-2">
              {(smsRegQ.data || [])
                .filter((s) => s.value_type === "BOOLEAN")
                .map((s) => (
                  <label
                    key={s.id}
                    className="flex cursor-pointer items-center justify-between rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-xs dark:border-slate-800 dark:bg-slate-800/40"
                  >
                    <div>
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        {s.title_fa}
                      </div>
                      <div className="font-mono text-[10px] text-slate-400">{s.key}</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={Boolean(s.value)}
                      onChange={(e) =>
                        toggleSettingMut.mutate({ key: s.key, value: e.target.checked })
                      }
                      className="h-4 w-4 accent-teal-700"
                    />
                  </label>
                ))}
            </div>
          )}
        </div>

        {/* Test SMS Dispatcher */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendTestMut.mutate();
          }}
          className="surface-card rounded-xl p-5 space-y-3"
        >
          <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
            <Send className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              ارسال پیامک آزمایشی و بررسی لاگ
            </h2>
          </div>
          <input
            required
            dir="ltr"
            placeholder="شماره گیرنده (مثال: 09123456789)"
            value={testForm.phone_number}
            onChange={(e) => setTestForm({ ...testForm, phone_number: e.target.value })}
            className="h-9 w-full rounded-lg border border-slate-300 px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <select
            value={testForm.template_key}
            onChange={(e) => setTestForm({ ...testForm, template_key: e.target.value })}
            className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="">متن آزاد (بدون قالب)</option>
            {(templatesQ.data || []).map((t) => (
              <option key={t.key} value={t.key}>
                {t.name_fa} ({t.key})
              </option>
            ))}
          </select>
          <textarea
            rows={3}
            value={testForm.message}
            onChange={(e) => setTestForm({ ...testForm, message: e.target.value })}
            className="w-full rounded-lg border border-slate-300 p-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <button
            type="submit"
            disabled={sendTestMut.isPending}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            <Send className="h-3.5 w-3.5" />
            ارسال پیامک تست
          </button>
        </form>
      </div>

      {/* SMS Templates CRUD */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <MessageSquare className="h-5 w-5 text-teal-700 dark:text-teal-400" />
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            قالب‌های پیامکی (SMS Templates)
          </h2>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            upsertTemplateMut.mutate();
          }}
          className="grid grid-cols-1 gap-2 sm:grid-cols-5"
        >
          <input
            required
            dir="ltr"
            placeholder="کلید قالب (otp_login)"
            value={tplForm.key}
            onChange={(e) => setTplForm({ ...tplForm, key: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            required
            placeholder="نام فارسی قالب"
            value={tplForm.name_fa}
            onChange={(e) => setTplForm({ ...tplForm, name_fa: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <select
            value={tplForm.event_type}
            onChange={(e) => setTplForm({ ...tplForm, event_type: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="OTP">ورود / OTP</option>
            <option value="PASSWORD_RESET">بازیابی رمز</option>
            <option value="APPOINTMENT">قرار بازدید</option>
            <option value="DEAL">معامله</option>
            <option value="SYSTEM_ALERT">هشدار امنیتی</option>
            <option value="GENERAL">عمومی</option>
          </select>
          <input
            dir="ltr"
            placeholder="شناسه قالب در اپراتور"
            value={tplForm.provider_template_id}
            onChange={(e) => setTplForm({ ...tplForm, provider_template_id: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <button
            type="submit"
            disabled={upsertTemplateMut.isPending}
            className="inline-flex h-9 items-center justify-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-3.5 w-3.5" />
            ذخیره قالب
          </button>
          <input
            required
            placeholder="متن الگو با توکن‌ها (مثال: کد شما {code})"
            value={tplForm.body_template}
            onChange={(e) => setTplForm({ ...tplForm, body_template: e.target.value })}
            className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs sm:col-span-5 dark:border-slate-700 dark:bg-slate-950"
          />
        </form>

        {templatesQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {(templatesQ.data || []).map((t) => (
              <div
                key={t.id}
                className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs space-y-1.5 dark:border-slate-800 dark:bg-slate-800/40"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 dark:text-slate-100">{t.name_fa}</span>
                  <span className="font-mono text-[11px] text-teal-700 dark:text-teal-400">
                    {t.key} · {t.event_type}
                  </span>
                </div>
                <p className="text-slate-600 dark:text-slate-300">{t.body_template}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delivery Logs */}
      <div className="surface-card rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
          گزارش ارسال پیامک‌ها (شماره‌های گیرنده به‌صورت امن ماسک شده‌اند)
        </h2>
        {logsQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-right text-xs">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                <tr>
                  <th className="py-2 px-2">گیرنده</th>
                  <th className="py-2 px-2">رویداد</th>
                  <th className="py-2 px-2">اپراتور</th>
                  <th className="py-2 px-2">وضعیت</th>
                  <th className="py-2 px-2">توضیح</th>
                  <th className="py-2 px-2">زمان</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(logsQ.data || []).map((log) => (
                  <tr key={log.id}>
                    <td className="py-2 px-2 font-mono tabular-nums" dir="ltr">
                      {log.recipient_masked}
                    </td>
                    <td className="py-2 px-2 font-mono">{log.event_type}</td>
                    <td className="py-2 px-2 font-mono">{log.provider_key}</td>
                    <td className="py-2 px-2">
                      <StatusText status={log.status} />
                    </td>
                    <td className="py-2 px-2 text-slate-500">{log.error_message || log.message_id || "—"}</td>
                    <td className="py-2 px-2">
                      <DateDisplay value={log.created_at} withTime />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
