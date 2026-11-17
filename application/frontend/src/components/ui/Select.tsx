"use client";

import React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectProps
     extends React.SelectHTMLAttributes<HTMLSelectElement> {
     invalid?: boolean;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
     ({ className, invalid, children, ...rest }, ref) => (
          <div className="relative">
               <select
                    ref={ref}
                    aria-invalid={invalid}
                    className={cn(
                         "h-10 w-full appearance-none rounded-lg border bg-surface pl-9 pr-3 text-sm text-fg transition-colors focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:bg-subtle disabled:text-fg-muted",
                         invalid ? "border-danger-500" : "border-border",
                         className
                    )}
                    {...rest}
               >
                    {children}
               </select>
               <ChevronDown className="pointer-events-none absolute inset-y-0 left-3 my-auto h-4 w-4 text-fg-muted" />
          </div>
     )
);
Select.displayName = "Select";