// Path: frontend/src/components/pwa/PWAInstallButton.tsx

"use client";

import React, { useState } from "react";
import { Download } from "lucide-react";
import { useOnlineStatus, usePWAInstall } from "@/hooks/usePWAInstall";

export function PWAInstallButton() {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [showIOSGuide, setShowIOSGuide] = useState(false);

  if (isInstalled) return null;

  if (isInstallable) {
    return (
      <button
        type="button"
        onClick={install}
        className="inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-teal-200 bg-teal-50 px-3 text-xs font-semibold text-teal-800 hover:bg-teal-100 dark:border-teal-800 dark:bg-teal-950/50 dark:text-teal-300 dark:hover:bg-teal-900/60"
      >
        <Download className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">نصب اپلیکیشن</span>
      </button>
    );
  }

  if (isIOS) {
    return (
      <>
        <button
          type="button"
          onClick={() => setShowIOSGuide(true)}
          className="inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
        >
          <Download className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">نصب در iOS</span>
        </button>
        {showIOSGuide && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4">
            <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">نصب بنیان ملک روی آیفون و آیپد</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                ۱. دکمه <strong>Share</strong> را در نوار ابزار Safari لمس کنید.<br />
                ۲. گزینه <strong>Add to Home Screen</strong> را انتخاب نمایید.
              </p>
              <button
                type="button"
                onClick={() => setShowIOSGuide(false)}
                className="mt-4 h-9 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800"
              >
                متوجه شدم
              </button>
            </div>
          </div>
        )}
      </>
    );
  }

  return null;
}

export function OfflineIndicator() {
  const isOnline = useOnlineStatus();
  if (isOnline) return null;

  return (
    <div className="fixed bottom-4 left-4 z-50 flex items-center gap-2 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white shadow-lg">
      <span className="h-2 w-2 rounded-full bg-white animate-pulse" />
      حالت آفلاین — برخی قابلیت‌ها نیاز به اتصال اینترنت دارند
    </div>
  );
}
