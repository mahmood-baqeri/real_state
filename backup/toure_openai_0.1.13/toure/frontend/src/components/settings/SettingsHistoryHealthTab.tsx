"use client";

import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, CheckCircle2, Database, History, RotateCcw, Server, XCircle } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa } from "@/lib/formatters";
import type { SystemHealthPayload, SystemSettingHistoryItem } from "@/lib/types";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { LoadingState } from "@/components/ui/StateNotice";

interface Props {
  onNotice: (msg: string) => void;
  onError: (msg: string) => void;
}

export function SettingsHistoryHealthTab({ onNotice, onError }: Props) {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();

  const historyQ = useQuery({
    queryKey: ["settings-history", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SystemSettingHistoryItem[]>("/api/v1/settings/registry/history", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const healthQ = useQuery({
    queryKey: ["settings-health"],
    enabled: !!accessToken && effectiveRole === "SUPER_ADMIN",
    queryFn: async () =>
      (
        await apiFetch<SystemHealthPayload>("/api/v1/settings/health", {
          token: accessToken,
        })
      ).data,
  });

  const rollbackMut = useMutation({
    mutationFn: async (historyId: string) =>
      apiFetch(`/api/v1/settings/registry/rollback/${historyId}`, {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: () => {
      onNotice("مقدار قبلی تنظیم با موفقیت بازیابی و کش سیستم به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["settings-history"] });
      qc.invalidateQueries({ queryKey: ["settings-registry"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  return (
    <div className="space-y-6">
      {/* System Health & Environment Status (SuperAdmin only, secret values never exposed) */}
      {effectiveRole === "SUPER_ADMIN" && (
        <div className="surface-card rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
            <Server className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              سلامت زیرساخت و وضعیت پیکربندی محرمانه (بدون افشای کلیدها)
            </h2>
          </div>

          {healthQ.isLoading ? (
            <LoadingState />
          ) : healthQ.data ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                  <div className="text-slate-500">PostgreSQL</div>
                  <div className="mt-1 flex items-center gap-1 font-bold">
                    {healthQ.data.database_ok ? (
                      <>
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        <span className="text-emerald-700 dark:text-emerald-400">متصل</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-4 w-4 text-rose-600" />
                        <span className="text-rose-700">قطع</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                  <div className="text-slate-500">Redis Cache</div>
                  <div className="mt-1 flex items-center gap-1 font-bold">
                    {healthQ.data.redis_ok ? (
                      <>
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        <span className="text-emerald-700 dark:text-emerald-400">متصل</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-4 w-4 text-amber-600" />
                        <span className="text-amber-700">غیرفعال / خطا</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                  <div className="text-slate-500">محیط اجرا</div>
                  <div className="mt-1 font-mono font-bold text-slate-900 dark:text-slate-100">
                    {healthQ.data.environment_mode}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                  <div className="text-slate-500">تعداد تنظیمات</div>
                  <div className="mt-1 font-bold tabular-nums">
                    {formatNumberFa(healthQ.data.settings_count)}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                  <div className="text-slate-500">نشست فعال / مشکوک</div>
                  <div className="mt-1 font-bold tabular-nums">
                    {formatNumberFa(healthQ.data.active_sessions_count)} /{" "}
                    <span className="text-rose-600">
                      {formatNumberFa(healthQ.data.suspicious_sessions_count)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {healthQ.data.env_status.map((env) => (
                  <div
                    key={env.key}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-800"
                  >
                    <div>
                      <div className="font-semibold">{env.label}</div>
                      <div className="font-mono text-[10px] text-slate-400">{env.key}</div>
                    </div>
                    <span
                      className={`font-semibold ${
                        env.configured
                          ? "text-emerald-700 dark:text-emerald-400"
                          : "text-amber-700 dark:text-amber-400"
                      }`}
                    >
                      {env.configured ? "پیکربندی‌شده" : "تنظیم‌نشده"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* Setting Change History & Rollback */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <History className="h-5 w-5 text-teal-700 dark:text-teal-400" />
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            تاریخچه تغییرات تنظیمات و قابلیت بازگشت (Rollback)
          </h2>
        </div>

        {historyQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-right text-xs">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                <tr>
                  <th className="py-2 px-2">کلید تنظیم</th>
                  <th className="py-2 px-2">مقدار قبلی</th>
                  <th className="py-2 px-2">مقدار جدید</th>
                  <th className="py-2 px-2">تغییردهنده</th>
                  <th className="py-2 px-2">دلیل</th>
                  <th className="py-2 px-2">زمان</th>
                  {effectiveRole === "SUPER_ADMIN" && <th className="py-2 px-2">بازگشت</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(historyQ.data || []).map((h) => (
                  <tr key={h.id}>
                    <td className="py-2.5 px-2 font-mono font-semibold text-slate-900 dark:text-slate-100">
                      {h.setting_key}
                    </td>
                    <td className="py-2.5 px-2 font-mono text-slate-500">
                      {h.is_secret ? "****" : JSON.stringify(h.previous_value)}
                    </td>
                    <td className="py-2.5 px-2 font-mono text-teal-700 dark:text-teal-400">
                      {h.is_secret ? "****" : JSON.stringify(h.new_value)}
                    </td>
                    <td className="py-2.5 px-2">{h.changed_by_name}</td>
                    <td className="py-2.5 px-2 text-slate-500">{h.change_reason || "—"}</td>
                    <td className="py-2.5 px-2">
                      <DateDisplay value={h.created_at} withTime />
                    </td>
                    {effectiveRole === "SUPER_ADMIN" && (
                      <td className="py-2.5 px-2">
                        <button
                          type="button"
                          disabled={rollbackMut.isPending}
                          onClick={() => rollbackMut.mutate(h.id)}
                          className="inline-flex items-center gap-1 font-semibold text-teal-700 hover:underline dark:text-teal-400"
                        >
                          <RotateCcw className="h-3 w-3" />
                          بازگشت
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                {(historyQ.data || []).length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-slate-400">
                      <Database className="mx-auto mb-1 h-4 w-4 opacity-50" />
                      هنوز تغییری ثبت نشده است.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {effectiveRole === "SUPER_ADMIN" && healthQ.data?.providers_summary && (
        <div className="surface-card rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            <Activity className="h-4 w-4 text-teal-600" />
            وضعیت سرویس‌دهنده‌های متصل
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {healthQ.data.providers_summary.map((p) => (
              <div
                key={`${p.category}-${p.provider_key}`}
                className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-800"
              >
                <div>
                  <div className="font-bold">{p.display_name}</div>
                  <div className="font-mono text-[10px] text-slate-400">
                    {p.category} · {p.provider_key}
                  </div>
                </div>
                <span
                  className={
                    p.is_active
                      ? "font-semibold text-emerald-700 dark:text-emerald-400"
                      : "text-slate-400"
                  }
                >
                  {p.is_active ? "فعال" : "غیرفعال"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
