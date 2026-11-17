"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { UserPlus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Label, FieldError } from "@/components/ui/Input";

const schema = z.object({
  first_name: z.string().min(2, "نام الزامی است"),
  last_name: z.string().min(2, "نام خانوادگی الزامی است"),
  phone_number: z.string().min(7, "شماره موبایل معتبر وارد کنید"),
  email: z.string().email("ایمیل نامعتبر").optional().or(z.literal("")),
  password: z.string().min(8, "رمز عبور حداقل ۸ کاراکتر باشد"),
});
type Values = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: Values) => {
    setErrMsg(null);
    try {
      await apiFetch("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          ...values,
          email: values.email || null,
          preferred_language: "fa",
          preferred_calendar: "jalali",
          preferred_currency: "IRT",
        }),
      });
      await login(values.phone_number, values.password);
      toast.success("ثبت‌نام موفق", "در حال انتقال به میز کار...");
      router.push("/dashboard");
    } catch (err) {
      setErrMsg(err instanceof Error ? err.message : "خطا در ثبت‌نام");
    }
  };

  return (
    <Card className="p-6">
      <div className="mb-5">
        <h1 className="text-lg font-bold text-fg">ایجاد حساب جدید</h1>
        <p className="mt-1 text-xs text-fg-secondary">
          پس از ثبت‌نام می‌توانید بازدید ثبت کنید یا آژانس بسازید.
        </p>
      </div>

      {errMsg && (
        <div className="mb-4 rounded-lg border border-danger-500/40 bg-danger-50 px-3 py-2 text-xs text-danger-700">
          {errMsg}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label required>نام</Label>
            <Input invalid={!!errors.first_name} {...register("first_name")} />
            <FieldError>{errors.first_name?.message}</FieldError>
          </div>
          <div>
            <Label required>نام خانوادگی</Label>
            <Input invalid={!!errors.last_name} {...register("last_name")} />
            <FieldError>{errors.last_name?.message}</FieldError>
          </div>
        </div>

        <div>
          <Label required>شماره موبایل</Label>
          <Input
            dir="ltr"
            placeholder="0912..."
            invalid={!!errors.phone_number}
            {...register("phone_number")}
          />
          <FieldError>{errors.phone_number?.message}</FieldError>
        </div>

        <div>
          <Label>ایمیل (اختیاری)</Label>
          <Input
            type="email"
            dir="ltr"
            invalid={!!errors.email}
            {...register("email")}
          />
          <FieldError>{errors.email?.message}</FieldError>
        </div>

        <div>
          <Label required>رمز عبور (حداقل ۸ کاراکتر)</Label>
          <Input
            type="password"
            dir="ltr"
            invalid={!!errors.password}
            {...register("password")}
          />
          <FieldError>{errors.password?.message}</FieldError>
        </div>

        <Button
          type="submit"
          size="lg"
          loading={isSubmitting}
          leftIcon={<UserPlus className="h-4 w-4" />}
          className="w-full"
        >
          {isSubmitting ? "در حال ثبت‌نام..." : "تکمیل ثبت‌نام"}
        </Button>

        <p className="text-center text-xs text-fg-secondary">
          قبلاً ثبت‌نام کرده‌اید؟{" "}
          <Link href="/login" className="font-semibold text-brand-700 hover:underline">
            ورود به حساب
          </Link>
        </p>
      </form>
    </Card>
  );
}