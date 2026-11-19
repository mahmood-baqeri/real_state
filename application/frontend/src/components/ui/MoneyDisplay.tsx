"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { formatMoney } from "@/lib/formatters";
import type { CurrencyCode } from "@/lib/types";

interface MoneyDisplayProps {
  amount: string | number;
  sourceCurrency?: CurrencyCode;
  className?: string;
}

export function MoneyDisplay({
  amount,
  sourceCurrency = "IRT",
  className = "",
}: MoneyDisplayProps) {
  const { currencyMode } = useAuth();
  const display =
    sourceCurrency === "IRT" || sourceCurrency === "IRR"
      ? currencyMode === "IRR" || currencyMode === "IRT"
        ? currencyMode
        : sourceCurrency
      : sourceCurrency;

  return (
    <span className={`tabular-nums whitespace-nowrap ${className}`}>
      {formatMoney(amount, sourceCurrency, display)}
    </span>
  );
}
