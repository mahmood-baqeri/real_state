// Path: frontend/src/app/faq/page.tsx

"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, HelpCircle } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { buildFaqJsonLd } from "@/lib/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

interface FaqRow {
  id: string;
  category: string;
  question: string;
  answer: string;
}

export default function FaqPage() {
  const [openId, setOpenId] = useState<string | null>(null);

  const faqsQ = useQuery({
    queryKey: ["public-faqs"],
    queryFn: async () => (await apiFetch<FaqRow[]>("/api/v1/cms/public/faqs")).data,
  });

  const faqs = faqsQ.data || [];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      {faqs.length > 0 && <JsonLd data={buildFaqJsonLd(faqs)} />}
      <PublicHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-12 sm:px-6 space-y-8">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-teal-700 dark:text-teal-400">
            <HelpCircle className="h-4 w-4" />
            پرسش‌های متداول
          </div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">پاسخ به سؤالات پرتکرار کاربران و آژانس‌ها</h1>
        </div>

        {faqsQ.isLoading ? (
          <LoadingState message="در حال دریافت پرسش‌های متداول..." />
        ) : faqsQ.error ? (
          <ErrorState
            message={faqsQ.error instanceof Error ? faqsQ.error.message : "خطا در بارگذاری سؤالات"}
            onRetry={() => faqsQ.refetch()}
          />
        ) : (
          <div className="space-y-3">
            {faqs.map((faq) => {
              const open = openId === faq.id;
              return (
                <div
                  key={faq.id}
                  className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => setOpenId(open ? null : faq.id)}
                    className="flex w-full items-center justify-between gap-4 p-5 text-right"
                  >
                    <div>
                      <div className="text-[11px] font-semibold text-teal-700 dark:text-teal-400">{faq.category}</div>
                      <div className="mt-1 text-sm font-bold text-slate-900 dark:text-slate-100">{faq.question}</div>
                    </div>
                    <ChevronDown
                      className={`h-5 w-5 shrink-0 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
                    />
                  </button>
                  {open && (
                    <div className="border-t border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/30 p-5 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                      {faq.answer}
                    </div>
                  )}
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
