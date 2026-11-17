"use client";

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DrawerProps {
     open: boolean;
     onClose: () => void;
     title?: string;
     description?: string;
     children: React.ReactNode;
     footer?: React.ReactNode;
     side?: "left" | "right";
     width?: "sm" | "md" | "lg" | "xl";
}

const widthMap = { sm: "max-w-sm", md: "max-w-md", lg: "max-w-xl", xl: "max-w-2xl" };

export function Drawer({
     open,
     onClose,
     title,
     description,
     children,
     footer,
     side = "left",
     width = "md",
}: DrawerProps) {
     const ref = useRef<HTMLDialogElement>(null);

     useEffect(() => {
          const el = ref.current;
          if (!el) return;
          if (open && !el.open) el.showModal();
          if (!open && el.open) el.close();
     }, [open]);

     useEffect(() => {
          const el = ref.current;
          if (!el) return;
          const cancel = (e: Event) => {
               e.preventDefault();
               onClose();
          };
          el.addEventListener("cancel", cancel);
          return () => el.removeEventListener("cancel", cancel);
     }, [onClose]);

     return (
          <dialog
               ref={ref}
               className={cn(
                    "fixed inset-0 z-50 m-0 hidden h-full w-full max-h-none max-w-none bg-transparent p-0 backdrop:bg-slate-900/50 backdrop:backdrop-blur-sm open:flex",
                    side === "left" ? "open:justify-end" : "open:justify-start"
               )}
               onClick={(e) => {
                    if (e.target === e.currentTarget) onClose();
               }}
          >
               <div
                    className={cn(
                         "flex h-full w-full flex-col overflow-hidden border-border bg-surface shadow-xl animate-slide-in-right",
                         side === "left" ? "border-l" : "border-r",
                         widthMap[width]
                    )}
                    onClick={(e) => e.stopPropagation()}
               >
                    <div className="flex items-start justify-between gap-4 border-b border-divider px-6 py-4">
                         <div className="min-w-0">
                              {title && <h2 className="truncate text-base font-bold text-fg">{title}</h2>}
                              {description && (
                                   <p className="mt-0.5 text-xs text-fg-secondary">{description}</p>
                              )}
                         </div>
                         <button
                              type="button"
                              onClick={onClose}
                              aria-label="بستن"
                              className="-m-1.5 rounded-md p-1.5 text-fg-muted hover:bg-subtle hover:text-fg"
                         >
                              <X className="h-5 w-5" />
                         </button>
                    </div>
                    <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
                    {footer && (
                         <div className="border-t border-divider bg-subtle/50 px-6 py-3">
                              {footer}
                         </div>
                    )}
               </div>
          </dialog>
     );
}