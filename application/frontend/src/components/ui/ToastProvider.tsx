// Path: frontend/src/components/ui/ToastProvider.tsx

"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
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
      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-4 left-4 z-[60] flex w-full max-w-sm flex-col gap-2 px-4 sm:px-0"
      >
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
              className={`pointer-events-auto flex items-start justify-between gap-3 rounded-xl border p-3.5 shadow-lg ${toneStyle}`}
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
