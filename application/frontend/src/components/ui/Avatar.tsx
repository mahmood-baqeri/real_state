import React from "react";
import { cn } from "@/lib/utils";

const sizes = {
     xs: "h-6 w-6 text-[10px]",
     sm: "h-8 w-8 text-xs",
     md: "h-10 w-10 text-sm",
     lg: "h-12 w-12 text-base",
     xl: "h-16 w-16 text-lg",
};

export function Avatar({
     name,
     src,
     size = "md",
     className,
}: {
     name: string;
     src?: string | null;
     size?: keyof typeof sizes;
     className?: string;
}) {
     const initials = name
          .split(" ")
          .map((n) => n[0])
          .filter(Boolean)
          .slice(0, 2)
          .join("")
          .toUpperCase();

     return (
          <span
               className={cn(
                    "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-brand-600 font-bold text-white",
                    sizes[size],
                    className
               )}
               aria-label={name}
          >
               {src ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={src} alt={name} className="h-full w-full object-cover" />
               ) : (
                    <span>{initials || "؟"}</span>
               )}
          </span>
     );
}