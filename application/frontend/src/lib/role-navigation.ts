import type { EffectiveRole, PlatformRole } from "./types";

export interface NavItemConfig {
  key: string;
  label: string;
  href: string;
  group: "core" | "portfolio" | "crm" | "deals" | "finance" | "admin";
  roles: EffectiveRole[];
  requiredPermission?: string;
}

export const NAV_GROUP_LABELS: Record<NavItemConfig["group"], string> = {
  core: "نمای کلی",
  portfolio: "ملک و اسناد",
  crm: "مشتریان و بازاریابی",
  deals: "مذاکره و معاملات",
  finance: "مالی و منابع انسانی",
  admin: "مدیریت و تنظیمات",
};

export const ALL_NAV_ITEMS: NavItemConfig[] = [
  {
    key: "overview",
    label: "داشبورد مدیریتی",
    href: "/dashboard",
    group: "core",
    roles: [
      "SUPER_ADMIN",
      "AGENCY_MANAGER",
      "SALES_MANAGER",
      "BRANCH_MANAGER",
      "AGENCY_ACCOUNTANT",
      "SUPPORT_AGENT",
      "AGENT",
      "CUSTOMER",
    ],
  },
  {
    key: "admin",
    label: "مدیریت کل پلتفرم",
    href: "/dashboard/admin",
    group: "core",
    roles: ["SUPER_ADMIN"],
  },
  {
    key: "agencies",
    label: "آژانس‌ها و شعب",
    href: "/dashboard/agencies",
    group: "core",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "BRANCH_MANAGER"],
  },
  {
    key: "properties",
    label: "فهرست املاک",
    href: "/dashboard/properties",
    group: "portfolio",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENT"],
  },
  {
    key: "documents",
    label: "اسناد و فایل‌ها",
    href: "/dashboard/documents",
    group: "portfolio",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT", "AGENT"],
  },
  {
    key: "customers",
    label: "مشتریان و اشتراک‌گذاری",
    href: "/dashboard/customers",
    group: "crm",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "SUPPORT_AGENT", "AGENT"],
  },
  {
    key: "leads",
    label: "سرنخ‌ها (Leads)",
    href: "/dashboard/leads",
    group: "crm",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENT"],
  },
  {
    key: "crm",
    label: "پایپ‌لاین CRM و تطبیق",
    href: "/dashboard/crm",
    group: "crm",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENT"],
  },
  {
    key: "appointments",
    label: "بازدیدها و تقویم",
    href: "/dashboard/appointments",
    group: "crm",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "SUPPORT_AGENT", "AGENT", "CUSTOMER"],
  },
  {
    key: "negotiations",
    label: "مذاکرات و پیشنهادها",
    href: "/dashboard/negotiations",
    group: "deals",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENT"],
  },
  {
    key: "contracts",
    label: "قراردادها و قالب‌ها",
    href: "/dashboard/contracts",
    group: "deals",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT", "AGENT"],
  },
  {
    key: "deals",
    label: "معاملات",
    href: "/dashboard/deals",
    group: "deals",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT", "AGENT"],
  },
  {
    key: "commissions",
    label: "کمیسیون‌ها و تقسیم سهم",
    href: "/dashboard/commissions",
    group: "deals",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "AGENCY_ACCOUNTANT", "AGENT"],
  },
  {
    key: "accounting",
    label: "حسابداری دوبل و خزانه",
    href: "/dashboard/accounting",
    group: "finance",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "AGENCY_ACCOUNTANT"],
    requiredPermission: "accounting.view",
  },
  {
    key: "payroll",
    label: "حقوق و دستمزد",
    href: "/dashboard/payroll",
    group: "finance",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "AGENCY_ACCOUNTANT"],
  },
  {
    key: "subscriptions",
    label: "اشتراک و درگاه پرداخت",
    href: "/dashboard/subscriptions",
    group: "finance",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER"],
  },
  {
    key: "reports",
    label: "گزارش‌ها و تحلیل",
    href: "/dashboard/reports",
    group: "finance",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT"],
  },
  {
    key: "team",
    label: "تیم آژانس",
    href: "/dashboard/team",
    group: "admin",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER"],
  },
  {
    key: "employees",
    label: "کارکنان و جبران خدمت",
    href: "/dashboard/employees",
    group: "admin",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT"],
  },
  {
    key: "agents",
    label: "مشاوران املاک",
    href: "/dashboard/agents",
    group: "admin",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER"],
  },
  {
    key: "roles",
    label: "نقش‌ها و سیاست دسترسی",
    href: "/dashboard/roles",
    group: "admin",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER"],
  },
  {
    key: "notifications",
    label: "اعلان‌ها و پوش",
    href: "/dashboard/notifications",
    group: "admin",
    roles: [
      "SUPER_ADMIN",
      "AGENCY_MANAGER",
      "SALES_MANAGER",
      "BRANCH_MANAGER",
      "AGENCY_ACCOUNTANT",
      "SUPPORT_AGENT",
      "AGENT",
      "CUSTOMER",
    ],
  },
  {
    key: "tickets",
    label: "تیکت‌های پشتیبانی",
    href: "/dashboard/tickets",
    group: "admin",
    roles: [
      "SUPER_ADMIN",
      "AGENCY_MANAGER",
      "SALES_MANAGER",
      "BRANCH_MANAGER",
      "AGENCY_ACCOUNTANT",
      "SUPPORT_AGENT",
      "AGENT",
      "CUSTOMER",
    ],
  },
  {
    key: "complaints",
    label: "شکایات و پیگیری",
    href: "/dashboard/complaints",
    group: "admin",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "BRANCH_MANAGER", "SUPPORT_AGENT", "CUSTOMER"],
  },
  {
    key: "surveys",
    label: "نظرسنجی و تحلیل",
    href: "/dashboard/surveys",
    group: "crm",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "SUPPORT_AGENT"],
  },
  {
    key: "ai",
    label: "دستیار هوشمند آژانس",
    href: "/dashboard/ai-assistant",
    group: "crm",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER", "SALES_MANAGER", "BRANCH_MANAGER", "AGENT"],
  },
  {
    key: "cms",
    label: "مدیریت محتوا، سئو و درخواست‌ها",
    href: "/dashboard/cms",
    group: "admin",
    roles: ["SUPER_ADMIN", "AGENCY_MANAGER"],
  },
  {
    key: "settings",
    label: "تنظیمات سیستم",
    href: "/dashboard/settings",
    group: "admin",
    roles: ["SUPER_ADMIN"],
  },
  {
    key: "audit",
    label: "گزارش ممیزی (Audit)",
    href: "/dashboard/audit",
    group: "admin",
    roles: ["SUPER_ADMIN"],
  },
  {
    key: "profile",
    label: "پروفایل و نشست‌ها",
    href: "/dashboard/profile",
    group: "admin",
    roles: [
      "SUPER_ADMIN",
      "AGENCY_MANAGER",
      "SALES_MANAGER",
      "BRANCH_MANAGER",
      "AGENCY_ACCOUNTANT",
      "SUPPORT_AGENT",
      "AGENT",
      "CUSTOMER",
    ],
  },
];

