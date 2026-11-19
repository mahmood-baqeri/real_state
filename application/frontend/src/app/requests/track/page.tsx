"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";

interface TrackedRequest {
  tracking_code: string;
  subject: string;
  inquiry_type: string;
  status: string;
  staff_response: string;
  created_at: string;
}

export default function TrackPublicRequestPage() {
  const [trackingCode, setTrackingCode] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [result, setResult] = useState<TrackedRequest | null>(null);

  const trackMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<TrackedRequest>(
          `/api/v1/public-requests/track?tracking_code=${encodeURIComponent(trackingCode)}&phone_number=${encodeURIComponent(phoneNumber)}`
        )
      ).data,
    onSuccess: (d) => setResult(d),
    onError: () => setResult(null),
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-12 sm:px-6 space-y-6">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 space-y-5">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">پیگیری درخواست ثبت‌شده</h1>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              کد رهگیری (مثلاً REQ-1405-1001) و شماره موبایل ثبت‌شده را وارد نمایید.
            </p>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              trackMut.mutate();
            }}
            className="grid grid-cols-1 gap-3 sm:grid-cols-3"
          >
            <input
              required
              dir="ltr"
              placeholder="REQ-1405-1001"
              value={trackingCode}
              onChange={(e) => setTrackingCode(e.target.value)}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
            />
            <input
              required
              dir="ltr"
              placeholder="09123004050"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
            />
            <button
              type="submit"
              disabled={trackMut.isPending}
              className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Search className="h-4 w-4" />
              استعلام وضعیت
            </button>
          </form>

          {trackMut.error && (
            <div className="rounded-lg border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/30 p-3 text-xs text-rose-700 dark:text-rose-300">
              {trackMut.error instanceof Error ? trackMut.error.message : "درخواستی یافت نشد."}
            </div>
          )}

          {result && (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-5 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-teal-700 dark:text-teal-400">{result.tracking_code}</span>
                <StatusText status={result.status} />
              </div>
              <div className="text-sm font-bold text-slate-900 dark:text-slate-100">{result.subject}</div>
              <div className="text-slate-500 dark:text-slate-400">
                تاریخ ثبت: <DateDisplay value={result.created_at} withTime />
              </div>
              {result.staff_response && (
                <div className="rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-white dark:bg-slate-900 p-3 text-slate-700 dark:text-slate-200">
                  <div className="font-bold mb-1">پاسخ کارشناس:</div>
                  {result.staff_response}
                </div>
              )}
            </div>
          )}

          <div className="pt-2 text-xs text-slate-500 dark:text-slate-400">
            هنوز درخواستی ثبت نکرده‌اید؟{" "}
            <Link href="/requests/new" className="font-semibold text-teal-700 dark:text-teal-400 underline">
              ثبت درخواست جدید
            </Link>
          </div>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
