import React from "react";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger" | "info" | "accent";

const tones: Record<Tone, string> = {
     neutral: "border-border bg-subtle text-fg-secondary",
     brand: "border-brand-200 bg-brand-50 text-brand-800",
     success: "border-success-500/30 bg-success-50 text-success-700",
     warning: "border-warning-500/30 bg-warning-50 text-warning-700",
     danger: "border-danger-500/30 bg-danger-50 text-danger-700",
     info: "border-info-500/30 bg-info-50 text-info-700",
     accent: "border-accent-300 bg-accent-50 text-accent-700",
};

const dotColor: Record<Tone, string> = {
     neutral: "bg-fg-muted",
     brand: "bg-brand-500",
     success: "bg-success-500",
     warning: "bg-warning-500",
     danger: "bg-danger-500",
     info: "bg-info-500",
     accent: "bg-accent-500",
};

export function Badge({
     tone = "neutral",
     className,
     children,
     dot = false,
}: {
     tone?: Tone;
     className?: string;
     children: React.ReactNode;
     dot?: boolean;
}) {
     return (
          <span
               className={cn(
                    "inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-[11px] font-medium",
                    tones[tone],
                    className
               )}
          >
               {dot && <span className={cn("h-1.5 w-1.5 rounded-full", dotColor[tone])} />}
               {children}
          </span>
     );
}