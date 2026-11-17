"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
     extends React.InputHTMLAttributes<HTMLInputElement> {
     invalid?: boolean;
     leftIcon?: React.ReactNode;
     rightIcon?: React.ReactNode;
}

const inputBase =
     "h-10 w-full rounded-lg border bg-surface px-3 text-sm text-fg placeholder:text-fg-muted transition-colors focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:bg-subtle disabled:text-fg-muted";

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
     ({ className, invalid, leftIcon, rightIcon, ...rest }, ref) => {
          const invalidCls = invalid
               ? "border-danger-500 focus:border-danger-600 focus:ring-danger-500/20"
               : "border-border";

          if (leftIcon || rightIcon) {
               return (
                    <div className="relative">
                         {rightIcon && (
                              <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-fg-muted">
                                   {rightIcon}
                              </span>
                         )}
                         <input
                              ref={ref}
                              aria-invalid={invalid}
                              className={cn(
                                   inputBase,
                                   invalidCls,
                                   // rightIcon && "pr-9",
                                   // leftIcon && "pl-9",
                                   className
                              )}
                              {...rest}
                         />
                         {leftIcon && (
                              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-fg-muted">
                                   {leftIcon}
                              </span>
                         )}
                    </div>
               );
          }
          return (
               <input
                    ref={ref}
                    aria-invalid={invalid}
                    className={cn(inputBase, invalidCls, className)}
                    {...rest}
               />
          );
     }
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<
     HTMLTextAreaElement,
     React.TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }
>(({ className, invalid, ...rest }, ref) => (
     <textarea
          ref={ref}
          aria-invalid={invalid}
          className={cn(
               "w-full rounded-lg border bg-surface p-3 text-sm text-fg placeholder:text-fg-muted transition-colors focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:bg-subtle disabled:text-fg-muted",
               invalid ? "border-danger-500" : "border-border",
               className
          )}
          {...rest}
     />
));
Textarea.displayName = "Textarea";

export function Label({
     className,
     children,
     required,
     ...rest
}: React.LabelHTMLAttributes<HTMLLabelElement> & { required?: boolean }) {
     return (
          <label
               className={cn("mb-1.5 block text-xs font-semibold text-fg", className)}
               {...rest}
          >
               {children}
               {required && <span className="mr-0.5 text-danger-600">*</span>}
          </label>
     );
}

export function FieldError({ children }: { children?: React.ReactNode }) {
     if (!children) return null;
     return <p className="mt-1 text-xs text-danger-600">{children}</p>;
}