"use client";

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DialogProps {
     open: boolean;
     onClose: () => void;
     title?: string;
     description?: string;
     children: React.ReactNode;
     footer?: React.ReactNode;
     size?: "sm" | "md" | "lg" | "xl" | "full";
     closeOnBackdrop?: boolean;
}

const sizeMap = {
     sm: "max-w-sm",
     md: "max-w-lg",
     lg: "max-w-2xl",
     xl: "max-w-4xl",
     full: "max-w-6xl",
};

export function Dialog({
     open,
     onClose,
     title,
     description,
     children,
     footer,
     size = "md",
     closeOnBackdrop = true,
}: DialogProps) {
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
               className="fixed inset-0 z-50 m-0 hidden h-full w-full max-h-none max-w-none bg-transparent p-4 backdrop:bg-slate-900/50 backdrop:backdrop-blur-sm open:flex open:items-center open:justify-center"
               onClick={(e) => {
                    if (closeOnBackdrop && e.target === e.currentTarget) onClose();
               }}
          >
               <div
                    className={cn(
                         "relative w-full overflow-hidden rounded-xl border border-border bg-surface shadow-xl animate-scale-in",
                         sizeMap[size]
                    )}
                    onClick={(e) => e.stopPropagation()}
               >
                    {(title || description) && (
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
                                   className="-m-1.5 rounded-md p-1.5 text-fg-muted transition-colors hover:bg-subtle hover:text-fg"
                              >
                                   <X className="h-5 w-5" />
                              </button>
                         </div>
                    )}
                    <div className="max-h-[70vh] overflow-y-auto px-6 py-5">{children}</div>
                    {footer && (
                         <div className="flex items-center justify-end gap-2 border-t border-divider bg-subtle/50 px-6 py-3">
                              {footer}
                         </div>
                    )}
               </div>
          </dialog>
     );
}