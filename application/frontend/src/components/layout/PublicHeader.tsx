"use client";

import React from "react";
import Link from "next/link";
import { Building2, LayoutDashboard, LogIn } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function PublicHeader() {
  const { user } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-700 text-white">
            <Building2 className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold leading-none text-slate-900">بنیان ملک</span>
            <span className="mt-1 text-[11px] leading-none text-slate-500">
              پلتفرم سازمانی مدیریت املاک
            </span>
          </div>
        </Link>

        <nav className="hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex">
          <Link href="/#listings" className="whitespace-nowrap hover:text-teal-700 transition-colors">
            بانک املاک
          </Link>
          <Link href="/#market-trends" className="whitespace-nowrap hover:text-teal-700 transition-colors">
            شاخص قیمت مناطق
          </Link>
          <Link href="/#capabilities" className="whitespace-nowrap hover:text-teal-700 transition-colors">
            زیرساخت آژانس‌ها
          </Link>
          <Link href="/register" className="whitespace-nowrap hover:text-teal-700 transition-colors">
            ثبت‌نام آژانس و مشتری
          </Link>
        </nav>

        <div className="flex shrink-0 items-center gap-2.5">
          {user ? (
            <Link
              href="/dashboard"
              className="inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800 transition-colors"
            >
              <LayoutDashboard className="h-4 w-4" />
              ورود به پنل مدیریت
            </Link>
          ) : (
            <Link
              href="/login"
              className="inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800 transition-colors"
            >
              <LogIn className="h-4 w-4" />
              ورود به سامانه
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
