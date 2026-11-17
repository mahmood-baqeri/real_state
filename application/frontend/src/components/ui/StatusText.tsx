import React from "react";
import { translateStatus } from "@/lib/formatters";

interface StatusTextProps {
  status: string;
  label?: string;
}

const POSITIVE = new Set([
  "ACTIVE",
  "PUBLISHED",
  "CONFIRMED",
  "COMPLETED",
  "ACCEPTED",
  "APPROVED",
  "SIGNED",
  "EXECUTED",
  "CLOSED_WON",
  "SETTLED",
  "POSTED",
  "PAID",
  "PASSED",
  "CLEARED",
  "CONVERTED",
  "DONE",
]);

const WARNING = new Set([
  "PENDING_REVIEW",
  "PENDING_APPROVAL",
  "REQUESTED",
  "COUNTER_OFFERED",
  "CONTRACT_ACTIVE",
  "CALCULATED",
  "PENDING",
  "HELD",
  "INITIATED",
  "TRIAL",
  "RESERVED",
  "QUALIFIED",
  "CONTACTED",
]);

const DANGER = new Set([
  "SUSPENDED",
  "CANCELLED",
  "NO_SHOW",
  "DISQUALIFIED",
  "REJECTED",
  "TERMINATED",
  "VOIDED",
  "REVERSED",
  "BOUNCED",
  "FAILED",
  "EXPIRED",
]);

export function StatusText({ status, label }: StatusTextProps) {
  let cls = "border-slate-200 bg-slate-100 text-slate-700";
  if (POSITIVE.has(status)) {
    cls = "border-emerald-200 bg-emerald-50 text-emerald-800";
  } else if (WARNING.has(status)) {
    cls = "border-amber-200 bg-amber-50 text-amber-800";
  } else if (DANGER.has(status)) {
    cls = "border-rose-200 bg-rose-50 text-rose-800";
  }

  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {label || translateStatus(status)}
    </span>
  );
}
