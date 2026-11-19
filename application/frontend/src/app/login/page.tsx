"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Building2, KeyRound, LogIn, ShieldCheck, Zap } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { ErrorState } from "@/components/ui/StateNotice";
import { useToast } from "@/components/ui/ToastProvider";

const loginSchema = z.object({
  phone_number: z.string().min(7, "شماره موبایل معتبر وارد کنید"),
  password: z.string().min(6, "رمز عبور حداقل ۶ کاراکتر باشد"),
});

type LoginValues = z.infer<typeof loginSchema>;

export interface DemoAccountRow {
  roleCode: string;
  label: string;
  scope: string;
  phone: string;
  pass: string;
}

const DEMO_ACCOUNTS: DemoAccountRow[] = [
  {
    roleCode: "SUPER_ADMIN",
    label: "مدیر کل پلتفرم",
    scope: "نظارت سراسری آژانس‌ها، اشتراک‌ها، سئو و CMS",
    phone: "09120000001",
    pass: "Admin@12345",
  },
  {
    roleCode: "AGENCY_MANAGER",
    label: "مدیر آژانس پارس نگین",
    scope: "کنترل کامل شعب، فایل‌ها، قراردادها و کمیسیون",
    phone: "09121111111",
    pass: "Manager@12345",
  },
  {
    roleCode: "SALES_MANAGER",
    label: "مدیر فروش آژانس",
    scope: "مدیریت پایپ‌لاین فروش، مذاکرات، تیم مشاوران و تحلیل",
    phone: "09127777777",
    pass: "Sales@12345",
  },
  {
    roleCode: "BRANCH_MANAGER",
    label: "مدیر شعبه نیاوران",
    scope: "تأیید فایل، مدیریت مشاوران و پایپ‌لاین شعبه",
    phone: "09125555555",
    pass: "Branch@12345",
  },
  {
    roleCode: "AGENCY_ACCOUNTANT",
    label: "حسابدار آژانس",
    scope: "کدینگ حساب‌ها، سند دوبل، خزانه چک و حقوق",
    phone: "09126666666",
    pass: "Accountant@12345",
  },
  {
    roleCode: "SUPPORT_AGENT",
    label: "کارشناس پشتیبانی",
    scope: "پاسخگویی تیکت‌های SLA، شکایات و نظرسنجی‌ها",
    phone: "09128888888",
    pass: "Support@12345",
  },
  {
    roleCode: "AGENT",
    label: "مشاور املاک",
    scope: "فایل‌های شخصی، سرنخ‌ها، بازدیدها و پورسانت",
    phone: "09122222222",
    pass: "Agent@12345",
  },
  {
    roleCode: "AGENCY_MANAGER_B",
    label: "مدیر آژانس آریا",
    scope: "تست ایزوله‌سازی کامل داده‌های مستأجر دوم",
    phone: "09123333333",
    pass: "Manager@12345",
  },
  {
    roleCode: "CUSTOMER",
    label: "مشتری / متقاضی",
    scope: "پورتال متقاضی، بازدیدها و پیگیری تیکت‌ها",
    phone: "09124444444",
    pass: "Customer@12345",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [quickLoadingPhone, setQuickLoadingPhone] = useState<string | null>(null);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaCode, setMfaCode] = useState("");

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { phone_number: "", password: "" },
  });

  const performLogin = async (phone: string, password: string, otp?: string) => {
    setErrorMsg(null);
    try {
      const profile = await login(phone, password, otp);
      toast.success("ورود موفق", `خوش آمدید، ${profile.full_name}`);
      router.push("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "خطا در ورود به حساب";
      if (msg.includes("دوعاملی") || msg.toUpperCase().includes("MFA")) {
        setMfaRequired(true);
      }
      setErrorMsg(msg);
    }
  };

  const onSubmit = async (values: LoginValues) => {
    await performLogin(values.phone_number, values.password, mfaCode);
  };

  const handleInstantLogin = async (acc: DemoAccountRow) => {
    setValue("phone_number", acc.phone);
    setValue("password", acc.pass);
    setMfaRequired(false);
    setMfaCode("");
    setQuickLoadingPhone(acc.phone);
    try {
      await performLogin(acc.phone, acc.pass);
    } finally {
      setQuickLoadingPhone(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
        <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-12">
          {/* Login Form Card */}
          <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-xs dark:border-slate-800 dark:bg-slate-900 lg:col-span-5">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-700 text-white dark:bg-teal-600">
                <Building2 className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  ورود به سامانه بنیان ملک
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  احراز هویت متمرکز آژانس‌ها، شعب، مالی و مشتریان
                </p>
              </div>
            </div>

            {errorMsg && (
              <div className="mb-4">
                <ErrorState message={errorMsg} />
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  شماره موبایل
                </label>
                <input
                  {...register("phone_number")}
                  dir="ltr"
                  placeholder="09121111111"
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-left font-mono text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
                {errors.phone_number && (
                  <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">
                    {errors.phone_number.message}
                  </p>
                )}
              </div>

              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    رمز عبور
                  </label>
                  <Link
                    href="/forgot-password"
                    className="text-xs font-medium text-teal-700 hover:underline dark:text-teal-400"
                  >
                    فراموشی رمز با پیامک OTP
                  </Link>
                </div>
                <input
                  type="password"
                  dir="ltr"
                  {...register("password")}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-left font-mono text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
                {errors.password && (
                  <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">
                    {errors.password.message}
                  </p>
                )}
              </div>

              {mfaRequired && (
                <div>
                  <label className="mb-1 block text-xs font-semibold text-amber-700 dark:text-amber-400">
                    کد تایید دوعاملی (۶ رقمی TOTP)
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    dir="ltr"
                    maxLength={6}
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value)}
                    placeholder="123456"
                    className="h-10 w-full rounded-lg border border-amber-400 bg-white px-3 text-left font-mono text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-amber-600 dark:bg-slate-950 dark:text-slate-100"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting || quickLoadingPhone !== null}
                className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-teal-700 text-sm font-semibold text-white transition-colors hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
              >
                <LogIn className="h-4 w-4" />
                {isSubmitting ? "در حال احراز هویت..." : "ورود به پنل"}
              </button>
            </form>

            <div className="mt-5 flex items-center justify-between border-t border-slate-200 pt-4 text-xs text-slate-600 dark:border-slate-800 dark:text-slate-400">
              <span>حساب کاربری ندارید؟</span>
              <Link
                href="/register"
                className="inline-flex items-center gap-1 font-semibold text-teal-700 hover:underline dark:text-teal-400"
              >
                ثبت‌نام سریع در سامانه
                <ArrowLeft className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>

          {/* 9-Role Quick Login & Auto-Fill Matrix */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900 lg:col-span-7">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-4 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="h-5 w-5 text-teal-700 dark:text-teal-400" />
                <div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    ورود فوری با هر ۹ نقش و حساب سازمانی و پورتال
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    احراز هویت واقعی JWT از طریق سرویس FastAPI و کنترل دسترسی RBAC
                  </p>
                </div>
              </div>
            </div>

            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {DEMO_ACCOUNTS.map((acc) => {
                const isBusy = quickLoadingPhone === acc.phone;
                return (
                  <div
                    key={acc.phone}
                    className="flex flex-col justify-between gap-3 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                          {acc.label}
                        </span>
                        <span
                          className="font-mono text-xs text-slate-500 dark:text-slate-400"
                          dir="ltr"
                        >
                          {acc.phone}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {acc.scope}
                      </p>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        type="button"
                        disabled={isSubmitting || quickLoadingPhone !== null}
                        onClick={() => {
                          setValue("phone_number", acc.phone);
                          setValue("password", acc.pass);
                          toast.success("اطلاعات تکمیل شد", `فرم با حساب ${acc.label} پر شد.`);
                        }}
                        className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                      >
                        <KeyRound className="h-3.5 w-3.5" />
                        تکمیل فرم
                      </button>

                      <button
                        type="button"
                        disabled={isSubmitting || quickLoadingPhone !== null}
                        onClick={() => handleInstantLogin(acc)}
                        className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white transition-colors hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
                      >
                        <Zap className="h-3.5 w-3.5" />
                        {isBusy ? "در حال ورود..." : "ورود فوری"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
