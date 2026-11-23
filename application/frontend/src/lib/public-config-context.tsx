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

  // The platform-wide visual preset is public configuration, not a per-user
  // light/dark preference. Apply it at the document root so every route and
  // every shared component receives the same design tokens.
  useEffect(() => {
    if (typeof document === "undefined" || !data) return;
    const allowed = new Set(["glass", "neo", "organic", "custom"]);
    const requested = data.public_settings?.["branding.default_theme_preset"];
    const preset = typeof requested === "string" && allowed.has(requested)
      ? requested
      : "glass";
    const root = document.documentElement;
    root.dataset.visualStyle = preset;
    if (preset === "custom") {
      const customTokens: Record<string, string> = { "--accent-primary": "--custom-accent", "--accent-secondary": "--custom-secondary", "--bg-canvas": "--custom-canvas", "--bg-surface": "--custom-surface" };
      for (const [token, key] of Object.entries(customTokens)) {
        try { const value = localStorage.getItem(`toure-theme-${key}`); if (value && /^#[0-9a-f]{6}$/i.test(value)) root.style.setProperty(token, value); } catch { /* storage may be unavailable */ }
      }
    } else {
      ["--accent-primary", "--accent-secondary", "--bg-canvas", "--bg-surface"].forEach((token) => root.style.removeProperty(token));
    }
  }, [data]);

  // Visual effects are a separate, per-browser presentation layer. They do not
  // alter the platform color preset or the user's light/dark preference.
  useEffect(() => {
    if (typeof document === "undefined") return;
    try {
      const saved = localStorage.getItem("toure-visual-effects");
      const allowedEffects = new Set(["aurora", "obsidian", "crystal", "holographic", "off"]);
      const prefs = JSON.parse(localStorage.getItem("toure-visual-experience-settings") || "{}") as { enabled?: boolean };
      document.documentElement.dataset.visualEffects = prefs.enabled === false ? "off" : (saved && allowedEffects.has(saved) ? saved : "aurora");
    } catch {
      document.documentElement.dataset.visualEffects = "aurora";
    }
  }, []);

  // Favicon is managed through the existing BrandMediaSlot registry. Keep
  // Next's bundled icon as a safe fallback until the public bootstrap arrives.
  useEffect(() => {
    if (typeof document === "undefined" || !data) return;
    const configured = data.branding?.favicon?.image_url?.trim() || "/icon.svg";
    // Older seeded databases point at /images/brand-mark.svg, which is not
    // shipped in the public directory. Keep the real bundled icon as fallback.
    const faviconUrl = configured === "/images/brand-mark.svg" ? "/icon.svg" : configured;
    const links = Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel~="icon"]'));
    const primary = links[0] || document.createElement("link");
    primary.rel = "icon";
    primary.href = faviconUrl;
    const extension = faviconUrl.split("?")[0].split(".").pop()?.toLowerCase();
    if (extension === "ico") primary.type = "image/x-icon";
    else if (extension === "png") primary.type = "image/png";
    else if (extension === "svg") primary.type = "image/svg+xml";
    if (!primary.parentNode) document.head.appendChild(primary);
    // Remove duplicate static icon declarations so browsers don't randomly
    // keep displaying the bundled placeholder instead of the configured file.
    links.slice(1).forEach((link) => link.remove());
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
