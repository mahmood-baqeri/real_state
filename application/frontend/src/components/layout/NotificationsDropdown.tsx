"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Check } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { NotificationItem } from "@/lib/types";
import { cn } from "@/lib/utils";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Tooltip } from "@/components/ui/Tooltip";

export function NotificationsDropdown() {
     const { accessToken, activeAgencyId } = useAuth();
     const qc = useQueryClient();
     const [open, setOpen] = useState(false);

     const listQ = useQuery({
          queryKey: ["notifications", activeAgencyId, "dropdown"],
          enabled: !!accessToken && open,
          queryFn: async () =>
               (
                    await apiFetch<NotificationItem[]>("/api/v1/notifications?page_size=8", {
                         token: accessToken,
                         agencyId: activeAgencyId,
                    })
               ).data,
     });

     const readOneMut = useMutation({
          mutationFn: async (id: string) =>
               apiFetch(`/api/v1/notifications/${id}/read`, {
                    method: "POST",
                    token: accessToken,
                    agencyId: activeAgencyId,
               }),
          onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
     });

     const readAllMut = useMutation({
          mutationFn: async () =>
               apiFetch("/api/v1/notifications/read-all", {
                    method: "POST",
                    token: accessToken,
                    agencyId: activeAgencyId,
               }),
          onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
     });

     const unreadCount = (listQ.data || []).filter((n) => !n.is_read).length;

     return (
          <div className="relative">
               <Tooltip content="اعلان‌ها">
                    <button
                         type="button"
                         onClick={() => setOpen((v) => !v)}
                         className="relative rounded-lg p-2 text-fg-secondary transition-colors hover:bg-subtle hover:text-fg"
                         aria-label="اعلان‌ها"
                    >
                         <Bell className="h-4 w-4" />
                         {unreadCount > 0 && (
                              <span className="absolute right-1.5 top-1.5 flex h-2 w-2 rounded-full bg-danger-500 ring-2 ring-surface" />
                         )}
                    </button>
               </Tooltip>

               {open && (
                    <>
                         <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden />
                         <div className="absolute left-0 top-full z-40 mt-2 w-80 overflow-hidden rounded-xl border border-border bg-surface shadow-lg animate-scale-in">
                              <div className="flex items-center justify-between border-b border-divider px-4 py-3">
                                   <span className="text-sm font-bold text-fg">اعلان‌ها</span>
                                   {unreadCount > 0 && (
                                        <button
                                             type="button"
                                             onClick={() => readAllMut.mutate()}
                                             className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:underline dark:text-brand-300"
                                        >
                                             <Check className="h-3 w-3" />
                                             خواندن همه
                                        </button>
                                   )}
                              </div>

                              <div className="max-h-96 overflow-y-auto">
                                   {listQ.isLoading ? (
                                        <div className="space-y-2 p-3">
                                             {[1, 2, 3].map((i) => (
                                                  <div key={i} className="h-14 animate-pulse rounded-md bg-subtle" />
                                             ))}
                                        </div>
                                   ) : (listQ.data || []).length === 0 ? (
                                        <div className="p-8 text-center text-xs text-fg-muted">
                                             اعلانی برای نمایش وجود ندارد
                                        </div>
                                   ) : (
                                        <ul className="divide-y divide-divider">
                                             {listQ.data?.map((n) => (
                                                  <li key={n.id}>
                                                       <button
                                                            type="button"
                                                            onClick={() => {
                                                                 if (!n.is_read) readOneMut.mutate(n.id);
                                                            }}
                                                            className={cn(
                                                                 "flex w-full flex-col gap-1 px-4 py-3 text-right transition-colors hover:bg-subtle",
                                                                 !n.is_read && "bg-brand-50/50 dark:bg-brand-900/20"
                                                            )}
                                                       >
                                                            <div className="flex items-start justify-between gap-2">
                                                                 <span className="line-clamp-1 text-xs font-semibold text-fg">
                                                                      {n.title}
                                                                 </span>
                                                                 {!n.is_read && (
                                                                      <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />
                                                                 )}
                                                            </div>
                                                            <span className="line-clamp-2 text-[11px] text-fg-secondary">
                                                                 {n.body}
                                                            </span>
                                                            <span className="text-[10px] text-fg-muted">
                                                                 <DateDisplay value={n.created_at} withTime />
                                                            </span>
                                                       </button>
                                                  </li>
                                             ))}
                                        </ul>
                                   )}
                              </div>

                              <Link
                                   href="/dashboard/notifications"
                                   onClick={() => setOpen(false)}
                                   className="block border-t border-divider bg-subtle/50 px-4 py-2.5 text-center text-xs font-semibold text-brand-700 hover:bg-subtle dark:text-brand-300"
                              >
                                   مشاهده همه اعلان‌ها
                              </Link>
                         </div>
                    </>
               )}
          </div>
     );
}