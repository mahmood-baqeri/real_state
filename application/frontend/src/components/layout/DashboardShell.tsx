"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Award,
  Bell,
  Briefcase,
  Building,
  Building2,
  Calendar,
  ChevronDown,
  Command,
  CreditCard,
  FileCheck2,
  FileText,
  FolderOpen,
  GitBranch,
  Handshake,
  Home,
  Landmark,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareWarning,
  Percent,
  PieChart,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Ticket,
  UserCheck,
  UserCog,
  UserPlus,
  Users,
  Vote,
  Wallet,
  X,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { ROLE_LABELS_FA } from "@/lib/formatters";
import {
  getNavigationForUser,
  NAV_GROUP_LABELS,
  type NavItemConfig,
} from "@/lib/role-navigation";
import type { GlobalSearchResult, NotificationItem } from "@/lib/types";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

const ICON_MAP: Record<string, React.ReactNode> = {
  overview: <LayoutDashboard className="h-4 w-4" />,
  admin: <ShieldCheck className="h-4 w-4" />,
  agencies: <Building className="h-4 w-4" />,
  properties: <Home className="h-4 w-4" />,
  documents: <FolderOpen className="h-4 w-4" />,
  customers: <Users className="h-4 w-4" />,
  leads: <UserPlus className="h-4 w-4" />,
  crm: <GitBranch className="h-4 w-4" />,
  appointments: <Calendar className="h-4 w-4" />,
  negotiations: <Handshake className="h-4 w-4" />,
  contracts: <FileText className="h-4 w-4" />,
  deals: <FileCheck2 className="h-4 w-4" />,
  commissions: <Percent className="h-4 w-4" />,
  accounting: <Landmark className="h-4 w-4" />,
  payroll: <Wallet className="h-4 w-4" />,
  subscriptions: <CreditCard className="h-4 w-4" />,
  reports: <PieChart className="h-4 w-4" />,
  team: <Users className="h-4 w-4" />,
  employees: <Briefcase className="h-4 w-4" />,
  agents: <Award className="h-4 w-4" />,
  roles: <UserCheck className="h-4 w-4" />,
  notifications: <Bell className="h-4 w-4" />,
  tickets: <Ticket className="h-4 w-4" />,
  complaints: <MessageSquareWarning className="h-4 w-4" />,
  surveys: <Vote className="h-4 w-4" />,
  ai: <Sparkles className="h-4 w-4" />,
  cms: <FileText className="h-4 w-4" />,
  settings: <Settings className="h-4 w-4" />,
  audit: <Activity className="h-4 w-4" />,
  profile: <UserCog className="h-4 w-4" />,
};

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const {
    user,
    accessToken,
    activeAgencyId,
    setActiveAgencyId,
    effectiveRole,
    calendarMode,
    setCalendarMode,
    currencyMode,
    setCurrencyMode,
    isLoading,
    logout,
  } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [wsUnreadCount, setWsUnreadCount] = useState<number | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(commandQuery.trim()), 240);
    return () => clearTimeout(t);
  }, [commandQuery]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    setMobileOpen(false);
    setCommandOpen(false);
  }, [pathname]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((o) => !o);
      } else if (e.key === "Escape") {
        setCommandOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!accessToken || typeof window === "undefined") return;
    if (window.location.protocol !== "http:") return;
    let ws: WebSocket | null = null;
    try {
      const wsUrl = `ws://${window.location.hostname}:8020/api/v1/ws/notifications?token=${encodeURIComponent(accessToken)}`;
      ws = new WebSocket(wsUrl);
      ws.onmessage = (evt) => {
        try {
          const parsed = JSON.parse(evt.data);
          if (parsed?.event === "notification_snapshot" && typeof parsed?.data?.unread_count === "number") {
            setWsUnreadCount(parsed.data.unread_count);
          }
        } catch {
          // ignore malformed event
        }
      };
      ws.onerror = () => {
        ws?.close();
      };
    } catch {
      // ignore if ws blocked
    }
    return () => {
      ws?.close();
    };
  }, [accessToken]);

  const { data: restUnreadCount = 0 } = useQuery({
    queryKey: ["unread-notifications-count", user?.id],
    enabled: !!accessToken,
    queryFn: async () => {
      const env = await apiFetch<NotificationItem[]>(
        "/api/v1/notifications?unread_only=true&page_size=20",
        { token: accessToken }
      );
      return env.meta?.pagination?.total_count ?? env.data.length;
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  const unreadCount = wsUnreadCount ?? restUnreadCount;

  const { data: globalSearchData, isFetching: globalSearchLoading } = useQuery({
    queryKey: ["global-search", debouncedQuery, activeAgencyId],
    enabled: !!accessToken && commandOpen && debouncedQuery.length >= 2,
    queryFn: async () => {
      const env = await apiFetch<GlobalSearchResult>(
        `/api/v1/search/global?q=${encodeURIComponent(debouncedQuery)}&limit=4`,
        { token: accessToken, agencyId: activeAgencyId }
      );
      return env.data;
    },
    staleTime: 10_000,
  });

  const activeMembership = useMemo(
    () => user?.memberships?.find((m) => m.agency_id === activeAgencyId) || user?.memberships?.[0],
    [user, activeAgencyId]
  );

  const navItems = useMemo(
    () =>
      getNavigationForUser(
        user?.platform_role,
        activeMembership?.role_code,
        user?.effective_permissions || []
      ),
    [user, activeMembership]
  );

  const groupedNav = useMemo(() => {
    const groups: { group: NavItemConfig["group"]; label: string; items: NavItemConfig[] }[] = [];
    const order: NavItemConfig["group"][] = ["core", "portfolio", "crm", "deals", "finance", "admin"];
    for (const g of order) {
      const items = navItems.filter((i) => i.group === g);
      if (items.length > 0) {
        groups.push({ group: g, label: NAV_GROUP_LABELS[g], items });
      }
    }
    return groups;
  }, [navItems]);

  const filteredCommands = useMemo(() => {
    const q = commandQuery.trim().toLowerCase();
    if (!q) return navItems;
    return navItems.filter(
      (i) => i.label.toLowerCase().includes(q) || i.href.toLowerCase().includes(q)
    );
  }, [navItems, commandQuery]);

  const globalSections = useMemo(() => {
    if (!globalSearchData) return [];
    const defs: { key: keyof Omit<GlobalSearchResult, "total_hits">; label: string }[] = [
      { key: "properties", label: "املاک" },
      { key: "customers", label: "مشتریان" },
      { key: "owners", label: "مالکان" },
      { key: "agents", label: "مشاوران" },
      { key: "contracts", label: "قراردادها" },
      { key: "tickets", label: "تیکت‌ها" },
      { key: "documents", label: "اسناد" },
      { key: "articles", label: "مقالات" },
    ];
    return defs
      .map((d) => ({ ...d, items: globalSearchData[d.key] || [] }))
      .filter((d) => d.items.length > 0);
  }, [globalSearchData]);

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-4 text-sm font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
          در حال آماده‌سازی میز کار سازمانی...
        </div>
      </div>
    );
  }

  const sidebarContent = (
    <div className="flex h-full flex-col bg-white dark:bg-slate-900">
      <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5 dark:border-slate-800">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-700 text-white dark:bg-teal-600">
            <Building2 className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-900 dark:text-slate-100">بنیان ملک</div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">میز کار یکپارچه</div>
          </div>
        </Link>
        <button
          type="button"
          onClick={() => setMobileOpen(false)}
          className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 lg:hidden"
          aria-label="بستن منو"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {groupedNav.map((grp) => (
          <div key={grp.group}>
            <div className="mb-1.5 px-3 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
              {grp.label}
            </div>
            <div className="space-y-0.5">
              {grp.items.map((item) => {
                const isActive =
                  item.href === "/dashboard"
                    ? pathname === "/dashboard"
                    : pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <Link
                    key={item.key}
                    href={item.href}
                    className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                      isActive
                        ? "border border-teal-200/80 bg-teal-50 font-semibold text-teal-800 dark:border-teal-800/70 dark:bg-teal-950/50 dark:text-teal-300"
                        : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                    }`}
                  >
                    <span className="flex items-center gap-2.5">
                      <span
                        className={
                          isActive
                            ? "text-teal-700 dark:text-teal-400"
                            : "text-slate-400 dark:text-slate-500"
                        }
                      >
                        {ICON_MAP[item.key] || <LayoutDashboard className="h-4 w-4" />}
                      </span>
                      <span className="whitespace-nowrap">{item.label}</span>
                    </span>
                    {item.key === "notifications" && unreadCount > 0 && (
                      <span className="tabular-nums rounded bg-teal-700 px-1.5 py-0.5 text-[10px] font-bold text-white dark:bg-teal-600">
                        {unreadCount}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-3 dark:border-slate-800">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/60">
          <div className="truncate text-xs font-bold text-slate-900 dark:text-slate-100">
            {user.full_name}
          </div>
          <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
            {ROLE_LABELS_FA[effectiveRole] || effectiveRole}
          </div>
          <div className="mt-2.5 flex items-center gap-2">
            <Link
              href="/dashboard/profile"
              className="flex-1 rounded-md border border-slate-300 bg-white py-1.5 text-center text-[11px] font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              پروفایل
            </Link>
            <button
              type="button"
              onClick={async () => {
                await logout();
                router.push("/login");
              }}
              className="inline-flex items-center justify-center gap-1 rounded-md border border-rose-200 bg-white px-2.5 py-1.5 text-[11px] font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-900/60 dark:bg-slate-900 dark:text-rose-400 dark:hover:bg-rose-950/40"
            >
              <LogOut className="h-3.5 w-3.5" />
              خروج
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen overflow-x-hidden bg-slate-50 dark:bg-slate-950">
      {/* Desktop RTL Sidebar */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:right-0 lg:z-30 lg:block lg:w-64 lg:border-l lg:border-slate-200 dark:lg:border-slate-800">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative z-10 w-72 max-w-[85vw] border-l border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900">
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Quick Command Jump & Global Search Modal */}
      {commandOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/60 px-4 pt-20 backdrop-blur-xs"
          onClick={() => setCommandOpen(false)}
        >
          <div
            className="w-full max-w-xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3 dark:border-slate-800">
              <Search className="h-4 w-4 text-slate-400" />
              <input
                autoFocus
                type="text"
                value={commandQuery}
                onChange={(e) => setCommandQuery(e.target.value)}
                placeholder="جستجوی سراسری (ملک، مشتری، قرارداد، تیکت) یا پرش به بخش..."
                className="flex-1 bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none dark:text-slate-100"
              />
              <button
                type="button"
                onClick={() => setCommandOpen(false)}
                className="rounded px-2 py-1 text-[11px] font-mono text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                ESC
              </button>
            </div>
            <div className="max-h-96 space-y-2 overflow-y-auto p-2">
              {debouncedQuery.length >= 2 && (
                <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-2 dark:border-slate-800 dark:bg-slate-800/40">
                  <div className="mb-1.5 flex items-center justify-between px-2 text-[11px] font-bold text-teal-700 dark:text-teal-400">
                    <span>نتایج جستجوی سراسری پایگاه داده</span>
                    {globalSearchLoading ? (
                      <span className="text-slate-400">در حال جستجو...</span>
                    ) : globalSearchData ? (
                      <span className="tabular-nums text-slate-500">
                        {globalSearchData.total_hits} نتیجه
                      </span>
                    ) : null}
                  </div>
                  {!globalSearchLoading && globalSections.length === 0 ? (
                    <div className="px-2 py-2 text-xs text-slate-500 dark:text-slate-400">
                      موردی در ماژول‌های دیتابیس با این عبارت یافت نشد.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {globalSections.map((sec) => (
                        <div key={sec.key}>
                          <div className="px-2 py-0.5 text-[10px] font-semibold text-slate-400 dark:text-slate-500">
                            {sec.label}
                          </div>
                          {sec.items.map((hit) => (
                            <button
                              key={`${sec.key}-${hit.id}`}
                              type="button"
                              onClick={() => {
                                setCommandOpen(false);
                                setCommandQuery("");
                                router.push(hit.href);
                              }}
                              className="flex w-full items-center justify-between rounded-md px-2.5 py-2 text-right text-xs hover:bg-white dark:hover:bg-slate-900"
                            >
                              <span className="font-semibold text-slate-800 dark:text-slate-200">
                                {hit.title}
                              </span>
                              <span className="truncate text-[11px] text-slate-500 dark:text-slate-400">
                                {hit.subtitle}
                              </span>
                            </button>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredCommands.length === 0 ? (
                  <div className="p-4 text-center text-xs text-slate-500 dark:text-slate-400">
                    بخشی با این عبارت یافت نشد.
                  </div>
                ) : (
                  filteredCommands.map((item) => (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => {
                        setCommandOpen(false);
                        setCommandQuery("");
                        router.push(item.href);
                      }}
                      className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-right text-xs font-medium text-slate-800 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                    >
                      <span className="flex items-center gap-2.5">
                        <span className="text-teal-700 dark:text-teal-400">
                          {ICON_MAP[item.key] || <LayoutDashboard className="h-4 w-4" />}
                        </span>
                        <span>{item.label}</span>
                      </span>
                      <span className="font-mono text-[11px] text-slate-400">{item.href}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="min-w-0 lg:pr-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-2 border-b border-slate-200 bg-white/95 px-3 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-900/95 sm:gap-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="باز کردن منوی ناوبری"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>

            {user.memberships && user.memberships.length > 0 ? (
              <div className="relative flex min-w-0 items-center">
                <select
                  aria-label="انتخاب آژانس فعال"
                  value={activeAgencyId || ""}
                  onChange={(e) => setActiveAgencyId(e.target.value || null)}
                  className="h-9 w-full max-w-[180px] truncate appearance-none rounded-lg border border-slate-300 bg-white pr-3 pl-7 text-xs font-semibold text-slate-800 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 sm:max-w-xs"
                >
                  {user.platform_role === "SUPER_ADMIN" && (
                    <option value="">نمای کل پلتفرم (سراسری)</option>
                  )}
                  {user.memberships.map((m) => (
                    <option key={m.agency_id} value={m.agency_id}>
                      {m.agency_name} — {m.role_name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-slate-500" />
              </div>
            ) : (
              <span className="truncate text-xs font-semibold text-slate-700 dark:text-slate-200">
                {user.platform_role === "SUPER_ADMIN"
                  ? "مدیر کل پلتفرم"
                  : "حساب کاربری متقاضی / مشتری"}
              </span>
            )}

            <button
              type="button"
              onClick={() => setCommandOpen(true)}
              className="hidden h-9 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-xs text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-400 dark:hover:bg-slate-800 xl:inline-flex"
            >
              <Command className="h-3.5 w-3.5" />
              <span>پرش سریع...</span>
              <kbd className="rounded border border-slate-300 bg-white px-1.5 py-0.5 font-mono text-[10px] dark:border-slate-600 dark:bg-slate-900">
                Ctrl+K
              </kbd>
            </button>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Theme Switcher */}
            <div className="hidden md:block">
              <ThemeToggle variant="segmented" />
            </div>
            <div className="md:hidden">
              <ThemeToggle variant="compact" />
            </div>

            {/* Currency Mode Toggle */}
            <div className="hidden items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5 dark:border-slate-700 dark:bg-slate-800/80 sm:flex">
              <button
                type="button"
                onClick={() => setCurrencyMode("IRT")}
                className={`h-7 whitespace-nowrap rounded-md px-2 text-[11px] font-semibold transition-colors ${
                  currencyMode === "IRT"
                    ? "bg-white text-teal-800 shadow-xs dark:bg-slate-900 dark:text-teal-300"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                تومان
              </button>
              <button
                type="button"
                onClick={() => setCurrencyMode("IRR")}
                className={`h-7 whitespace-nowrap rounded-md px-2 text-[11px] font-semibold transition-colors ${
                  currencyMode === "IRR"
                    ? "bg-white text-teal-800 shadow-xs dark:bg-slate-900 dark:text-teal-300"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                ریال
              </button>
            </div>

            {/* Calendar Mode Toggle */}
            <div className="hidden items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5 dark:border-slate-700 dark:bg-slate-800/80 sm:flex">
              <button
                type="button"
                onClick={() => setCalendarMode("jalali")}
                className={`h-7 whitespace-nowrap rounded-md px-2 text-[11px] font-semibold transition-colors ${
                  calendarMode === "jalali"
                    ? "bg-white text-teal-800 shadow-xs dark:bg-slate-900 dark:text-teal-300"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                شمسی
              </button>
              <button
                type="button"
                onClick={() => setCalendarMode("gregorian")}
                className={`h-7 whitespace-nowrap rounded-md px-2 text-[11px] font-semibold transition-colors ${
                  calendarMode === "gregorian"
                    ? "bg-white text-teal-800 shadow-xs dark:bg-slate-900 dark:text-teal-300"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                میلادی
              </button>
            </div>

            <Link
              href="/dashboard/notifications"
              className="relative inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
              aria-label="اعلان‌ها"
            >
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -left-1 flex h-4 min-w-4 items-center justify-center rounded bg-teal-700 px-1 text-[10px] font-bold text-white tabular-nums dark:bg-teal-500 dark:text-slate-950">
                  {unreadCount}
                </span>
              )}
            </Link>

            <Link
              href="/"
              className="hidden h-9 items-center whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 sm:inline-flex"
            >
              پورتال عمومی
            </Link>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
