"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Building2, LogIn, Phone, Lock } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Label, FieldError } from "@/components/ui/Input";

const schema = z.object({
  phone_number: z.string().min(7, "شماره موبایل معتبر وارد کنید"),
  password: z.string().min(6, "رمز عبور حداقل ۶ کاراکتر باشد"),
});
type Values = z.infer<typeof schema>;

const DEMO_ACCOUNTS = [
  { label: "مدیر کل پلتفرم", phone: "09120000001", pass: "Admin@12345" },
  { label: "مدیر آژانس", phone: "09121111111", pass: "Manager@12345" },
  { label: "مشاور املاک", phone: "09122222222", pass: "Agent@12345" },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { phone_number: "", password: "" },
  });

  const onSubmit = async (values: Values) => {
    setErrMsg(null);
    setLoading(true);
    try {
      await login(values.phone_number, values.password);
      toast.success("خوش آمدید", "در حال انتقال به میز کار...");
      router.push("/dashboard");
    } catch (err) {
      setErrMsg(err instanceof Error ? err.message : "خطا در ورود");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="overflow-hidden p-0">
      <div className="border-b border-divider px-6 pb-5 pt-6">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
            <Building2 className="h-6 w-6" />
          </span>
          <div>
            <h1 className="text-lg font-bold text-fg">ورود به بنیان ملک</h1>
            <p className="text-xs text-fg-secondary">
              احراز هویت متمرکز آژانس‌ها و مشاوران
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-6">
        {errMsg && (
          <div className="rounded-lg border border-danger-500/40 bg-danger-50 px-3 py-2 text-xs text-danger-700">
            {errMsg}
          </div>
        )}

        <div>
          <Label htmlFor="phone" required>شماره موبایل</Label>
          <Input
            id="phone"
            dir="ltr"
            placeholder="09121111111"
            rightIcon={<Phone className="h-4 w-4" />}
            invalid={!!errors.phone_number}
            {...register("phone_number")}
          />
          <FieldError>{errors.phone_number?.message}</FieldError>
        </div>

        <div>
          <div className="flex items-center justify-between">
            <Label htmlFor="password" required>رمز عبور</Label>
            <Link
              href="/forgot-password"
              className="mb-1.5 text-xs font-semibold text-brand-700 hover:underline"
            >
              فراموشی رمز؟
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            dir="ltr"
            rightIcon={<Lock className="h-4 w-4" />}
            invalid={!!errors.password}
            {...register("password")}
          />
          <FieldError>{errors.password?.message}</FieldError>
        </div>

        <Button
          type="submit"
          size="lg"
          loading={loading}
          leftIcon={<LogIn className="h-4 w-4" />}
          className="w-full"
        >
          {loading ? "در حال ورود..." : "ورود به میز کار"}
        </Button>

        <p className="text-center text-xs text-fg-secondary">
          حساب ندارید؟{" "}
          <Link
            href="/register"
            className="font-semibold text-brand-700 hover:underline"
          >
            ثبت‌نام سریع
          </Link>
        </p>
      </form>

      <div className="border-t border-divider bg-subtle/60 px-6 py-4">
        <p className="mb-2 text-[11px] font-bold text-fg-muted">
          ورود سریع نمونه (کلیک کنید):
        </p>
        <div className="grid grid-cols-1 gap-1.5">
          {DEMO_ACCOUNTS.map((acc) => (
            <button
              key={acc.phone}
              type="button"
              onClick={() => {
                setValue("phone_number", acc.phone);
                setValue("password", acc.pass);
              }}
              className="flex items-center justify-between rounded-md border border-border bg-surface px-2.5 py-1.5 text-[11px] transition-colors hover:border-brand-500 hover:bg-brand-50/40"
            >
              <span className="font-medium text-fg">{acc.label}</span>
              <span className="font-mono text-fg-muted" dir="ltr">
                {acc.phone}
              </span>
            </button>
          ))}
        </div>
      </div>
    </Card>
  );
}