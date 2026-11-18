"use client";

import React, { useMemo, useState } from "react";
import { Calculator } from "lucide-react";
import { formatMoney, formatNumberFa } from "@/lib/formatters";
import { useAuth } from "@/lib/auth-context";

const DEAL_PRESETS = [
  { label: "۱۵ میلیارد تومان", value: 15_000_000_000 },
  { label: "۲۹/۴ میلیارد تومان", value: 29_400_000_000 },
  { label: "۴۵ میلیارد تومان", value: 45_000_000_000 },
  { label: "۶۸ میلیارد تومان", value: 68_000_000_000 },
];

export function CommissionCalculatorPreview() {
  const { currencyMode } = useAuth();
  const displayCur = currencyMode === "IRR" ? "IRR" : "IRT";

  const [dealValue, setDealValue] = useState<number>(29_400_000_000);
  const [grossRatePercent, setGrossRatePercent] = useState<number>(1.0);
  const [taxPercent, setTaxPercent] = useState<number>(10);
  const [agentSharePercent, setAgentSharePercent] = useState<number>(50);

  const calc = useMemo(() => {
    const gross = Math.round((dealValue * grossRatePercent) / 100);
    const tax = Math.round((gross * taxPercent) / 100);
    const netDistributable = gross - tax;
    const agentShare = Math.round((netDistributable * agentSharePercent) / 100);
    const agencyShare = netDistributable - agentShare;
    return {
      gross,
      tax,
      netDistributable,
      agentShare,
      agencyShare,
    };
  }, [dealValue, grossRatePercent, taxPercent, agentSharePercent]);

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs font-bold tracking-wide text-amber-700 dark:text-amber-400">
            ۰۴. موتور مالی و حسابداری دوطرفه
          </p>
          <h2
            className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100 sm:text-3xl"
            style={{ textWrap: "balance" }}
          >
            محاسبه زنده کمیسیون و صدور خودکار سند متوازن
          </h2>
        </div>
        <p className="max-w-md text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          ارزش معامله و درصد تقسیم را تغییر دهید تا تفکیک دقیق مالیات، سهم مشاور، سهم آژانس و
          آرتیکل‌های سند دوبل را هم‌زمان ببینید.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Controls */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 lg:col-span-5">
          <div className="mb-5 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            <Calculator className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            پارامترهای معامله و تعرفه کمیسیون
          </div>

          <div className="space-y-5">
            <div>
              <div className="mb-2 flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  ارزش قطعی معامله
                </span>
                <span className="tabular-nums font-bold text-teal-800 dark:text-teal-300">
                  {formatMoney(dealValue, "IRT", displayCur)}
                </span>
              </div>
              <input
                type="range"
                min={5_000_000_000}
                max={80_000_000_000}
                step={500_000_000}
                value={dealValue}
                onChange={(e) => setDealValue(Number(e.target.value))}
                aria-label="مبلغ معامله"
                className="w-full accent-teal-700 dark:accent-teal-500"
              />
              <div className="mt-2 flex flex-wrap gap-1.5">
                {DEAL_PRESETS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setDealValue(p.value)}
                    className={`rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors ${
                      dealValue === p.value
                        ? "border-teal-700 bg-teal-700 text-white dark:border-teal-500 dark:bg-teal-600"
                        : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
              <div>
                <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                  نرخ کمیسیون (٪)
                </label>
                <select
                  value={grossRatePercent}
                  onChange={(e) => setGrossRatePercent(Number(e.target.value))}
                  className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs font-semibold text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                >
                  <option value={0.5}>۰/۵ درصد</option>
                  <option value={1.0}>۱/۰ درصد</option>
                  <option value={1.5}>۱/۵ درصد</option>
                  <option value={2.0}>۲/۰ درصد</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                  مالیات قانونی (٪)
                </label>
                <select
                  value={taxPercent}
                  onChange={(e) => setTaxPercent(Number(e.target.value))}
                  className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs font-semibold text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                >
                  <option value={0}>معاف (۰٪)</option>
                  <option value={10}>۱۰ درصد</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                  سهم مشاور اول (٪)
                </label>
                <select
                  value={agentSharePercent}
                  onChange={(e) => setAgentSharePercent(Number(e.target.value))}
                  className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs font-semibold text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                >
                  <option value={40}>۴۰٪ مشاور / ۶۰٪ آژانس</option>
                  <option value={50}>۵۰٪ مشاور / ۵۰٪ آژانس</option>
                  <option value={60}>۶۰٪ مشاور / ۴۰٪ آژانس</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950">
                <div className="text-[11px] text-slate-500 dark:text-slate-400">سهم خالص آژانس</div>
                <div className="mt-1 tabular-nums text-sm font-bold text-slate-900 dark:text-slate-100">
                  {formatMoney(calc.agencyShare, "IRT", displayCur)}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950">
                <div className="text-[11px] text-slate-500 dark:text-slate-400">پورسانت قابل پرداخت مشاور</div>
                <div className="mt-1 tabular-nums text-sm font-bold text-teal-800 dark:text-teal-300">
                  {formatMoney(calc.agentShare, "IRT", displayCur)}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Live Double-Entry Voucher Output */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 lg:col-span-7">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4 dark:border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                پیش‌نمایش سند حسابداری دوطرفه (Double-Entry Journal)
              </h3>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                در لایه بک‌اند فقط اسناد با جمع بدهکار برابر بستانکار مجاز به قطعی‌سازی هستند.
              </p>
            </div>
            <span className="tabular-nums font-mono text-xs font-semibold text-teal-700 dark:text-teal-400">
              تراز: {formatNumberFa(0)} اختلاف
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-right text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <th className="py-2.5 font-semibold">کد و عنوان حساب</th>
                  <th className="py-2.5 font-semibold">شرح آرتیکل</th>
                  <th className="py-2.5 text-left font-semibold">بدهکار</th>
                  <th className="py-2.5 text-left font-semibold">بستانکار</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                <tr>
                  <td className="py-3 font-semibold text-slate-900 dark:text-slate-100">
                    <span className="ml-1.5 font-mono text-slate-400">1103</span>
                    حساب‌های دریافتنی
                  </td>
                  <td className="py-3 text-slate-600 dark:text-slate-400">
                    مطالبه کارمزد کل معامله از طرفین
                  </td>
                  <td className="py-3 text-left tabular-nums font-bold text-slate-900 dark:text-slate-100">
                    {formatMoney(calc.gross, "IRT", displayCur)}
                  </td>
                  <td className="py-3 text-left tabular-nums text-slate-400">۰</td>
                </tr>
                <tr>
                  <td className="py-3 font-semibold text-slate-900 dark:text-slate-100">
                    <span className="ml-1.5 font-mono text-slate-400">4101</span>
                    درآمد کمیسیون آژانس
                  </td>
                  <td className="py-3 text-slate-600 dark:text-slate-400">
                    سهم {formatNumberFa(100 - agentSharePercent)}٪ آژانس از خالص
                  </td>
                  <td className="py-3 text-left tabular-nums text-slate-400">۰</td>
                  <td className="py-3 text-left tabular-nums font-bold text-teal-800 dark:text-teal-300">
                    {formatMoney(calc.agencyShare, "IRT", displayCur)}
                  </td>
                </tr>
                <tr>
                  <td className="py-3 font-semibold text-slate-900 dark:text-slate-100">
                    <span className="ml-1.5 font-mono text-slate-400">2104</span>
                    کمیسیون پرداختنی مشاوران
                  </td>
                  <td className="py-3 text-slate-600 dark:text-slate-400">
                    سهم {formatNumberFa(agentSharePercent)}٪ منتقل‌شده به حقوق ماهانه
                  </td>
                  <td className="py-3 text-left tabular-nums text-slate-400">۰</td>
                  <td className="py-3 text-left tabular-nums font-bold text-teal-800 dark:text-teal-300">
                    {formatMoney(calc.agentShare, "IRT", displayCur)}
                  </td>
                </tr>
                {calc.tax > 0 && (
                  <tr>
                    <td className="py-3 font-semibold text-slate-900 dark:text-slate-100">
                      <span className="ml-1.5 font-mono text-slate-400">2109</span>
                      مالیات و عوارض پرداختنی
                    </td>
                    <td className="py-3 text-slate-600 dark:text-slate-400">
                      کسر {formatNumberFa(taxPercent)}٪ مالیات بر ارزش افزوده
                    </td>
                    <td className="py-3 text-left tabular-nums text-slate-400">۰</td>
                    <td className="py-3 text-left tabular-nums font-bold text-amber-700 dark:text-amber-400">
                      {formatMoney(calc.tax, "IRT", displayCur)}
                    </td>
                  </tr>
                )}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-slate-200 bg-slate-50/70 font-bold text-slate-900 dark:border-slate-700 dark:bg-slate-800/40 dark:text-slate-100">
                  <td colSpan={2} className="py-3 pr-2">
                    جمع کل سند تراز (بدهکار = بستانکار)
                  </td>
                  <td className="py-3 text-left tabular-nums">
                    {formatMoney(calc.gross, "IRT", displayCur)}
                  </td>
                  <td className="py-3 text-left tabular-nums text-teal-800 dark:text-teal-300">
                    {formatMoney(calc.agencyShare + calc.agentShare + calc.tax, "IRT", displayCur)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
