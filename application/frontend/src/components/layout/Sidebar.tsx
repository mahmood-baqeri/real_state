"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
     Activity, Award, Bell, Briefcase, Building, Building2, Calendar,
     ChevronLeft, ChevronRight, CreditCard, FileCheck2, FileText,
     FolderOpen, GitBranch, Handshake, Home, Landmark, LayoutDashboard,
     MessageSquare, Newspaper, Percent, PieChart, Settings, ShieldCheck,
     Sparkles, UserCheck, UserCog, UserPlus, Users, Wallet, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import {
     getNavigationForUser,
     NAV_GROUP_LABELS,
     type NavItemConfig,
} from "@/lib/role-navigation";
import { Tooltip } from "@/components/ui/Tooltip";

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
     settings: <Settings className="h-4 w-4" />,
     audit: <Activity className="h-4 w-4" />,
     profile: <UserCog className="h-4 w-4" />,
     content: <Newspaper className="h-4 w-4" />,
     surveys: <Sparkles className="h-4 w-4" />,
     tickets: <MessageSquare className="h-4 w-4" />,
};

interface SidebarProps {
     mobileOpen: boolean;
     onClose: () => void;
     collapsed: boolean;
     onToggleCollapse: () => void;
}

export function Sidebar({
     mobileOpen,
     onClose,
     collapsed,
     onToggleCollapse,
}: SidebarProps) {
     const pathname = usePathname();
     const { user, activeAgencyId } = useAuth();

     const items = useMemo(() => {
          const agencyRole = user?.memberships?.find(
               (m) => m.agency_id === activeAgencyId
          )?.role_code;
          return getNavigationForUser(
               user?.platform_role,
               agencyRole,
               user?.effective_permissions ?? []
          );
     }, [user, activeAgencyId]);

     const grouped = useMemo(() => {
          const map = new Map<NavItemConfig["group"], NavItemConfig[]>();
          for (const item of items) {
               if (!map.has(item.group)) map.set(item.group, []);
               map.get(item.group)!.push(item);
          }
          return Array.from(map.entries());
     }, [items]);

     const isActive = (href: string) => {
          if (href === "/dashboard") return pathname === "/dashboard";
          return pathname === href || pathname.startsWith(href + "/");
     };

     return (
          <>
               {mobileOpen && (
                    <div
                         className="fixed inset-0 z-30 bg-slate-900/50 backdrop-blur-sm lg:hidden"
                         onClick={onClose}
                         aria-hidden
                    />
               )}

               <aside
                    className={cn(
                         "fixed inset-y-0 right-0 z-40 flex flex-col border-l border-border bg-surface transition-all duration-200",
                         "lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
                         mobileOpen ? "translate-x-0" : "translate-x-full lg:translate-x-0",
                         collapsed ? "w-16" : "w-64"
                    )}
               >
                    <div className="flex h-16 items-center justify-between border-b border-divider px-4">
                         {!collapsed ? (
                              <Link href="/dashboard" className="flex items-center gap-2.5">
                                   <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm">
                                        <Building2 className="h-5 w-5" />
                                   </span>
                                   <div className="min-w-0">
                                        <div className="text-sm font-bold text-fg">بنیان ملک</div>
                                        <div className="text-[10px] text-fg-muted">Enterprise Platform</div>
                                   </div>
                              </Link>
                         ) : (
                              <Link
                                   href="/dashboard"
                                   className="mx-auto flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm"
                              >
                                   <Building2 className="h-5 w-5" />
                              </Link>
                         )}
                         <button
                              type="button"
                              onClick={onClose}
                              className="rounded-md p-1.5 text-fg-muted hover:bg-subtle lg:hidden"
                              aria-label="بستن منو"
                         >
                              <X className="h-5 w-5" />
                         </button>
                    </div>

                    <nav className="flex-1 space-y-4 overflow-y-auto px-2 py-4">
                         {grouped.map(([group, groupItems]) => (
                              <div key={group}>
                                   {!collapsed && (
                                        <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-fg-muted">
                                             {NAV_GROUP_LABELS[group]}
                                        </div>
                                   )}
                                   <ul className="space-y-0.5">
                                        {groupItems.map((item) => {
                                             const active = isActive(item.href);
                                             const link = (
                                                  <Link
                                                       href={item.href}
                                                       onClick={() => mobileOpen && onClose()}
                                                       className={cn(
                                                            "group flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
                                                            active
                                                                 ? "bg-brand-50 text-brand-800 dark:bg-brand-900/40 dark:text-brand-100"
                                                                 : "text-fg-secondary hover:bg-subtle hover:text-fg",
                                                            collapsed && "justify-center"
                                                       )}
                                                  >
                                                       <span
                                                            className={cn(
                                                                 "shrink-0",
                                                                 active ? "text-brand-600 dark:text-brand-300" : "text-fg-muted group-hover:text-fg-secondary"
                                                            )}
                                                       >
                                                            {ICON_MAP[item.key] ?? <LayoutDashboard className="h-4 w-4" />}
                                                       </span>
                                                       {!collapsed && <span className="truncate">{item.label}</span>}
                                                       {active && !collapsed && (
                                                            <ChevronLeft className="mr-auto h-3.5 w-3.5 text-brand-600 dark:text-brand-300" />
                                                       )}
                                                  </Link>
                                             );
                                             return (
                                                  <li key={item.key}>
                                                       {collapsed ? (
                                                            <Tooltip content={item.label} side="left">
                                                                 {link}
                                                            </Tooltip>
                                                       ) : (
                                                            link
                                                       )}
                                                  </li>
                                             );
                                        })}
                                   </ul>
                              </div>
                         ))}
                    </nav>

                    <div className="border-t border-divider p-2">
                         <button
                              type="button"
                              onClick={onToggleCollapse}
                              className={cn(
                                   "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-fg-secondary transition-colors hover:bg-subtle hover:text-fg",
                                   collapsed && "justify-center"
                              )}
                              aria-label={collapsed ? "باز کردن منو" : "جمع کردن منو"}
                         >
                              {collapsed ? (
                                   <ChevronLeft className="h-4 w-4" />
                              ) : (
                                   <>
                                        <ChevronRight className="h-4 w-4" />
                                        <span>جمع کردن منو</span>
                                   </>
                              )}
                         </button>
                    </div>
               </aside>
          </>
     );
}