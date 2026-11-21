"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileText, ShieldCheck } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { usePublicConfig } from "@/lib/public-config-context";
import { formatNumberFa } from "@/lib/formatters";
import type { LegalDocumentItem } from "@/lib/types";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

interface LegalDocumentViewProps {
  slug?: string;
  fallbackTitle?: string;
}

const DOC_TYPE_LABELS: Record<string, string> = {
  LEGAL: "مقررات و حقوقی",
  RULES: "قوانین پلتفرم",
  PRIVACY: "حریم خصوصی",
  TERMS: "شرایط استفاده",
  ABOUT: "معرفی پلتفرم",
  POLICY: "سیاست اجرایی",
};

export function LegalDocumentView({ slug: propSlug, fallbackTitle }: LegalDocumentViewProps) {
  const params = useParams<{ slug?: string }>();
  const slug = propSlug || params?.slug || "platform-rules";
  const { accessToken } = useAuth();
  const { legalDocuments } = usePublicConfig();
  const qc = useQueryClient();
  const [acceptMsg, setAcceptMsg] = useState<string | null>(null);
  const [acceptErr, setAcceptErr] = useState<string | null>(null);

  const docQ = useQuery({
    queryKey: ["public-legal-doc", slug, !!accessToken],
    queryFn: async () =>
      (
        await apiFetch<LegalDocumentItem>(`/api/v1/legal/${encodeURIComponent(slug)}`, {
          token: accessToken,
        })
      ).data,
  });

  const acceptMut = useMutation({
    mutationFn: async () =>
      apiFetch<{ id: string; slug: string; version_number: number; accepted_at: string }>(
        `/api/v1/legal/${encodeURIComponent(slug)}/accept`,
        { method: "POST", token: accessToken }
      ),
    onSuccess: (res) => {
      setAcceptErr(null);
      setAcceptMsg(`نسخه ${formatNumberFa(res.data.version_number)} این سند با موفقیت در سوابق شما ثبت شد.`);
      qc.invalidateQueries({ queryKey: ["public-legal-doc", slug] });
    },
    onError: (e: Error) => setAcceptErr(e.message),
  });

  const doc = docQ.data;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Sidebar list of published legal documents */}
          <aside className="lg:col-span-4 space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
                <FileText className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  فهرست اسناد حقوقی و مقررات
                </h2>
              </div>
              <nav className="space-y-1.5">
                {legalDocuments.length === 0 ? (
                  <p className="text-xs text-slate-500 dark:text-slate-400">در حال بارگذاری فهرست...</p>
                ) : (
                  legalDocuments.map((item) => {
                    const active = item.slug === slug;
                    return (
                      <Link
                        key={item.slug}
                        href={`/legal/${item.slug}`}
                        className={`flex items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-xs transition-colors ${
                          active
                            ? "border-teal-700 bg-teal-50/70 font-bold text-teal-900 dark:border-teal-500 dark:bg-teal-950/40 dark:text-teal-200"
                            : "border-transparent text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/60"
                        }`}
                      >
                        <span className="truncate">{item.title_fa}</span>
                        <span className="shrink-0 font-mono text-[10px] text-slate-400 tabular-nums">
                          v{item.version_number}
                        </span>
                      </Link>
                    );
                  })
                )}
              </nav>
            </div>
          </aside>

          {/* Main Document Body */}
          <section className="lg:col-span-8 space-y-5">
            {docQ.isLoading ? (
              <LoadingState />
            ) : docQ.error instanceof Error ? (
              <ErrorState message={docQ.error.message} onRetry={() => docQ.refetch()} />
            ) : doc ? (
              <article className="rounded-xl border border-slate-200 bg-white p-6 sm:p-8 dark:border-slate-800 dark:bg-slate-900 space-y-6">
                <header className="space-y-3 border-b border-slate-100 pb-5 dark:border-slate-800">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded border border-teal-200 bg-teal-50 px-2.5 py-0.5 text-[11px] font-semibold text-teal-800 dark:border-teal-900 dark:bg-teal-950/50 dark:text-teal-300">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      {DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}
                    </span>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                      <span className="font-mono tabular-nums">نسخه {formatNumberFa(doc.version_number)}</span>
                      {doc.effective_at && (
                        <span>
                          تاریخ اجرا: <DateDisplay value={doc.effective_at} />
                        </span>
                      )}
                      {!doc.effective_at && doc.published_at && (
                        <span>
                          تاریخ انتشار: <DateDisplay value={doc.published_at} />
                        </span>
                      )}
                    </div>
                  </div>
                  <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {doc.title_fa || fallbackTitle}
                  </h1>
                  {doc.summary && (
                    <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                      {doc.summary}
                    </p>
                  )}
                </header>

                {acceptMsg && <SuccessBanner message={acceptMsg} />}
                {acceptErr && <ErrorState message={acceptErr} />}

                <div
                  className="prose prose-sm max-w-none leading-7 text-slate-700 dark:prose-invert dark:text-slate-300 [&_h2]:mt-6 [&_h2]:mb-2 [&_h2]:text-base [&_h2]:font-bold [&_h2]:text-slate-900 dark:[&_h2]:text-slate-100 [&_h3]:mt-4 [&_h3]:mb-1.5 [&_h3]:text-sm [&_h3]:font-bold [&_p]:mb-3 [&_ul]:list-disc [&_ul]:pr-5 [&_ol]:list-decimal [&_ol]:pr-5 [&_li]:mb-1.5"
                  dangerouslySetInnerHTML={{ __html: doc.body_html }}
                />

                {/* Acceptance footer */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5 dark:border-slate-800">
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {doc.accepted_by_current_user ? (
                      <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-700 dark:text-emerald-400">
                        <CheckCircle2 className="h-4 w-4" />
                        شما آخرین نسخه این سند را تأیید کرده‌اید.
                      </span>
                    ) : doc.requires_acceptance ? (
                      <span>پذیرش این سند برای استفاده کامل از خدمات الزامی است.</span>
                    ) : (
                      <span>متن رسمی از مرکز مدیریت اسناد حقوقی بنیان ملک</span>
                    )}
                  </div>

                  {accessToken ? (
                    !doc.accepted_by_current_user && (
                      <button
                        type="button"
                        disabled={acceptMut.isPending}
                        onClick={() => acceptMut.mutate()}
                        className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50 dark:bg-teal-600"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        {acceptMut.isPending ? "در حال ثبت..." : "تأیید و پذیرش نسخه فعلی"}
                      </button>
                    )
                  ) : (
                    doc.requires_acceptance && (
                      <Link
                        href="/login"
                        className="inline-flex h-9 shrink-0 items-center whitespace-nowrap rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                      >
                        ورود برای ثبت پذیرش سند
                      </Link>
                    )
                  )}
                </div>
              </article>
            ) : null}
          </section>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
