"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Lock, LogOut, Save, Search, ShieldAlert, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AdminSessionItem, SecurityEventItem, SystemSettingItem } from "@/lib/types";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { LoadingState } from "@/components/ui/StateNotice";

interface Props {
  onNotice: (msg: string) => void;
  onError: (msg: string) => void;
}

export function SecurityConsoleTab({ onNotice, onError }: Props) {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();

  const [suspiciousOnly, setSuspiciousOnly] = useState(false);
  const [searchQ, setSearchQ] = useState("");
  const [draftSec, setDraftSec] = useState<Record<string, unknown>>({});
  const [panicOpen, setPanicOpen] = useState(false);
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [excludeCurrent, setExcludeCurrent] = useState(true);

  const secRegQ = useQuery({
    queryKey: ["security-registry-settings", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SystemSettingItem[]>("/api/v1/settings/registry?category=SECURITY", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const sessionsQ = useQuery({
    queryKey: ["admin-sessions", suspiciousOnly, searchQ],
    enabled: !!accessToken,
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (suspiciousOnly) qs.set("suspicious_only", "true");
      if (searchQ.trim()) qs.set("q", searchQ.trim());
      return (
        await apiFetch<AdminSessionItem[]>(`/api/v1/auth/admin/sessions?${qs.toString()}`, {
          token: accessToken,
        })
      ).data;
    },
  });

  const eventsQ = useQuery({
    queryKey: ["admin-security-events"],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SecurityEventItem[]>("/api/v1/auth/admin/security-events", {
          token: accessToken,
        })
      ).data,
  });

  const savePolicyMut = useMutation({
    mutationFn: async () => {
      const updates = Object.entries(draftSec).map(([key, val]) => {
        const orig = (secRegQ.data || []).find((x) => x.key === key);
        return {
          key,
          value: orig?.value_type === "INTEGER" ? Number(val) : val,
        };
      });
      return apiFetch("/api/v1/settings/registry", {
        method: "PUT",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ updates, change_reason: "به‌روزرسانی سیاست‌های امنیتی پلتفرم" }),
      });
    },
    onSuccess: () => {
      setDraftSec({});
      onNotice("سیاست‌های امنیتی در PostgreSQL ذخیره و اعمال شدند.");
      qc.invalidateQueries({ queryKey: ["security-registry-settings"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const revokeSessionMut = useMutation({
    mutationFn: async (sessionId: string) =>
      apiFetch(`/api/v1/auth/admin/sessions/${sessionId}`, {
        method: "DELETE",
        token: accessToken,
      }),
    onSuccess: () => {
      onNotice("نشست انتخاب‌شده فوراً لغو شد.");
      qc.invalidateQueries({ queryKey: ["admin-sessions"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const revokeUserAllMut = useMutation({
    mutationFn: async (userId: string) =>
      apiFetch<{ revoked_count: number }>(`/api/v1/auth/admin/users/${userId}/revoke-sessions`, {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: (res) => {
      onNotice(`${res.data.revoked_count} نشست فعال کاربر لغو شد.`);
      qc.invalidateQueries({ queryKey: ["admin-sessions"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const emergencyLogoutMut = useMutation({
    mutationFn: async () =>
      apiFetch<{ revoked_count: number }>("/api/v1/auth/admin/emergency-force-logout", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          password_confirm: passwordConfirm,
          exclude_current: excludeCurrent,
        }),
      }),
    onSuccess: (res) => {
      setPanicOpen(false);
      setPasswordConfirm("");
      onNotice(`خروج اضطراری سراسری اجرا شد (${res.data.revoked_count} نشست منقضی شد).`);
      qc.invalidateQueries({ queryKey: ["admin-sessions"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  return (
    <div className="space-y-6">
      {/* 1. Dynamic Security Policies */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Lock className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              سیاست‌های پویا امنیت، رمز عبور و محدودیت نرخ (Rate Limit / JWT / Brute-Force)
            </h2>
          </div>
          {Object.keys(draftSec).length > 0 && (
            <button
              type="button"
              disabled={savePolicyMut.isPending}
              onClick={() => savePolicyMut.mutate()}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Save className="h-3.5 w-3.5" />
              ذخیره سیاست‌های امنیتی
            </button>
          )}
        </div>

        {secRegQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {(secRegQ.data || []).map((s) => {
              const val = s.key in draftSec ? draftSec[s.key] : s.value;
              return (
                <div
                  key={s.id}
                  className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 space-y-2 dark:border-slate-800 dark:bg-slate-800/40"
                >
                  <div>
                    <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
                      {s.title_fa}
                    </div>
                    <div className="font-mono text-[10px] text-slate-400">{s.key}</div>
                  </div>
                  {s.value_type === "BOOLEAN" ? (
                    <label className="inline-flex cursor-pointer items-center gap-2 text-xs">
                      <input
                        type="checkbox"
                        checked={Boolean(val)}
                        onChange={(e) => setDraftSec((p) => ({ ...p, [s.key]: e.target.checked }))}
                        className="h-4 w-4 accent-teal-700"
                      />
                      {Boolean(val) ? "فعال" : "غیرفعال"}
                    </label>
                  ) : (
                    <input
                      type={s.value_type === "INTEGER" ? "number" : "text"}
                      value={String(val ?? "")}
                      onChange={(e) => setDraftSec((p) => ({ ...p, [s.key]: e.target.value }))}
                      className="h-8 w-full rounded border border-slate-300 bg-white px-2.5 font-mono text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 2. Session & Emergency Console */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              کنسول نظارت نشست‌های فعال کاربران و ابطال اضطراری
            </h2>
          </div>

          <button
            type="button"
            onClick={() => setPanicOpen(true)}
            className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-rose-300 bg-rose-50 px-3.5 text-xs font-bold text-rose-800 hover:bg-rose-100 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300"
          >
            <LogOut className="h-3.5 w-3.5" />
            خروج اجباری سراسری (Emergency Force Logout)
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="pointer-events-none absolute right-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="فیلتر بر اساس نام، شماره موبایل یا IP..."
              className="h-9 w-full rounded-lg border border-slate-300 bg-white pr-9 pl-3 text-xs dark:border-slate-700 dark:bg-slate-950"
            />
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-semibold">
            <input
              type="checkbox"
              checked={suspiciousOnly}
              onChange={(e) => setSuspiciousOnly(e.target.checked)}
              className="accent-rose-600"
            />
            فقط نشست‌های مشکوک
          </label>
        </div>

        {sessionsQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-right text-xs">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                <tr>
                  <th className="py-2 px-2">کاربر</th>
                  <th className="py-2 px-2">دستگاه / روش</th>
                  <th className="py-2 px-2">IP</th>
                  <th className="py-2 px-2">آخرین فعالیت</th>
                  <th className="py-2 px-2">ریسک</th>
                  <th className="py-2 px-2">عملیات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(sessionsQ.data || []).map((ses) => (
                  <tr
                    key={ses.id}
                    className={ses.is_suspicious ? "bg-rose-50/50 dark:bg-rose-950/20" : ""}
                  >
                    <td className="py-2.5 px-2">
                      <div className="font-bold text-slate-900 dark:text-slate-100">
                        {ses.user_name}{" "}
                        {ses.is_current && (
                          <span className="font-mono text-[10px] text-teal-600">(نشست فعلی)</span>
                        )}
                      </div>
                      <div className="font-mono text-[11px] text-slate-500" dir="ltr">
                        {ses.user_phone}
                      </div>
                    </td>
                    <td className="py-2.5 px-2">
                      <div>{ses.device_name || ses.device_type}</div>
                      <div className="font-mono text-[10px] text-slate-400">{ses.auth_method}</div>
                    </td>
                    <td className="py-2.5 px-2 font-mono" dir="ltr">
                      {ses.ip_address || "—"}
                    </td>
                    <td className="py-2.5 px-2">
                      <DateDisplay value={ses.last_active_at} withTime />
                    </td>
                    <td className="py-2.5 px-2">
                      {ses.is_suspicious ? (
                        <span className="inline-flex items-center gap-1 font-semibold text-rose-700 dark:text-rose-400">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          {ses.suspicious_reason || "مشکوک"}
                        </span>
                      ) : (
                        <span className="text-emerald-700 dark:text-emerald-400">عادی</span>
                      )}
                    </td>
                    <td className="py-2.5 px-2">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => revokeSessionMut.mutate(ses.id)}
                          className="inline-flex items-center gap-1 text-rose-700 hover:underline dark:text-rose-400"
                        >
                          <Trash2 className="h-3 w-3" />
                          ابطال نشست
                        </button>
                        <button
                          type="button"
                          onClick={() => revokeUserAllMut.mutate(ses.user_id)}
                          className="text-amber-700 hover:underline dark:text-amber-400"
                        >
                          لغو کل کاربر
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 3. Recent Security Events */}
      <div className="surface-card rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
          رویدادهای احراز هویت و تلاش‌های ورود ناموفق اخیر
        </h2>
        {eventsQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-right text-xs">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                <tr>
                  <th className="py-2 px-2">کاربر / تلفن</th>
                  <th className="py-2 px-2">IP</th>
                  <th className="py-2 px-2">نتیجه</th>
                  <th className="py-2 px-2">جزئیات</th>
                  <th className="py-2 px-2">زمان</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(eventsQ.data || []).map((ev) => (
                  <tr key={ev.id}>
                    <td className="py-2 px-2">
                      <span className="font-semibold">{ev.user_name || "ناشناس"}</span>{" "}
                      <span className="font-mono text-[11px] text-slate-500" dir="ltr">
                        ({ev.phone_number})
                      </span>
                    </td>
                    <td className="py-2 px-2 font-mono" dir="ltr">
                      {ev.ip_address || "—"}
                    </td>
                    <td className="py-2 px-2 font-semibold">
                      {ev.succeeded ? (
                        <span className="text-emerald-700 dark:text-emerald-400">موفق</span>
                      ) : (
                        <span className="text-rose-700 dark:text-rose-400">ناموفق</span>
                      )}
                    </td>
                    <td className="py-2 px-2 text-slate-500">{ev.failure_reason || "—"}</td>
                    <td className="py-2 px-2">
                      <DateDisplay value={ev.created_at} withTime />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Emergency Force Logout Confirmation Modal */}
      <ModalDrawer
        open={panicOpen}
        onClose={() => setPanicOpen(false)}
        title="تأیید خروج اضطراری سراسری کاربران"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            emergencyLogoutMut.mutate();
          }}
          className="space-y-4"
        >
          <p className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
            با اجرای این دستور، کلیه نشست‌های فعال JWT در سطح کل پلتفرم باطل شده و کاربران موظف به
            ورود مجدد خواهند شد.
          </p>
          <div>
            <label className="mb-1 block text-xs font-semibold">
              رمز عبور مدیر ارشد جهت تأیید نهایی
            </label>
            <input
              required
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              placeholder="رمز عبور خود را وارد کنید..."
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm dark:border-slate-700 dark:bg-slate-950"
            />
          </div>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={excludeCurrent}
              onChange={(e) => setExcludeCurrent(e.target.checked)}
              className="accent-teal-700"
            />
            نشست فعلی خودِ من حفظ شود
          </label>
          <button
            type="submit"
            disabled={emergencyLogoutMut.isPending}
            className="h-10 w-full rounded-lg bg-rose-700 text-xs font-bold text-white hover:bg-rose-800 disabled:opacity-50"
          >
            اجرای ابطال سراسری نشست‌ها
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
