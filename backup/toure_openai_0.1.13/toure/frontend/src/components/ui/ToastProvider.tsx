"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

type ToastTone = "success" | "error" | "info";

interface ToastItem {
  id: string;
  tone: ToastTone;
  title: string;
  description?: string;
}

interface ToastContextValue {
  pushToast: (toast: Omit<ToastItem, "id">) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const [mounted, setMounted] = useState(false);
  const [serverBusy, setServerBusy] = useState(false);

  useEffect(() => {
    setMounted(true);
    let delayTimer: ReturnType<typeof setTimeout> | undefined;
    const onRequestCount = (event: Event) => {
      const count = Number((event as CustomEvent<{ count?: number }>).detail?.count ?? 0);
      if (count > 0) {
        if (!delayTimer) delayTimer = setTimeout(() => setServerBusy(true), 160);
      } else {
        if (delayTimer) clearTimeout(delayTimer);
        delayTimer = undefined;
        setServerBusy(false);
      }
    };
    window.addEventListener("bonyan-api-request-count", onRequestCount);
    return () => { if (delayTimer) clearTimeout(delayTimer); window.removeEventListener("bonyan-api-request-count", onRequestCount); };
  }, []);

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const pushToast = useCallback(
    (toast: Omit<ToastItem, "id">) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setItems((prev) => [...prev.slice(-3), { ...toast, id }]);
      setTimeout(() => dismiss(id), 4500);
    },
    [dismiss]
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      pushToast,
      success: (title, description) => pushToast({ tone: "success", title, description }),
      error: (title, description) => pushToast({ tone: "error", title, description }),
      info: (title, description) => pushToast({ tone: "info", title, description }),
    }),
    [pushToast]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      {mounted && createPortal(
        <>
          {serverBusy && <>
            <div aria-label="در حال ارتباط با سرور" role="status" className="fixed z-[10040] h-[3px] overflow-hidden rounded-b-full bg-slate-200/80 dark:bg-slate-800/80" style={{ left: 20, top: 0, width: "min(360px, calc(100vw - 40px))" }}><div className="h-full w-1/3 animate-[dashboard-progress_1.1s_ease-in-out_infinite] rounded-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-teal-400 shadow-[0_0_10px_rgba(45,212,191,.6)]" /></div>
            <div className="fixed z-[10040] rounded-full border border-slate-200/80 bg-white/90 px-3 py-1.5 text-[11px] font-medium text-slate-600 shadow-md backdrop-blur dark:border-slate-700 dark:bg-slate-900/90 dark:text-slate-300" style={{ left: 20, top: 14, maxWidth: "calc(100vw - 40px)" }}><span className="mr-1.5 inline-block h-2 w-2 animate-pulse rounded-full bg-teal-500 align-middle" />در حال دریافت اطلاعات از سرور</div>
          </>}
          <div aria-live="polite" className="pointer-events-none fixed z-[10050] flex flex-col items-start gap-2" style={{ left: 20, top: serverBusy ? 58 : 20, width: "min(360px, calc(100vw - 40px))", direction: "ltr" }}>
        {items.map((item) => {
          const toneStyle =
            item.tone === "success"
              ? "border-emerald-200 bg-white text-emerald-900 dark:border-emerald-800/70 dark:bg-slate-900 dark:text-emerald-200"
              : item.tone === "error"
              ? "border-rose-200 bg-white text-rose-900 dark:border-rose-800/70 dark:bg-slate-900 dark:text-rose-200"
              : "border-slate-200 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

          const icon =
            item.tone === "success" ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            ) : item.tone === "error" ? (
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400" />
            ) : (
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-teal-600 dark:text-teal-400" />
            );

          return (
            <div
              key={item.id}
              role="status"
              dir="rtl" className={`pointer-events-auto w-full flex items-start justify-between gap-3 rounded-xl border p-3.5 shadow-lg backdrop-blur-md ${toneStyle}`}
            >
              <div className="flex items-start gap-2.5">
                {icon}
                <div className="min-w-0">
                  <div className="text-xs font-bold">{item.title}</div>
                  {item.description && (
                    <div className="mt-0.5 text-[11px] opacity-85">{item.description}</div>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => dismiss(item.id)}
                aria-label="بستن اعلان"
                className="rounded p-1 opacity-60 hover:opacity-100"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
          </div>
        </>, document.body
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
