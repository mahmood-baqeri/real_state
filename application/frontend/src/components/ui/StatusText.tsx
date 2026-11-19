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
  "PRE_AGREEMENT",
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
  "RESOLVED",
  "CLOSED",
]);

const WARNING = new Set([
  "PENDING_REVIEW",
  "PENDING_APPROVAL",
  "REQUESTED",
  "COUNTER_OFFERED",
  "OWNER_COUNTERED",
  "BUYER_OFFERED",
  "BARGAINING",
  "AWAITING_BUYER_OFFER",
  "AWAITING_OWNER_RESPONSE",
  "AWAITING_FINAL_APPROVAL",
  "CREATED",
  "PAUSED",
  "CONTRACT_ACTIVE",
  "CALCULATED",
  "PENDING",
  "HELD",
  "INITIATED",
  "TRIAL",
  "RESERVED",
  "QUALIFIED",
  "CONTACTED",
  "OPEN",
  "IN_PROGRESS",
  "WAITING_USER",
  "SCHEDULED",
  "REVIEW",
]);

const DANGER = new Set([
  "SUSPENDED",
  "CANCELLED",
  "NO_SHOW",
  "DISQUALIFIED",
  "REJECTED",
  "WITHDRAWN",
  "TERMINATED",
  "VOIDED",
  "REVERSED",
  "BOUNCED",
  "FAILED",
  "EXPIRED",
  "ESCALATED",
]);

export function StatusText({ status, label }: StatusTextProps) {
  let cls =
    "border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300";
  if (POSITIVE.has(status)) {
    cls =
      "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800/70 dark:bg-emerald-950/50 dark:text-emerald-300";
  } else if (WARNING.has(status)) {
    cls =
      "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800/70 dark:bg-amber-950/50 dark:text-amber-300";
  } else if (DANGER.has(status)) {
    cls =
      "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-800/70 dark:bg-rose-950/50 dark:text-rose-300";
  }

  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {label || translateStatus(status)}
    </span>
  );
}
