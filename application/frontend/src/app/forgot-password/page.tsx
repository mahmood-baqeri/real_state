"use client";

import React, { useState } from "react";
import Link from "next/link";
import { KeyRound } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [doneMsg, setDoneMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    try {
      const env = await apiFetch<{ sent: boolean; debug_otp?: string }>(
        "/api/v1/auth/password-reset/request",
        {
          method: "POST",
          body: JSON.stringify({ phone_number: phone }),
        }
      );
      if (env.data?.debug_otp) setDevOtpHint(env.data.debug_otp);
      setStep(2);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "خطا در ارسال کد یک‌بارمصرف");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    try {
      await apiFetch("/api/v1/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({
          phone_number: phone,
          otp_code: otpCode,
          new_password: newPassword,
        }),
      });
      setDoneMsg("رمز عبور با موفقیت تغییر یافت. اکنون می‌توانید وارد شوید.");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "کد تایید نامعتبر است");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <div className="mx-auto flex max-w-md flex-col justify-center px-4 py-12">
        <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/70 dark:bg-amber-950/40 dark:text-amber-300">
              <KeyRound className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                بازیابی رمز عبور
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                ارسال کد تایید پیامکی (SMS Adapter)
              </p>
            </div>
          </div>

          {errorMsg && (
            <div className="mb-4">
              <ErrorState message={errorMsg} />
            </div>
          )}
          {doneMsg && (
            <div className="mb-4 space-y-3">
              <SuccessBanner message={doneMsg} />
              <Link
                href="/login"
                className="flex h-10 w-full items-center justify-center rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 dark:bg-teal-600"
              >
                بازگشت به صفحه ورود
              </Link>
            </div>
          )}

          {!doneMsg && step === 1 && (
            <form onSubmit={handleRequestOtp} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  شماره موبایل
                </label>
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                  dir="ltr"
                  placeholder="09121111111"
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-left font-mono text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
              >
                {loading ? "در حال ارسال..." : "ارسال کد تایید"}
              </button>
            </form>
          )}

          {!doneMsg && step === 2 && (
            <form onSubmit={handleConfirmReset} className="space-y-4">
              {devOtpHint && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-800/70 dark:bg-amber-950/40 dark:text-amber-200">
                  کد ارسال‌شده توسط آداپتر توسعه پیامک:{" "}
                  <span className="font-mono font-bold">{devOtpHint}</span>
                </div>
              )}
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  کد تایید پیامکی
                </label>
                <input
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  required
                  dir="ltr"
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-left font-mono text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  رمز عبور جدید
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  dir="ltr"
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-left font-mono text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600 dark:hover:bg-teal-500"
              >
                {loading ? "در حال ثبت..." : "تایید و تغییر رمز عبور"}
              </button>
            </form>
          )}

          <div className="mt-5 border-t border-slate-200 pt-4 text-center text-xs dark:border-slate-800">
            <Link
              href="/login"
              className="font-medium text-slate-600 hover:text-teal-700 dark:text-slate-400 dark:hover:text-teal-400"
            >
              بازگشت به صفحه ورود
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
