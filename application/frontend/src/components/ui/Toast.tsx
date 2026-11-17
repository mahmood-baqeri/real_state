"use client";

import React, {
     createContext,
     useCallback,
     useContext,
     useMemo,
     useState,
} from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastTone = "success" | "error" | "info" | "warning";

interface Toast {
     id: string;
     tone: ToastTone;
     title: string;
     description?: string;
     duration?: number;
}

interface ToastContextValue {
     toasts: Toast[];
     push: (t: Omit<Toast, "id">) => void;
     success: (title: string, description?: string) => void;
     error: (title: string, description?: string) => void;
     info: (title: string, description?: string) => void;
     warning: (title: string, description?: string) => void;
     dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const toneStyles: Record<ToastTone, string> = {
     success: "border-success-500/40 bg-success-50",
     error: "border-danger-500/40 bg-danger-50",
     info: "border-info-500/40 bg-info-50",
     warning: "border-warning-500/40 bg-warning-50",
};

const toneIcon: Record<ToastTone, React.ReactNode> = {
     success: <CheckCircle2 className="h-4 w-4 text-success-600" />,
     error: <AlertCircle className="h-4 w-4 text-danger-600" />,
     info: <Info className="h-4 w-4 text-info-600" />,
     warning: <AlertTriangle className="h-4 w-4 text-warning-600" />,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
     const [toasts, setToasts] = useState<Toast[]>([]);

     const dismiss = useCallback((id: string) => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
     }, []);

     const push = useCallback(
          (t: Omit<Toast, "id">) => {
               const id = Math.random().toString(36).slice(2);
               setToasts((prev) => [...prev, { ...t, id }]);
               setTimeout(() => dismiss(id), t.duration ?? 4000);
          },
          [dismiss]
     );

     const value = useMemo<ToastContextValue>(
          () => ({
               toasts,
               push,
               success: (title, description) => push({ tone: "success", title, description }),
               error: (title, description) => push({ tone: "error", title, description }),
               info: (title, description) => push({ tone: "info", title, description }),
               warning: (title, description) => push({ tone: "warning", title, description }),
               dismiss,
          }),
          [toasts, push, dismiss]
     );

     return (
          <ToastContext.Provider value={value}>
               {children}
               <div className="pointer-events-none fixed top-4 left-4 z-[100] flex w-full max-w-sm flex-col gap-2">
                    {toasts.map((t) => (
                         <div
                              key={t.id}
                              role="alert"
                              className={cn(
                                   "pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-md animate-slide-up",
                                   toneStyles[t.tone]
                              )}
                         >
                              <span className="mt-0.5">{toneIcon[t.tone]}</span>
                              <div className="min-w-0 flex-1">
                                   <p className="text-sm font-semibold text-fg">{t.title}</p>
                                   {t.description && (
                                        <p className="mt-0.5 text-xs text-fg-secondary">{t.description}</p>
                                   )}
                              </div>
                              <button
                                   type="button"
                                   onClick={() => dismiss(t.id)}
                                   aria-label="بستن"
                                   className="-m-1 rounded-md p-1 text-fg-muted hover:bg-black/5 dark:hover:bg-white/10"
                              >
                                   <X className="h-4 w-4" />
                              </button>
                         </div>
                    ))}
               </div>
          </ToastContext.Provider>
     );
}

export function useToast(): ToastContextValue {
     const ctx = useContext(ToastContext);
     if (!ctx) throw new Error("useToast must be inside <ToastProvider>");
     return ctx;
}