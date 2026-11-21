"use client";

import React, { createContext, useContext, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./api-client";
import { setRuntimeLocalizationRegistry } from "./formatters";
import type {
  BrandMediaSlotItem,
  CalendarSystemItem,
  CountryItem,
  CurrencyConfigItem,
  ExchangeRateItem,
  PublicBootstrapPayload,
  PublicLegalSummaryItem,
  SiteContentBlockItem,
} from "./types";

interface PublicConfigContextValue {
  bootstrap: PublicBootstrapPayload | null;
  isLoading: boolean;
  publicSettings: Record<string, unknown>;
  branding: Record<string, BrandMediaSlotItem>;
  contentBlocks: Record<string, SiteContentBlockItem>;
  legalDocuments: PublicLegalSummaryItem[];
  countries: CountryItem[];
  calendars: CalendarSystemItem[];
  currencies: CurrencyConfigItem[];
  exchangeRates: ExchangeRateItem[];
  getSetting: <T = unknown>(key: string, fallback: T) => T;
  getBrandAsset: (slotKey: string, dark?: boolean, fallbackUrl?: string) => string;
  getContentBlock: (slugKey: string) => SiteContentBlockItem | undefined;
  refreshBootstrap: () => void;
}

const PublicConfigContext = createContext<PublicConfigContextValue | null>(null);

export function PublicConfigProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["public-bootstrap"],
    queryFn: async () =>
      (await apiFetch<PublicBootstrapPayload>("/api/v1/settings/public-bootstrap")).data,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (data) {
      setRuntimeLocalizationRegistry(data.currencies || [], data.exchange_rates || []);
    }
  }, [data]);

  const value = useMemo<PublicConfigContextValue>(() => {
    const publicSettings = data?.public_settings || {};
    const branding = data?.branding || {};
    const contentBlocks = data?.content_blocks || {};

    return {
      bootstrap: data || null,
      isLoading,
      publicSettings,
      branding,
      contentBlocks,
      legalDocuments: data?.legal_documents || [],
      countries: data?.countries || [],
      calendars: data?.calendars || [],
      currencies: data?.currencies || [],
      exchangeRates: data?.exchange_rates || [],
      getSetting: <T,>(key: string, fallback: T): T => {
        if (key in publicSettings && publicSettings[key] !== null && publicSettings[key] !== undefined) {
          return publicSettings[key] as T;
        }
        return fallback;
      },
      getBrandAsset: (slotKey: string, dark = false, fallbackUrl = ""): string => {
        const slot = branding[slotKey];
        if (!slot) return fallbackUrl;
        if (dark && slot.dark_image_url) return slot.dark_image_url;
        return slot.image_url || fallbackUrl;
      },
      getContentBlock: (slugKey: string) => contentBlocks[slugKey],
      refreshBootstrap: () => {
        void refetch();
      },
    };
  }, [data, isLoading, refetch]);

  return <PublicConfigContext.Provider value={value}>{children}</PublicConfigContext.Provider>;
}

export function usePublicConfig(): PublicConfigContextValue {
  const ctx = useContext(PublicConfigContext);
  if (!ctx) {
    return {
      bootstrap: null,
      isLoading: false,
      publicSettings: {},
      branding: {},
      contentBlocks: {},
      legalDocuments: [],
      countries: [],
      calendars: [],
      currencies: [],
      exchangeRates: [],
      getSetting: <T,>(_key: string, fallback: T) => fallback,
      getBrandAsset: (_slotKey: string, _dark = false, fallbackUrl = "") => fallbackUrl,
      getContentBlock: () => undefined,
      refreshBootstrap: () => undefined,
    };
  }
  return ctx;
}
