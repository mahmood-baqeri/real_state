import React from "react";
import { AlertCircle, CheckCircle2, Inbox, RefreshCw, LoaderCircle } from "lucide-react";

export function LoadingState({ message = "در حال بارگذاری اطلاعات..." }: { message?: string }) {
  return (
    <div role="status" aria-live="polite" className="relative overflow-hidden rounded-2xl border border-teal-100 bg-white/90 p-5 shadow-sm dark:border-teal-950 dark:bg-slate-900/90">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-teal-500 via-cyan-400 to-indigo-500" />
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300"><LoaderCircle className="h-5 w-5 animate-spin" /></div>
        <div className="min-w-0 flex-1"><div className="text-sm font-semibold text-slate-700 dark:text-slate-200">{message}</div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-full w-1/3 animate-[dashboard-progress_1.2s_ease-in-out_infinite] rounded-full bg-gradient-to-r from-teal-500 to-indigo-500" /></div></div>
      </div>
      <div className="mt-4 grid gap-2 animate-pulse"><div className="h-7 rounded-lg bg-slate-100 dark:bg-slate-800"/><div className="h-7 rounded-lg bg-slate-100 dark:bg-slate-800"/><div className="h-7 w-4/5 rounded-lg bg-slate-100 dark:bg-slate-800"/></div>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 p-5 dark:border-rose-900/70 dark:bg-rose-950/30 sm:flex-row sm:items-center">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-700 dark:text-rose-400" />
        <div>
          <p className="text-sm font-semibold text-rose-900 dark:text-rose-200">
            خطا در دریافت یا ثبت اطلاعات
          </p>
          <p className="mt-0.5 text-sm text-rose-800 dark:text-rose-300">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-rose-300 bg-white px-3.5 py-2 text-xs font-semibold text-rose-800 hover:bg-rose-100 dark:border-rose-800 dark:bg-slate-900 dark:text-rose-300 dark:hover:bg-rose-950/50"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          تلاش مجدد
        </button>
      )}
    </div>
  );
}

export function SuccessBanner({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-900 dark:border-emerald-900/70 dark:bg-emerald-950/30 dark:text-emerald-200">
      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-700 dark:text-emerald-400" />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({
  title = "موردی یافت نشد",
  description = "هیچ رکوردی مطابق با شرایط فعلی ثبت نشده است.",
  action,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
        <Inbox className="h-5 w-5" />
      </div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      <p className="mt-1 max-w-md text-xs text-slate-500 dark:text-slate-400">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
