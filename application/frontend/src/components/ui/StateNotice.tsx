import React from "react";
import { AlertCircle, CheckCircle2, Inbox, RefreshCw } from "lucide-react";

export function LoadingState({ message = "در حال بارگذاری اطلاعات..." }: { message?: string }) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-6">
      <div className="text-sm font-medium text-slate-600">{message}</div>
      <div className="space-y-2">
        <div className="h-9 w-full rounded-lg bg-slate-100" />
        <div className="h-9 w-full rounded-lg bg-slate-100" />
        <div className="h-9 w-4/5 rounded-lg bg-slate-100" />
      </div>
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
    <div className="flex flex-col items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 p-5 sm:flex-row sm:items-center">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-700" />
        <div>
          <p className="text-sm font-semibold text-rose-900">خطا در دریافت یا ثبت اطلاعات</p>
          <p className="mt-0.5 text-sm text-rose-800">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-rose-300 bg-white px-3.5 py-2 text-xs font-semibold text-rose-800 hover:bg-rose-100"
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
    <div className="flex items-center gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-900">
      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-700" />
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
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-500">
        <Inbox className="h-5 w-5" />
      </div>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-md text-xs text-slate-500">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
