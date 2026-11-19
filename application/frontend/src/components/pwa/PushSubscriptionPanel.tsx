// Path: frontend/src/components/pwa/PushSubscriptionPanel.tsx

"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Check, Send, Smartphone } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/ToastProvider";

interface PushPref {
  in_app_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  email_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

interface PushSubItem {
  id: string;
  endpoint: string;
  device_label: string;
  is_active: boolean;
  last_used_at: string | null;
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function PushSubscriptionPanel() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [subscribing, setSubscribing] = useState(false);

  const prefsQ = useQuery({
    queryKey: ["push-preferences"],
    enabled: !!accessToken,
    queryFn: async () => (await apiFetch<PushPref>("/api/v1/push/preferences", { token: accessToken })).data,
  });

  const subsQ = useQuery({
    queryKey: ["push-subscriptions"],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<PushSubItem[]>("/api/v1/push/subscriptions", { token: accessToken })).data,
  });

  const prefMut = useMutation({
    mutationFn: async (patch: Partial<PushPref>) =>
      apiFetch<PushPref>("/api/v1/push/preferences", {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify(patch),
      }),
    onSuccess: () => {
      toast.success("تنظیمات کانال‌های اعلان ذخیره شد.");
      qc.invalidateQueries({ queryKey: ["push-preferences"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const testMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/push/test", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      toast.success("اعلان آزمایشی پوش صف‌بندی و ارسال شد.");
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  async function handleEnableBrowserPush() {
    if (typeof window === "undefined" || !("Notification" in window) || !("serviceWorker" in navigator)) {
      toast.error("مرورگر شما از Web Push پشتیبانی نمی‌کند.");
      return;
    }
    setSubscribing(true);
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") {
        toast.info("مجوز اعلان مرورگر صادر نشد.");
        return;
      }
      const keyRes = await apiFetch<{ public_key: string }>("/api/v1/push/vapid-public-key", {
        token: accessToken,
      });
      const reg = await navigator.serviceWorker.ready;
      const appServerKey = urlBase64ToUint8Array(keyRes.data.public_key);
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: appServerKey.buffer as ArrayBuffer,
      });
      const json = sub.toJSON();
      await apiFetch("/api/v1/push/subscribe", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          endpoint: sub.endpoint,
          p256dh: json.keys?.p256dh || "",
          auth: json.keys?.auth || "",
          device_label: navigator.userAgent.slice(0, 60),
        }),
      });
      toast.success("اشتراک Web Push این دستگاه با موفقیت ثبت شد.");
      qc.invalidateQueries({ queryKey: ["push-subscriptions"] });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "خطا در فعال‌سازی پوش مرورگر");
    } finally {
      setSubscribing(false);
    }
  }

  const prefs = prefsQ.data;
  const subs = subsQ.data || [];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BellRing className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">پوش نوتیفیکیشن مرورگر (Web Push)</h2>
          </div>
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
            {subs.length} دستگاه فعال
          </span>
        </div>
        <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
          با فعال‌سازی اعلان مرورگر، تغییر وضعیت قراردادها، بازدیدهای جدید، تیکت‌ها و یادآورهای CRM حتی هنگام بسته‌بودن تب سامانه نمایش داده می‌شوند.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={subscribing}
            onClick={handleEnableBrowserPush}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            <Smartphone className="h-4 w-4" />
            {subscribing ? "در حال ثبت..." : "فعال‌سازی پوش روی این دستگاه"}
          </button>
          <button
            type="button"
            disabled={testMut.isPending}
            onClick={() => testMut.mutate()}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            <Send className="h-3.5 w-3.5" />
            ارسال اعلان آزمایشی
          </button>
        </div>
        {subs.length > 0 && (
          <div className="divide-y divide-slate-100 dark:divide-slate-800 pt-2 text-xs">
            {subs.map((s) => (
              <div key={s.id} className="flex items-center justify-between py-2">
                <span className="truncate text-slate-700 dark:text-slate-300">{s.device_label}</span>
                <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-semibold">
                  <Check className="h-3.5 w-3.5" />
                  فعال
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">تنظیمات کانال‌های دریافت اعلان</h2>
        {prefs ? (
          <div className="space-y-3 text-xs">
            {[
              { key: "in_app_enabled" as const, label: "اعلان درون‌برنامه‌ای (میز کار)" },
              { key: "push_enabled" as const, label: "اعلان لحظه‌ای مرورگر (Web Push)" },
              { key: "sms_enabled" as const, label: "پیامک رویدادهای مهم (SMS)" },
              { key: "email_enabled" as const, label: "گزارش و اعلان ایمیل" },
            ].map((item) => (
              <label
                key={item.key}
                className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 px-3 py-2.5 cursor-pointer"
              >
                <span className="font-medium text-slate-800 dark:text-slate-200">{item.label}</span>
                <input
                  type="checkbox"
                  checked={prefs[item.key]}
                  onChange={(e) => prefMut.mutate({ [item.key]: e.target.checked })}
                  className="h-4 w-4 accent-teal-700"
                />
              </label>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 dark:text-slate-400">در حال بارگذاری تنظیمات...</p>
        )}
      </section>
    </div>
  );
}
