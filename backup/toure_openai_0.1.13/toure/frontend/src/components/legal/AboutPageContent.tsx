"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Building2, Shield, Users } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { usePublicConfig } from "@/lib/public-config-context";
import type { LegalDocumentItem } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";

export function AboutPageContent() {
  const { getContentBlock, getBrandAsset } = usePublicConfig();
  const overviewBlock = getContentBlock("about_overview");
  const aboutBanner = getBrandAsset("about_banner", false, "");

  const aboutLegalQ = useQuery({
    queryKey: ["public-legal-doc", "about-platform"],
    queryFn: async () => {
      try {
        return (await apiFetch<LegalDocumentItem>("/api/v1/legal/about-platform")).data;
      } catch {
        return null;
      }
    },
  });

  const title =
    overviewBlock?.title_fa ||
    aboutLegalQ.data?.title_fa ||
    "زیرساخت اعتماد، شفافیت مالی و مدیریت علمی در بازار املاک";
  const subtitle =
    overviewBlock?.subtitle_fa ||
    aboutLegalQ.data?.summary ||
    "بنیان ملک با هدف استانداردسازی عملیات آژانس‌های املاک، حفاظت از حریم خصوصی مالکین و متقاضیان، و ارائه ابزارهای دقیق مالی و حقوقی توسعه یافته است.";

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-10">
        {aboutBanner && (
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
            <img
              src={aboutBanner}
              alt={title}
              className="max-h-64 w-full object-cover"
            />
          </div>
        )}

        <div className="space-y-3">
          <div className="text-xs font-bold text-teal-700 dark:text-teal-400">درباره بنیان ملک</div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">{title}</h1>
          <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{subtitle}</p>
        </div>

        {(overviewBlock?.body_html || aboutLegalQ.data?.body_html) && (
          <div
            className="rounded-xl border border-slate-200 bg-white p-6 sm:p-8 text-sm leading-relaxed text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 [&_h2]:mt-4 [&_h2]:mb-2 [&_h2]:text-base [&_h2]:font-bold [&_p]:mb-3 [&_ul]:list-disc [&_ul]:pr-5"
            dangerouslySetInnerHTML={{
              __html: overviewBlock?.body_html || aboutLegalQ.data?.body_html || "",
            }}
          />
        )}

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Shield className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">ایزوله‌سازی سخت‌گیرانه داده‌ها</h2>
            <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              فایل‌های اختصاصی و فهرست مشتریان هر آژانس کاملاً ایزوله است و پلاک و اطلاعات مالک بدون مجوز افشا نمی‌شود.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Building2 className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">پشتیبانی از شبکه‌های چندشعبه‌ای</h2>
            <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              طراحی‌شده برای دفاتر تک‌شعبه‌ای تا هلدینگ‌های املاک با ده‌ها شعبه، قراردادهای همکاری متقابل و حسابداری یکپارچه.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2">
            <Users className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">تیم مهندسی و حقوقی متخصص</h2>
            <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              همراهی مداوم با مدیران آژانس‌ها برای انطباق قالب‌های قرارداد، محاسبات مالیاتی و گزارش‌های مدیریتی.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          {overviewBlock?.cta_label && overviewBlock?.cta_href && (
            <Link
              href={overviewBlock.cta_href}
              className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-5 text-xs font-semibold text-white"
            >
              {overviewBlock.cta_label}
            </Link>
          )}
          <Link href="/careers" className="inline-flex h-10 items-center rounded-lg bg-teal-700 px-5 text-xs font-semibold text-white">
            فرصت‌های شغلی و پیوستن به تیم
          </Link>
          <Link href="/contact" className="inline-flex h-10 items-center rounded-lg border border-slate-300 dark:border-slate-700 px-5 text-xs font-semibold text-slate-800 dark:text-slate-200">
            تماس با ما
          </Link>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
