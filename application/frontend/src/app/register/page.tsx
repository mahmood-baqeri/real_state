"use client";

// فرم ایجاد حساب و ثبت پذیرش اسناد جاری سامانه.
import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { UserPlus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { usePublicConfig } from "@/lib/public-config-context";
import { formatNumberFa } from "@/lib/formatters";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

const registerSchema = z.object({
  first_name: z.string().min(2, "نام الزامی است"),
  last_name: z.string().min(2, "نام خانوادگی الزامی است"),
  phone_number: z.string().min(7, "شماره موبایل معتبر وارد کنید"),
  email: z.string().optional(),
  password: z.string().min(6, "رمز عبور نامعتبر است"),
  preferred_currency: z.string().default("IRT"),
  preferred_calendar: z.string().default("jalali"),
  accept_legal: z.boolean().default(true),
});

type RegisterValues = z.infer<typeof registerSchema>;

/** داده‌های ثبت‌نام و پذیرش اختیاری یا الزامی قوانین را مدیریت می‌کند. */
export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const { getSetting, currencies, calendars, getContentBlock } = usePublicConfig();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [okMsg, setOkMsg] = useState(false);

  const minLen = Number(getSetting<number>("security.password_min_length", 8) || 8);
  const reqUpper = Boolean(getSetting<boolean>("security.password_require_uppercase", true));
  const reqDigit = Boolean(getSetting<boolean>("security.password_require_digit", true));
  const reqSpecial = Boolean(getSetting<boolean>("security.password_require_special", false));
  const requireTerms = Boolean(
    getSetting<boolean>("compliance.require_terms_acceptance_on_register", true)
  );
  const introBlock = getContentBlock("register_intro");

  const activeCurrencies =
    currencies.length > 0
      ? currencies
      : [
          { code: "IRT", name_fa: "تومان" },
          { code: "IRR", name_fa: "ریال" },
          { code: "USD", name_fa: "دلار" },
        ];
  const activeCalendars =
    calendars.length > 0
      ? calendars
      : [
          { code: "jalali", name_fa: "شمسی" },
          { code: "gregorian", name_fa: "میلادی" },
        ];

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.input<typeof registerSchema>, unknown, RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      preferred_currency: "IRT",
      preferred_calendar: "jalali",
      accept_legal: true,
    },
  });

  const onSubmit = async (values: RegisterValues) => {
    setErrorMsg(null);
    if (values.password.length < minLen) {
      setErrorMsg(`رمز عبور باید حداقل ${formatNumberFa(minLen)} کاراکتر باشد.`);
      return;
    }
    if (requireTerms && !values.accept_legal) {
      setErrorMsg("پذیرش قوانین پلتفرم، شرایط استفاده و سیاست حریم خصوصی برای ثبت‌نام الزامی است.");
      return;
    }

    try {
      await apiFetch("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          first_name: values.first_name,
          last_name: values.last_name,
          phone_number: values.phone_number,
          email: values.email,
          password: values.password,
          preferred_currency: values.preferred_currency,
          preferred_calendar: values.preferred_calendar,
        }),
      });
      setOkMsg(true);
      await login(values.phone_number, values.password);
      if (requireTerms && values.accept_legal) {
        const stored = localStorage.getItem("bonyan_auth_v2");
        const token = stored ? JSON.parse(stored)?.access : null;
        if (token) {
          await Promise.allSettled([
            apiFetch("/api/v1/legal/terms-of-use/accept", { method: "POST", token }),
            apiFetch("/api/v1/legal/privacy-policy/accept", { method: "POST", token }),
          ]);
        }
      }
      router.push("/dashboard");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "خطا در ثبت‌نام");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <div className="mx-auto flex max-w-md flex-col justify-center px-4 py-12">
        <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            {introBlock?.title_fa || "ایجاد حساب کاربری جدید"}
          </h1>
          <p className="mt-1 mb-5 text-xs text-slate-500 dark:text-slate-400">
            {introBlock?.subtitle_fa ||
              "پس از ثبت‌نام می‌توانید بازدید ثبت کنید یا درخواست راه‌اندازی آژانس ارسال کنید."}
          </p>

          {errorMsg && (
            <div className="mb-4">
              <ErrorState message={errorMsg} />
            </div>
          )}
          {okMsg && (
            <div className="mb-4">
              <SuccessBanner message="ثبت‌نام انجام شد. در حال ورود به میز کار..." />
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  نام
                </label>
                <input
                  {...register("first_name")}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
                {errors.first_name && (
                  <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">
                    {errors.first_name.message}
                  </p>
                )}
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  نام خانوادگی
                </label>
                <input
                  {...register("last_name")}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
                {errors.last_name && (
                  <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">
                    {errors.last_name.message}
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                شماره موبایل
              </label>
              <input
                {...register("phone_number")}
                dir="ltr"
                placeholder="0912..."
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-left font-mono text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
              {errors.phone_number && (
                <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">
                  {errors.phone_number.message}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                ایمیل (اختیاری)
              </label>
              <input
                type="email"
                dir="ltr"
                {...register("email")}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-left font-mono text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                رمز عبور (حداقل {formatNumberFa(minLen)} کاراکتر)
              </label>
              <input
                type="password"
                dir="ltr"
                {...register("password")}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-left font-mono text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
              <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                الزامات امنیتی فعلی: حداقل {formatNumberFa(minLen)} کاراکتر
                {reqUpper ? " · حرف بزرگ انگلیسی" : ""}
                {reqDigit ? " · حداقل یک رقم" : ""}
                {reqSpecial ? " · کاراکتر ویژه (!@#)" : ""}
              </p>
              {errors.password && (
                <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">
                  {errors.password.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  واحد پول
                </label>
                <select
                  {...register("preferred_currency")}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                >
                  {activeCurrencies.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name_fa} ({c.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  تقویم
                </label>
                <select
                  {...register("preferred_calendar")}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                >
                  {activeCalendars.map((cal) => (
                    <option key={cal.code} value={cal.code}>
                      {cal.name_fa}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {requireTerms && (
              <label className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-300">
                <input
                  type="checkbox"
                  {...register("accept_legal")}
                  className="mt-0.5 h-4 w-4 accent-teal-700"
                />
                <span>
                  <Link href="/legal/terms-of-use" className="font-semibold text-teal-700 hover:underline dark:text-teal-400">
                    شرایط استفاده
                  </Link>{" "}
                  و{" "}
                  <Link href="/legal/privacy-policy" className="font-semibold text-teal-700 hover:underline dark:text-teal-400">
                    سیاست حریم خصوصی
                  </Link>{" "}
                  را مطالعه کرده و می‌پذیرم.
                </span>
              </label>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
            >
              <UserPlus className="h-4 w-4" />
              {isSubmitting ? "در حال ثبت‌نام..." : "تکمیل ثبت‌نام"}
            </button>
          </form>

          <div className="mt-5 border-t border-slate-200 pt-4 text-center text-xs text-slate-600 dark:border-slate-800 dark:text-slate-400">
            قبلاً ثبت‌نام کرده‌اید؟{" "}
            <Link
              href="/login"
              className="font-semibold text-teal-700 hover:underline dark:text-teal-400"
            >
              ورود به حساب
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
