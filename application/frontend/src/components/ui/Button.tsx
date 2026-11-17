"use client";

import React from "react";
import { cn } from "@/lib/utils";

type Variant =
     | "primary"
     | "secondary"
     | "outline"
     | "ghost"
     | "danger"
     | "success"
     | "link";
type Size = "xs" | "sm" | "md" | "lg" | "icon";

export interface ButtonProps
     extends React.ButtonHTMLAttributes<HTMLButtonElement> {
     variant?: Variant;
     size?: Size;
     loading?: boolean;
     leftIcon?: React.ReactNode;
     rightIcon?: React.ReactNode;
}

const base =
     "inline-flex items-center justify-center gap-2 whitespace-nowrap font-semibold transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-canvas";

const variants: Record<Variant, string> = {
     primary:
          "bg-brand-600 text-white shadow-sm hover:bg-brand-700 active:bg-brand-800",
     secondary:
          "bg-subtle text-fg border border-border hover:bg-elevated active:bg-subtle",
     outline:
          "bg-surface text-fg border border-border-strong hover:bg-subtle active:bg-subtle",
     ghost:
          "bg-transparent text-fg-secondary hover:bg-subtle hover:text-fg",
     danger:
          "bg-danger-600 text-white shadow-sm hover:bg-danger-700 active:bg-danger-700/90",
     success:
          "bg-success-600 text-white shadow-sm hover:bg-success-700 active:bg-success-700/90",
     link:
          "bg-transparent text-brand-600 hover:text-brand-700 underline-offset-4 hover:underline px-0",
};

const sizes: Record<Size, string> = {
     xs: "h-7 px-2.5 text-xs rounded-md",
     sm: "h-8 px-3 text-xs rounded-md",
     md: "h-10 px-4 text-sm rounded-lg",
     lg: "h-11 px-5 text-sm rounded-lg",
     icon: "h-9 w-9 rounded-lg",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
     (
          {
               variant = "primary",
               size = "md",
               loading = false,
               leftIcon,
               rightIcon,
               className,
               children,
               disabled,
               ...rest
          },
          ref
     ) => (
          <button
               ref={ref}
               disabled={disabled || loading}
               className={cn(base, variants[variant], sizes[size], className)}
               {...rest}
          >
               {loading ? (
                    <span
                         className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
                         aria-hidden
                    />
               ) : (
                    leftIcon
               )}
               {children}
               {rightIcon}
          </button>
     )
);
Button.displayName = "Button";