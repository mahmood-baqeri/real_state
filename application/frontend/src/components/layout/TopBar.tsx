"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Menu, Search, Settings, User as UserIcon } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Avatar } from "@/components/ui/Avatar";
import { ThemeToggle } from "./ThemeToggle";
import { NotificationsDropdown } from "./NotificationsDropdown";
import { Kbd } from "@/components/ui/Kbd";

export function TopBar({ onOpenSidebar }: { onOpenSidebar: () => void }) {
     const router = useRouter();
     const { user, activeAgencyId, logout } = useAuth();
     const [userMenuOpen, setUserMenuOpen] = useState(false);

     const activeMembership = user?.memberships?.find(
          (m) => m.agency_id === activeAgencyId
     );

     return (
          <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-surface/80 px-4 backdrop-blur-md lg:px-6">
               <button
                    type="button"
                    onClick={onOpenSidebar}
                    className="rounded-lg p-2 text-fg-secondary hover:bg-subtle lg:hidden"
                    aria-label="باز کردن منو"
               >
                    <Menu className="h-5 w-5" />
               </button>

               <button
                    type="button"
                    onClick={() =>
                         window.dispatchEvent(new CustomEvent("bonyan:open-command-palette"))
                    }
                    className="hidden h-9 flex-1 items-center gap-2 rounded-lg border border-border bg-subtle px-3 text-xs text-fg-muted transition-colors hover:border-border-strong sm:flex sm:max-w-md"
                    aria-label="جستجو"
               >
                    <Search className="h-3.5 w-3.5" />
                    <span className="flex-1 text-right">جستجوی سراسری...</span>
                    <span className="hidden items-center gap-0.5 md:flex">
                         <Kbd>⌘</Kbd>
                         <Kbd>K</Kbd>
                    </span>
               </button>

               <div className="flex-1" />

               <div className="flex items-center gap-1">
                    <ThemeToggle />
                    <NotificationsDropdown />

                    <div className="relative">
                         <button
                              type="button"
                              onClick={() => setUserMenuOpen((v) => !v)}
                              className="flex items-center gap-2 rounded-lg p-1 pr-2 transition-colors hover:bg-subtle"
                              aria-haspopup="menu"
                              aria-expanded={userMenuOpen}
                         >
                              <Avatar name={user?.full_name ?? "؟"} size="sm" />
                              <div className="hidden text-right sm:block">
                                   <div className="text-xs font-semibold leading-tight text-fg">
                                        {user?.full_name}
                                   </div>
                                   <div className="text-[10px] leading-tight text-fg-muted">
                                        {activeMembership?.role_name ?? user?.platform_role ?? ""}
                                   </div>
                              </div>
                         </button>

                         {userMenuOpen && (
                              <>
                                   <div
                                        className="fixed inset-0 z-30"
                                        onClick={() => setUserMenuOpen(false)}
                                        aria-hidden
                                   />
                                   <div className="absolute left-0 top-full z-40 mt-2 w-56 overflow-hidden rounded-xl border border-border bg-surface shadow-lg animate-scale-in">
                                        <div className="border-b border-divider px-4 py-3">
                                             <div className="text-sm font-semibold text-fg">{user?.full_name}</div>
                                             <div className="mt-0.5 font-mono text-xs text-fg-muted" dir="ltr">
                                                  {user?.phone_number}
                                             </div>
                                        </div>
                                        <div className="py-1">
                                             <button
                                                  type="button"
                                                  onClick={() => {
                                                       setUserMenuOpen(false);
                                                       router.push("/dashboard/profile");
                                                  }}
                                                  className="flex w-full items-center gap-2 px-4 py-2 text-xs font-medium text-fg-secondary hover:bg-subtle hover:text-fg"
                                             >
                                                  <UserIcon className="h-3.5 w-3.5" />
                                                  پروفایل من
                                             </button>
                                             <button
                                                  type="button"
                                                  onClick={() => {
                                                       setUserMenuOpen(false);
                                                       router.push("/dashboard/settings");
                                                  }}
                                                  className="flex w-full items-center gap-2 px-4 py-2 text-xs font-medium text-fg-secondary hover:bg-subtle hover:text-fg"
                                             >
                                                  <Settings className="h-3.5 w-3.5" />
                                                  تنظیمات
                                             </button>
                                        </div>
                                        <div className="border-t border-divider py-1">
                                             <button
                                                  type="button"
                                                  onClick={async () => {
                                                       setUserMenuOpen(false);
                                                       await logout();
                                                       router.push("/login");
                                                  }}
                                                  className="flex w-full items-center gap-2 px-4 py-2 text-xs font-medium text-danger-600 hover:bg-danger-50"
                                             >
                                                  <LogOut className="h-3.5 w-3.5" />
                                                  خروج از حساب
                                             </button>
                                        </div>
                                   </div>
                              </>
                         )}
                    </div>
               </div>
          </header>
     );
}