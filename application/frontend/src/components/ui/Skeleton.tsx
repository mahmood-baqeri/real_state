import React from "react";
import { cn } from "@/lib/utils";

export function Skeleton({
     className,
     ...rest
}: React.HTMLAttributes<HTMLDivElement>) {
     return (
          <div
               className={cn(
                    "relative overflow-hidden rounded-md bg-subtle",
                    "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.6s_infinite] before:bg-gradient-to-r before:from-transparent before:via-black/5 before:to-transparent dark:before:via-white/5",
                    className
               )}
               {...rest}
          />
     );
}