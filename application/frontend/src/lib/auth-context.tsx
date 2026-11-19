// Path: frontend/src/lib/auth-context.tsx

"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, STORAGE_KEY } from "./api-client";
import { resolveEffectiveRole } from "./role-navigation";
import type { CalendarMode, CurrencyCode, EffectiveRole, UserProfile } from "./types";

interface StoredAuth {
  access: string;
  refresh: string;
  user: UserProfile;
  activeAgencyId: string | null;
}

interface AuthContextValue {
  user: UserProfile | null;
  accessToken: string | null;
  activeAgencyId: string | null;
  effectiveRole: EffectiveRole;
  calendarMode: CalendarMode;
  currencyMode: CurrencyCode;
  isLoading: boolean;
  setActiveAgencyId: (id: string | null) => void;
  setCalendarMode: (mode: CalendarMode) => void;
  setCurrencyMode: (code: CurrencyCode) => void;
  login: (phoneNumber: string, password: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasPermission: (code: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [activeAgencyId, setActiveAgencyIdState] = useState<string | null>(null);
  const [calendarMode, setCalendarMode] = useState<CalendarMode>("jalali");
  const [currencyMode, setCurrencyMode] = useState<CurrencyCode>("IRT");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: StoredAuth = JSON.parse(raw);
        if (parsed.access && parsed.user) {
          setAccessToken(parsed.access);
          setUser(parsed.user);
          setActiveAgencyIdState(
            parsed.activeAgencyId ?? parsed.user.memberships?.[0]?.agency_id ?? null
          );
          setCalendarMode(parsed.user.preferred_calendar || "jalali");
          setCurrencyMode(parsed.user.preferred_currency || "IRT");
        }
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setIsLoading(false);
    }

    const onTokenRefresh = (e: Event) => {
      const detail = (e as CustomEvent<StoredAuth>).detail;
      if (detail?.access) setAccessToken(detail.access);
    };
    window.addEventListener("bonyan-token-refreshed", onTokenRefresh);
    return () => window.removeEventListener("bonyan-token-refreshed", onTokenRefresh);
  }, []);

  const persist = useCallback((next: StoredAuth | null) => {
    if (!next) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
  }, []);

  const setActiveAgencyId = useCallback(
    (id: string | null) => {
      setActiveAgencyIdState(id);
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          const parsed: StoredAuth = JSON.parse(raw);
          persist({ ...parsed, activeAgencyId: id });
        }
      } catch {
        // ignore
      }
    },
    [persist]
  );

  const login = useCallback(
    async (phoneNumber: string, password: string): Promise<UserProfile> => {
      const env = await apiFetch<{ access: string; refresh: string; user: UserProfile }>(
        "/api/v1/auth/login",
        {
          method: "POST",
          body: JSON.stringify({
            phone_number: phoneNumber,
            password,
            device_name: "Web Workspace",
          }),
        }
      );
      const defaultAgency = env.data.user.memberships?.[0]?.agency_id ?? null;
      setAccessToken(env.data.access);
      setUser(env.data.user);
      setActiveAgencyIdState(defaultAgency);
      setCalendarMode(env.data.user.preferred_calendar || "jalali");
      setCurrencyMode(env.data.user.preferred_currency || "IRT");
      persist({
        access: env.data.access,
        refresh: env.data.refresh,
        user: env.data.user,
        activeAgencyId: defaultAgency,
      });
      return env.data.user;
    },
    [persist]
  );

  const logout = useCallback(async () => {
    try {
      if (accessToken) {
        await apiFetch("/api/v1/auth/logout", {
          method: "POST",
          token: accessToken,
          skipRefresh: true,
        });
      }
    } catch {
      // ignore
    } finally {
      setAccessToken(null);
      setUser(null);
      setActiveAgencyIdState(null);
      persist(null);
    }
  }, [accessToken, persist]);

  const refreshUser = useCallback(async () => {
    if (!accessToken) return;
    const env = await apiFetch<UserProfile>("/api/v1/auth/me", {
      token: accessToken,
      agencyId: activeAgencyId,
    });
    setUser(env.data);
    setCalendarMode(env.data.preferred_calendar || "jalali");
    setCurrencyMode(env.data.preferred_currency || "IRT");
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: StoredAuth = JSON.parse(raw);
        persist({ ...parsed, user: env.data });
      }
    } catch {
      // ignore
    }
  }, [accessToken, activeAgencyId, persist]);

  const activeMembership = useMemo(
    () => user?.memberships?.find((m) => m.agency_id === activeAgencyId) || user?.memberships?.[0],
    [user, activeAgencyId]
  );

  const effectiveRole = useMemo(
    () => resolveEffectiveRole(user?.platform_role, activeMembership?.role_code),
    [user, activeMembership]
  );

  const hasPermission = useCallback(
    (code: string) => {
      if (!user) return false;
      if (user.platform_role === "SUPER_ADMIN") return true;
      return user.effective_permissions?.includes(code) ?? false;
    },
    [user]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      activeAgencyId,
      effectiveRole,
      calendarMode,
      currencyMode,
      isLoading,
      setActiveAgencyId,
      setCalendarMode,
      setCurrencyMode,
      login,
      logout,
      refreshUser,
      hasPermission,
    }),
    [
      user,
      accessToken,
      activeAgencyId,
      effectiveRole,
      calendarMode,
      currencyMode,
      isLoading,
      setActiveAgencyId,
      login,
      logout,
      refreshUser,
      hasPermission,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
