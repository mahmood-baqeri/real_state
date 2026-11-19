// Path: frontend/src/components/Providers.tsx

"use client";

import React, { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { ToastProvider } from "@/components/ui/ToastProvider";
import { OfflineIndicator } from "@/components/pwa/PWAInstallButton";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            retry: 1,
          },
        },
      })
  );

  useEffect(() => {
    if (typeof window !== "undefined" && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            {children}
            <OfflineIndicator />
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