export function resolveEffectiveRole(
  platformRole?: PlatformRole | null,
  agencyRoleCode?: string | null
): EffectiveRole {
  if (platformRole === "SUPER_ADMIN") return "SUPER_ADMIN";
  if (platformRole === "CUSTOMER") return "CUSTOMER";
  if (agencyRoleCode === "AGENCY_MANAGER") return "AGENCY_MANAGER";
  if (agencyRoleCode === "SALES_MANAGER") return "SALES_MANAGER";
  if (agencyRoleCode === "BRANCH_MANAGER") return "BRANCH_MANAGER";
  if (agencyRoleCode === "AGENCY_ACCOUNTANT") return "AGENCY_ACCOUNTANT";
  if (agencyRoleCode === "SUPPORT_AGENT") return "SUPPORT_AGENT";
  if (platformRole === "AGENCY_USER") return "AGENT";
  return "CUSTOMER";
}

export function getNavigationForUser(
  platformRole?: PlatformRole | null,
  agencyRoleCode?: string | null,
  effectivePermissions: string[] = []
): NavItemConfig[] {
  const effective = resolveEffectiveRole(platformRole, agencyRoleCode);
  return ALL_NAV_ITEMS.filter((item) => {
    if (!item.roles.includes(effective)) return false;
    if (
      item.requiredPermission &&
      effective !== "SUPER_ADMIN" &&
      effectivePermissions.length > 0 &&
      !effectivePermissions.includes(item.requiredPermission)
    ) {
      return false;
    }
    return true;
  });
}

export function getRoleNavigationKeys(
  platformRole?: PlatformRole | null,
  agencyRoleCode?: string | null
): string[] {
  return getNavigationForUser(platformRole, agencyRoleCode).map((i) => i.key);
}
