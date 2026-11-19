// Path: frontend/src/lib/formatters.ts

import type { AreaUnit, CalendarMode, CurrencyCode } from "./types";

export function formatNumberFa(value: number | string): string {
  const num = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(num)) return String(value);
  return new Intl.NumberFormat("fa-IR").format(num);
}

/**
 * Explicit conversion between IRT (Toman) and IRR (Rial): 1 IRT = 10 IRR.
 */
export function convertTomanRial(
  amount: number | string,
  fromCurrency: CurrencyCode,
  toCurrency: CurrencyCode
): number {
  const numeric = typeof amount === "string" ? Number(amount) : amount;
  if (!Number.isFinite(numeric)) return 0;
  if (fromCurrency === toCurrency) return numeric;
  if (fromCurrency === "IRT" && toCurrency === "IRR") return numeric * 10;
  if (fromCurrency === "IRR" && toCurrency === "IRT") return Math.round(numeric / 10);
  return numeric;
}

export function formatMoney(
  amount: number | string,
  sourceCurrency: CurrencyCode = "IRT",
  displayCurrency: CurrencyCode = "IRT"
): string {
  const converted = convertTomanRial(amount, sourceCurrency, displayCurrency);
  const label =
    displayCurrency === "IRT"
      ? "تومان"
      : displayCurrency === "IRR"
      ? "ریال"
      : displayCurrency === "USD"
      ? "دلار"
      : displayCurrency === "EUR"
      ? "یورو"
      : displayCurrency === "AED"
      ? "درهم"
      : displayCurrency;
  return `${formatNumberFa(converted)} ${label}`;
}

export function formatArea(sqm: number | string, unit: AreaUnit = "SQM"): string {
  const numeric = typeof sqm === "string" ? Number(sqm) : sqm;
  if (!Number.isFinite(numeric)) return "—";
  if (unit === "SQFT") {
    return `${formatNumberFa(Math.round(numeric * 10.7639))} فوت مربع`;
  }
  return `${formatNumberFa(Math.round(numeric))} مترمربع`;
}

export function formatLocalizedDate(
  isoUtc: string | null | undefined,
  calendar: CalendarMode = "jalali"
): string {
  if (!isoUtc) return "—";
  const date = new Date(isoUtc);
  if (Number.isNaN(date.getTime())) return isoUtc;
  if (calendar === "jalali") {
    return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date);
  }
  return new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

export function formatLocalizedDateTime(
  isoUtc: string | null | undefined,
  calendar: CalendarMode = "jalali"
): string {
  if (!isoUtc) return "—";
  const date = new Date(isoUtc);
  if (Number.isNaN(date.getTime())) return isoUtc;
  if (calendar === "jalali") {
    return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export const STATUS_LABELS_FA: Record<string, string> = {
  ACTIVE: "فعال",
  PENDING_REVIEW: "در انتظار بررسی",
  SUSPENDED: "معلق",
  DRAFT: "پیش‌نویس",
  PENDING_APPROVAL: "در انتظار تأیید",
  PUBLISHED: "منتشرشده",
  RESERVED: "رزروشده",
  SOLD: "فروخته‌شده",
  RENTED: "اجاره‌داده‌شده",
  ARCHIVED: "بایگانی",
  REQUESTED: "درخواست‌شده",
  CONFIRMED: "تأییدشده",
  COMPLETED: "انجام‌شده",
  CANCELLED: "لغوشده",
  NO_SHOW: "عدم حضور",
  NEW: "جدید",
  CONTACTED: "تماس گرفته‌شده",
  QUALIFIED: "واجد شرایط",
  CONVERTED: "تبدیل به مشتری",
  DISQUALIFIED: "ردشده",
  OPEN: "باز",
  COUNTER_OFFERED: "پیشنهاد متقابل",
  ACCEPTED: "پذیرفته‌شده",
  REJECTED: "ردشده",
  APPROVED: "تأییدشده",
  SIGNED: "امضاشده",
  EXECUTED: "اجراشده",
  TERMINATED: "فسخ‌شده",
  CONTRACT_ACTIVE: "قرارداد فعال",
  CLOSED_WON: "موفق / مختومه",
  VOIDED: "ابطال‌شده",
  CALCULATED: "محاسبه‌شده",
  SETTLED: "تسویه‌شده",
  POSTED: "قطعی‌شده",
  REVERSED: "برگشت‌خورده",
  PAID: "پرداخت‌شده",
  PENDING: "در انتظار",
  PASSED: "پاس‌شده",
  BOUNCED: "برگشتی",
  INITIATED: "در جریان",
  FAILED: "ناموفق",
  TRIAL: "آزمایشی",
  EXPIRED: "منقضی",
  DONE: "انجام‌شده",
  HELD: "نزد صندوق",
  CLEARED: "وصول‌شده",
  IN_PROGRESS: "در حال بررسی",
  WAITING_USER: "در انتظار پاسخ کاربر",
  RESOLVED: "حل‌شده",
  CLOSED: "بسته‌شده",
  ESCALATED: "ارجاع به سطح بالاتر",
  REVIEW: "در صف بازبینی",
  SCHEDULED: "زمان‌بندی‌شده",
};

export function translateStatus(status: string): string {
  return STATUS_LABELS_FA[status] || status;
}

export const ROLE_LABELS_FA: Record<string, string> = {
  SUPER_ADMIN: "مدیر کل سامانه",
  AGENCY_MANAGER: "مدیر آژانس",
  AGENCY_ACCOUNTANT: "حسابدار آژانس",
  REAL_ESTATE_AGENT: "مشاور املاک",
  AGENT: "مشاور املاک",
  CUSTOMER: "مشتری / متقاضی",
};
