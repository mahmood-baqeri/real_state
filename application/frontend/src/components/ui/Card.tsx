import React from "react";
import { cn } from "@/lib/utils";

export const Card = React.forwardRef<
     HTMLDivElement,
     React.HTMLAttributes<HTMLDivElement> & { interactive?: boolean }
>(({ className, interactive, ...rest }, ref) => (
     <div
          ref={ref}
          className={cn(
               "rounded-xl border border-border bg-surface shadow-sm",
               interactive &&
               "cursor-pointer transition-all duration-150 hover:border-border-strong hover:shadow-md",
               className
          )}
          {...rest}
     />
));
Card.displayName = "Card";

export const CardHeader = React.forwardRef<
     HTMLDivElement,
     React.HTMLAttributes<HTMLDivElement>
>(({ className, ...rest }, ref) => (
     <div
          ref={ref}
          className={cn(
               "flex items-start justify-between gap-3 border-b border-divider px-5 py-4",
               className
          )}
          {...rest}
     />
));
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<
     HTMLHeadingElement,
     React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...rest }, ref) => (
     <h3
          ref={ref}
          className={cn("text-sm font-bold text-fg", className)}
          {...rest}
     />
));
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<
     HTMLParagraphElement,
     React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...rest }, ref) => (
     <p
          ref={ref}
          className={cn("mt-0.5 text-xs text-fg-secondary", className)}
          {...rest}
     />
));
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<
     HTMLDivElement,
     React.HTMLAttributes<HTMLDivElement>
>(({ className, ...rest }, ref) => (
     <div ref={ref} className={cn("px-5 py-4", className)} {...rest} />
));
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<
     HTMLDivElement,
     React.HTMLAttributes<HTMLDivElement>
>(({ className, ...rest }, ref) => (
     <div
          ref={ref}
          className={cn(
               "flex items-center justify-end gap-2 border-t border-divider px-5 py-3",
               className
          )}
          {...rest}
     />
));
CardFooter.displayName = "CardFooter";