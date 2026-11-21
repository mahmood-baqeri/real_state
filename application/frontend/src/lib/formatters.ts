import type {
  AreaUnit,
  CalendarMode,
  CurrencyCode,
  CurrencyConfigItem,
  ExchangeRateItem,
} from "./types";

interface RuntimeLocalizationRegistry {
  currencies: Record<string, CurrencyConfigItem>;
  exchangeRates: Record<string, number>;
}

const DEFAULT_CURRENCY_LABELS: Record<string, string> = {
  IRT: "تومان",
  IRR: "ریال",
  USD: "دلار",
  EUR: "یورو",
  AED: "درهم",
};

const runtimeLocalization: RuntimeLocalizationRegistry = {
  currencies: {},
  exchangeRates: {
    "IRT->IRR": 10,
    "IRR->IRT": 0.1,
  },
};

export function setRuntimeLocalizationRegistry(
  currencies: CurrencyConfigItem[] = [],
  exchangeRates: ExchangeRateItem[] = []
): void {
  const curMap: Record<string, CurrencyConfigItem> = {};
  for (const c of currencies) {
    if (c?.code) curMap[c.code.toUpperCase()] = c;
  }
  const fxMap: Record<string, number> = {
    "IRT->IRR": 10,
    "IRR->IRT": 0.1,
  };
  for (const fx of exchangeRates) {
    const rateNum = Number(fx.rate);
    if (Number.isFinite(rateNum) && rateNum > 0) {
      const pair = `${fx.base_currency_code.toUpperCase()}->${fx.quote_currency_code.toUpperCase()}`;
      fxMap[pair] = rateNum;
      const rev = `${fx.quote_currency_code.toUpperCase()}->${fx.base_currency_code.toUpperCase()}`;
      if (!(rev in fxMap)) {
        fxMap[rev] = 1 / rateNum;
      }
    }
  }
  runtimeLocalization.currencies = curMap;
  runtimeLocalization.exchangeRates = fxMap;
}

export function getCurrencyDisplayLabel(code: string): string {
  const up = (code || "IRT").toUpperCase();
  const reg = runtimeLocalization.currencies[up];
  if (reg?.name_fa) return reg.name_fa;
  return DEFAULT_CURRENCY_LABELS[up] || up;
}

export function formatNumberFa(value: number | string): string {
  const num = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(num)) return String(value);
  return new Intl.NumberFormat("fa-IR").format(num);
}

/**
 * Dynamic DB-backed currency conversion with explicit 1 IRT = 10 IRR invariant fallback.
 */
export function convertTomanRial(
  amount: number | string,
  fromCurrency: CurrencyCode | string,
  toCurrency: CurrencyCode | string
): number {
  const numeric = typeof amount === "string" ? Number(amount) : amount;
  if (!Number.isFinite(numeric)) return 0;
  const from = (fromCurrency || "IRT").toUpperCase();
  const to = (toCurrency || "IRT").toUpperCase();
  if (from === to) return numeric;

  const direct = runtimeLocalization.exchangeRates[`${from}->${to}`];
  if (direct && Number.isFinite(direct)) {
    const decimals = runtimeLocalization.currencies[to]?.decimal_places ?? 0;
    const factor = 10 ** decimals;
    return Math.round(numeric * direct * factor) / factor;
  }
  if (from === "IRT" && to === "IRR") return numeric * 10;
  if (from === "IRR" && to === "IRT") return Math.round(numeric / 10);

  // Pivot via IRT if both pairs exist
  const toIrt = runtimeLocalization.exchangeRates[`${from}->IRT`];
  const fromIrt = runtimeLocalization.exchangeRates[`IRT->${to}`];
  if (toIrt && fromIrt) {
    const decimals = runtimeLocalization.currencies[to]?.decimal_places ?? 0;
    const factor = 10 ** decimals;
    return Math.round(numeric * toIrt * fromIrt * factor) / factor;
  }
  return numeric;
}

export function formatMoney(
  amount: number | string,
  sourceCurrency: CurrencyCode | string = "IRT",
  displayCurrency: CurrencyCode | string = "IRT"
): string {
  const converted = convertTomanRial(amount, sourceCurrency, displayCurrency);
  const label = getCurrencyDisplayLabel(String(displayCurrency || "IRT"));
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
  CREATED: "ثبت اولیه مذاکره",
  AWAITING_BUYER_OFFER: "در انتظار پیشنهاد خریدار",
  BUYER_OFFERED: "پیشنهاد خریدار ثبت شد",
  AWAITING_OWNER_RESPONSE: "در انتظار پاسخ مالک",
  OWNER_COUNTERED: "پیشنهاد متقابل مالک",
  BARGAINING: "در حال چانه‌زنی و تعدیل",
  PRE_AGREEMENT: "توافق اولیه حاصل شد",
  AWAITING_FINAL_APPROVAL: "در انتظار تأیید نهایی",
  PAUSED: "مذاکره متوقف‌شده",
  WITHDRAWN: "انصراف طرفین",
  UNVERIFIED: "احرازنشده",
  VERIFIED: "احرازشده",
  EXCEPTION_APPROVED: "تأیید با استثنای مجاز",
  SENT: "ارسال‌شده",
  BLOCKED_BY_TOGGLE: "مسدود توسط تنظیمات رویداد",
  DELIVERED: "تحویل‌شده",
  UNDER_REVIEW: "در دست بررسی بازرسی",
  RESOLVED_SUSPENDED: "مختومه و تعلیق آگهی",
  RESOLVED_CONFIRMED: "تأیید تخلف",
  DISMISSED: "ردشده / بدون تخلف",
  INACTIVE: "غیرفعال",
};

export function translateStatus(status: string): string {
  return STATUS_LABELS_FA[status] || status;
}

export const ROLE_LABELS_FA: Record<string, string> = {
  SUPER_ADMIN: "مدیر کل سامانه",
  AGENCY_MANAGER: "مدیر آژانس",
  BRANCH_MANAGER: "مدیر شعبه",
  SALES_MANAGER: "مدیر فروش",
  AGENCY_ACCOUNTANT: "حسابدار آژانس",
  SUPPORT_AGENT: "کارشناس پشتیبانی",
  REAL_ESTATE_AGENT: "مشاور املاک",
  AGENT: "مشاور املاک",
  CUSTOMER: "مشتری / متقاضی",
};
