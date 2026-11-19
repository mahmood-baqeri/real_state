// Path: frontend/src/app/pricing/page.tsx

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { formatMoney, formatNumberFa } from "@/lib/formatters";

interface PlanItem {
  id: string;
  code: string;
  name_fa: string;
  name_en: string;
  monthly_price: string;
  annual_price: string;
  max_agents: number;
  max_branches: number;
  max_active_listings: number;
}

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);

  const plansQ = useQuery({
    queryKey: ["public-plans"],
    queryFn: async () => (await apiFetch<PlanItem[]>("/api/v1/subscriptions/plans")).data,
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center max-w-2xl mx-auto space-y-4">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">تعرفه‌ها و پلن‌های اشتراک آژانس‌ها</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            تعرفه شفاف متناسب با تعداد مشاوران، شعب و حجم فایل‌های فعال آژانس شما
          </p>
          <div className="inline-flex rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-1">
            <button
              type="button"
              onClick={() => setAnnual(false)}
              className={`rounded-lg px-4 py-2 text-xs font-semibold transition-colors ${
                !annual ? "bg-teal-700 text-white" : "text-slate-600 dark:text-slate-300"
              }`}
            >
              پرداخت ماهانه
            </button>
            <button
              type="button"
              onClick={() => setAnnual(true)}
              className={`rounded-lg px-4 py-2 text-xs font-semibold transition-colors ${
                annual ? "bg-teal-700 text-white" : "text-slate-600 dark:text-slate-300"
              }`}
            >
              پرداخت سالانه (۲ ماه تخفیف)
            </button>
          </div>
        </div>

        {plansQ.isLoading ? (
          <LoadingState message="در حال دریافت پلن‌های اشتراک..." />
        ) : plansQ.error ? (
          <ErrorState
            message={plansQ.error instanceof Error ? plansQ.error.message : "خطا در دریافت پلن‌ها"}
            onRetry={() => plansQ.refetch()}
          />
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {(plansQ.data || []).map((plan) => {
              const isPro = plan.code === "PRO";
              const price = annual ? plan.annual_price : plan.monthly_price;
              return (
                <div
                  key={plan.id}
                  className={`flex flex-col justify-between rounded-2xl border p-6 ${
                    isPro
                      ? "border-teal-700 bg-white dark:bg-slate-900 shadow-md"
                      : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
                  }`}
                >
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">{plan.name_fa}</h2>
                      <span className="font-mono text-xs font-semibold text-teal-700 dark:text-teal-400">{plan.code}</span>
                    </div>
                    <div className="border-y border-slate-100 dark:border-slate-800 py-4">
                      <div className="tabular-nums text-2xl font-bold text-slate-900 dark:text-slate-100">
                        {formatMoney(price, "IRT", "IRT")}
                      </div>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {annual ? "صورت‌حساب سالانه" : "صورت‌حساب ماهانه"}
                      </div>
                    </div>
                    <ul className="space-y-2.5 text-xs text-slate-700 dark:text-slate-300">
                      <li className="flex items-center gap-2">
                        <Check className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                        حداکثر {formatNumberFa(plan.max_agents)} مشاور فعال
                      </li>
                      <li className="flex items-center gap-2">
                        <Check className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                        حداکثر {formatNumberFa(plan.max_branches)} شعبه مستقل
                      </li>
                      <li className="flex items-center gap-2">
                        <Check className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                        تا {formatNumberFa(plan.max_active_listings)} فایل ملکی فعال
                      </li>
                      <li className="flex items-center gap-2">
                        <Check className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                        حسابداری دوبل، کمیسیون و گزارش‌های تحلیلی
                      </li>
                    </ul>
                  </div>

                  <Link
                    href="/agency-application"
                    className={`mt-6 inline-flex h-10 items-center justify-center rounded-lg text-xs font-semibold transition-colors ${
                      isPro
                        ? "bg-teal-700 text-white hover:bg-teal-800"
                        : "border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
                    }`}
                  >
                    انتخاب پلن و درخواست فعال‌سازی
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
