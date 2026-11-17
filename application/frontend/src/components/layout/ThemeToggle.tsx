"use client";

import React from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme, type ThemeMode } from "@/lib/theme-provider";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/Tooltip";

const options: { mode: ThemeMode; label: string; icon: React.ReactNode }[] = [
     { mode: "light", label: "روشن", icon: <Sun className="h-4 w-4" /> },
     { mode: "dark", label: "تاریک", icon: <Moon className="h-4 w-4" /> },
     { mode: "system", label: "سیستم", icon: <Monitor className="h-4 w-4" /> },
];

export function ThemeToggle() {
     const { mode, setMode } = useTheme();

     return (
          <div
               role="radiogroup"
               aria-label="انتخاب تم"
               className="inline-flex items-center gap-0.5 rounded-lg border border-border bg-subtle p-0.5"
          >
               {options.map((opt) => {
                    const active = mode === opt.mode;
                    return (
                         <Tooltip key={opt.mode} content={opt.label}>
                              <button
                                   type="button"
                                   role="radio"
                                   aria-checked={active}
                                   aria-label={opt.label}
                                   onClick={() => setMode(opt.mode)}
                                   className={cn(
                                        "inline-flex h-8 w-8 items-center justify-center rounded-md transition-all",
                                        active
                                             ? "bg-surface text-brand-700 shadow-sm dark:text-brand-300"
                                             : "text-fg-muted hover:text-fg-secondary"
                                   )}
                              >
                                   {opt.icon}
                              </button>
                         </Tooltip>
                    );
               })}
          </div>
     );
}