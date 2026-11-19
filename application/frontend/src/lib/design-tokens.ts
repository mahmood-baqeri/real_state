export type ShowcaseStyleId =
  | "cinematic-dark"
  | "luxury-light"
  | "real-estate-visual"
  | "advanced-analytics";

export interface DesignStylePreset {
  id: ShowcaseStyleId;
  titleFa: string;
  subtitleEn: string;
  summaryFa: string;
  surfaceClass: string;
  recommendedFor: string[];
}

export const DESIGN_STYLE_PRESETS: DesignStylePreset[] = [
  {
    id: "cinematic-dark",
    titleFa: "نمای سینمایی تیره (Cinematic Dark)",
    subtitleEn: "Cinematic Dark",
    summaryFa:
      "سطوح لایه‌بندی‌شده شب‌رنگ، نورپردازی کنترل‌شده، کنتراست بالا و تمرکز عمیق برای میزکارهای شبانه و نمایشگرهای مدیریتی.",
    surfaceClass:
      "border-slate-700/80 bg-slate-950 text-slate-100 cinematic-glow",
    recommendedFor: ["داشبورد مدیریتی", "مرکز عملیات", "پایش لحظه‌ای"],
  },
  {
    id: "luxury-light",
    titleFa: "نمای لوکس روشن (Luxury Light)",
    subtitleEn: "Luxury Light",
    summaryFa:
      "پس‌زمینه عاجی گرم، خطوط مرزی ظریف، تایپوگرافی خوانا و فضای تنفس بالا برای کار روزانه و نمایش حرفه‌ای به مشتریان.",
    surfaceClass:
      "border-[#e5e2dc] bg-[#faf9f6] text-slate-900 luxury-backdrop",
    recommendedFor: ["پورتال عمومی", "صفحات برند و معرفی", "اسناد و قراردادها"],
  },
  {
    id: "real-estate-visual",
    titleFa: "نمای بصری املاک (Real Estate Visual)",
    subtitleEn: "Real Estate Visual",
    summaryFa:
      "گالری تمام‌عرض، لایت‌باکس تصویر، نقشه تعاملی محله و کارت‌های معماری با نسبت ۱۶:۱۰ برای تصمیم‌گیری سریع خریدار.",
    surfaceClass:
      "border-teal-200/80 bg-white text-slate-900 dark:border-teal-900/60 dark:bg-slate-900 dark:text-slate-100",
    recommendedFor: ["جستجوی نقشه و ملک", "صفحه جزئیات ملک", "مقایسه املاک"],
  },
  {
    id: "advanced-analytics",
    titleFa: "نمای تحلیل پیشرفته (Advanced Analytics)",
    subtitleEn: "Advanced Analytics",
    summaryFa:
      "نمودارهای تعاملی قیف فروش، نقشه حرارتی هفتگی، مقایسه شعب و جداول متراکم با خروجی Excel/CSV و فیلترهای چندلایه.",
    surfaceClass:
      "border-amber-200/80 bg-white text-slate-900 dark:border-amber-900/50 dark:bg-slate-900 dark:text-slate-100",
    recommendedFor: ["گزارش‌های BI", "حسابداری و تراز", "تطبیق هوشمند"],
  },
];

export const CHART_COLORS = {
  teal: "#0f766e",
  tealBright: "#14b8a6",
  amber: "#b45309",
  amberBright: "#f59e0b",
  indigo: "#4f46e5",
  emerald: "#059669",
  rose: "#e11d48",
  slate: "#64748b",
};
