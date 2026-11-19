// Path: frontend/src/components/ui/DateDisplay.tsx

"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { formatLocalizedDate, formatLocalizedDateTime } from "@/lib/formatters";

interface DateDisplayProps {
  value: string | null | undefined;
  withTime?: boolean;
  className?: string;
}

export function DateDisplay({ value, withTime = false, className = "" }: DateDisplayProps) {
  const { calendarMode } = useAuth();
  const formatted = withTime
    ? formatLocalizedDateTime(value, calendarMode)
    : formatLocalizedDate(value, calendarMode);
  return <span className={`tabular-nums whitespace-nowrap ${className}`}>{formatted}</span>;
}
