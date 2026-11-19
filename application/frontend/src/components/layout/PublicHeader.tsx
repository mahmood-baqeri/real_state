"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, LayoutDashboard, LogIn, Menu, X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

const NAV_LINKS = [
  { href: "/properties", label: "بانک املاک" },
  { href: "/search", label: "جستجوی نقشه و پیشرفته" },
  { href: "/features", label: "امکانات سامانه" },
  { href: "/pricing", label: "تعرفه‌ها" },
  { href: "/blog", label: "مجله و تحلیل" },
];

export function PublicHeader() {
  const { user } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/90 bg-white/95 backdrop-blur-md dark:border-slate-800/90 dark:bg-slate-900/95">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileMenuOpen((v) => !v)}
            aria-label="منوی پورتال عمومی"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 md:hidden"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <Link href="/" className="flex shrink-0 items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-700 text-white shadow-xs dark:bg-teal-600">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <span className="block whitespace-nowrap text-base font-bold text-slate-900 dark:text-slate-100">
                بنیان ملک
              </span>
            </div>
          </Link>
        </div>

        <nav className="hidden items-center gap-1 text-sm font-medium text-slate-600 dark:text-slate-300 md:flex">
          {NAV_LINKS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap shrink-0 rounded-lg px-3 py-1.5 transition-colors ${
                  active
                    ? "bg-teal-50 font-semibold text-teal-800 dark:bg-teal-950/60 dark:text-teal-300"
                    : "hover:bg-slate-100 hover:text-teal-700 dark:hover:bg-slate-800 dark:hover:text-teal-400"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex shrink-0 items-center gap-2">
          <ThemeToggle variant="compact" />
          {user ? (
            <Link
              href="/dashboard"
              className="inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white transition-colors hover:bg-teal-800 dark:bg-teal-600 dark:hover:bg-teal-500 sm:text-sm"
            >
              <LayoutDashboard className="h-4 w-4" />
              <span>ورود به پنل</span>
            </Link>
          ) : (
            <Link
              href="/login"
              className="inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white transition-colors hover:bg-teal-800 dark:bg-teal-600 dark:hover:bg-teal-500 sm:text-sm"
            >
              <LogIn className="h-4 w-4" />
              <span>ورود به سامانه</span>
            </Link>
          )}
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="border-t border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 md:hidden">
          <nav className="grid grid-cols-2 gap-2">
            {NAV_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-800/70 dark:text-slate-200"
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/agency-application"
              onClick={() => setMobileMenuOpen(false)}
              className="col-span-2 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-center text-xs font-semibold text-teal-800 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-300"
            >
              درخواست همکاری و عضویت آژانس
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
