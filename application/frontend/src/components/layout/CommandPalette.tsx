"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { getNavigationForUser } from "@/lib/role-navigation";
import { cn } from "@/lib/utils";
import { Kbd } from "@/components/ui/Kbd";

export function CommandPalette() {
     const router = useRouter();
     const { user, activeAgencyId } = useAuth();
     const [open, setOpen] = useState(false);
     const [query, setQuery] = useState("");
     const [selected, setSelected] = useState(0);
     const inputRef = useRef<HTMLInputElement>(null);

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

     const filtered = useMemo(() => {
          const q = query.trim().toLowerCase();
          if (!q) return items;
          return items.filter((i) => i.label.toLowerCase().includes(q));
     }, [items, query]);

     useEffect(() => {
          const openHandler = () => setOpen(true);
          window.addEventListener("bonyan:open-command-palette", openHandler);
          return () => window.removeEventListener("bonyan:open-command-palette", openHandler);
     }, []);

     useEffect(() => {
          const keyHandler = (e: KeyboardEvent) => {
               if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
                    e.preventDefault();
                    setOpen((v) => !v);
               }
               if (!open) return;
               if (e.key === "Escape") setOpen(false);
               else if (e.key === "ArrowDown") {
                    e.preventDefault();
                    setSelected((s) => Math.min(s + 1, filtered.length - 1));
               } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    setSelected((s) => Math.max(s - 1, 0));
               } else if (e.key === "Enter") {
                    e.preventDefault();
                    const target = filtered[selected];
                    if (target) {
                         setOpen(false);
                         router.push(target.href);
                    }
               }
          };
          window.addEventListener("keydown", keyHandler);
          return () => window.removeEventListener("keydown", keyHandler);
     }, [open, filtered, selected, router]);

     useEffect(() => {
          if (open) {
               setQuery("");
               setSelected(0);
               setTimeout(() => inputRef.current?.focus(), 30);
          }
     }, [open]);

     if (!open) return null;

     return (
          <div
               className="fixed inset-0 z-[90] flex items-start justify-center bg-slate-900/60 px-4 pt-[12vh] backdrop-blur-sm animate-fade-in"
               onClick={() => setOpen(false)}
          >
               <div
                    className="w-full max-w-xl overflow-hidden rounded-xl border border-border bg-surface shadow-xl animate-scale-in"
                    onClick={(e) => e.stopPropagation()}
                    role="dialog"
                    aria-label="جستجوی سراسری"
               >
                    <div className="flex items-center gap-2 border-b border-divider px-4 py-3">
                         <Search className="h-4 w-4 text-fg-muted" />
                         <input
                              ref={inputRef}
                              value={query}
                              onChange={(e) => {
                                   setQuery(e.target.value);
                                   setSelected(0);
                              }}
                              placeholder="جستجو در منوها..."
                              className="flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-fg-muted"
                         />
                         <Kbd>ESC</Kbd>
                    </div>
                    <div className="max-h-[50vh] overflow-y-auto py-2">
                         {filtered.length === 0 ? (
                              <div className="px-4 py-8 text-center text-xs text-fg-muted">
                                   نتیجه‌ای یافت نشد
                              </div>
                         ) : (
                              <ul>
                                   {filtered.map((item, idx) => (
                                        <li key={item.key}>
                                             <button
                                                  type="button"
                                                  onMouseEnter={() => setSelected(idx)}
                                                  onClick={() => {
                                                       setOpen(false);
                                                       router.push(item.href);
                                                  }}
                                                  className={cn(
                                                       "flex w-full items-center gap-3 px-4 py-2 text-right text-sm transition-colors",
                                                       idx === selected
                                                            ? "bg-brand-50 text-brand-800 dark:bg-brand-900/40 dark:text-brand-100"
                                                            : "text-fg-secondary hover:bg-subtle"
                                                  )}
                                             >
                                                  <span className="text-xs">{item.label}</span>
                                                  <span className="mr-auto font-mono text-[10px] text-fg-muted">
                                                       {item.href}
                                                  </span>
                                             </button>
                                        </li>
                                   ))}
                              </ul>
                         )}
                    </div>
               </div>
          </div>
     );
}