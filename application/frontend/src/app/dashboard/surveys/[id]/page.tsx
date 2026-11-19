// Path: frontend/src/app/dashboard/surveys/[id]/page.tsx

"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Copy, Download, ExternalLink, TrendingUp } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { useToast } from "@/components/ui/ToastProvider";
import { formatNumberFa } from "@/lib/formatters";

interface QuestionAnalytics {
  question_id: string;
  question_text: string;
  question_type: string;
  response_count: number;
  average: number | null;
  nps: number | null;
  distribution: Record<string, number>;
  sample_texts: string[];
}

interface SurveyAnalyticsData {
  survey_id: string;
  title: string;
  slug: string;
  total_responses: number;
  nps_score: number | null;
  questions: QuestionAnalytics[];
}

export default function SurveyAnalyticsDetailPage() {
  const params = useParams();
  const surveyId = String(params?.id || "");
  const { accessToken, activeAgencyId } = useAuth();
  const toast = useToast();

  const analyticsQ = useQuery({
    queryKey: ["survey-analytics", surveyId, activeAgencyId],
    enabled: !!accessToken && !!surveyId,
    queryFn: async () =>
      (
        await apiFetch<SurveyAnalyticsData>(`/api/v1/surveys/${surveyId}/analytics`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const exportCsv = () => {
    const d = analyticsQ.data;
    if (!d) return;
    const rows = [["سؤال", "نوع", "تعداد پاسخ", "میانگین", "NPS", "توزیع"]];
    d.questions.forEach((q) => {
      rows.push([
        q.question_text,
        q.question_type,
        String(q.response_count),
        q.average !== null ? String(q.average) : "-",
        q.nps !== null ? String(q.nps) : "-",
        JSON.stringify(q.distribution),
      ]);
    });
    const csv = "\uFEFF" + rows.map((r) => r.map((v) => `"${v.replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `survey-${d.slug}-analytics.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (analyticsQ.isLoading) return <LoadingState message="در حال محاسبه آمار و تحلیل نظرسنجی..." />;
  if (analyticsQ.error) {
    return (
      <ErrorState
        message={analyticsQ.error instanceof Error ? analyticsQ.error.message : "خطا در بارگذاری تحلیل نظرسنجی"}
        onRetry={() => analyticsQ.refetch()}
      />
    );
  }

  const data = analyticsQ.data;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`تحلیل نتایج: ${data.title}`}
        subtitle={`شناسه عمومی فرم: /surveys/${data.slug}`}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "نظرسنجی‌ها", href: "/dashboard/surveys" },
          { label: data.title },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            <Link
              href="/dashboard/surveys"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-semibold text-slate-700 dark:text-slate-200"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت
            </Link>
            <button
              type="button"
              onClick={async () => {
                await navigator.clipboard.writeText(`${window.location.origin}/surveys/${data.slug}`).catch(() => {});
                toast.success("لینک فرم عمومی کپی شد.");
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-semibold text-slate-800 dark:text-slate-200"
            >
              <Copy className="h-3.5 w-3.5" />
              کپی لینک فرم
            </button>
            <Link
              href={`/surveys/${data.slug}`}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-teal-700 text-teal-700 dark:text-teal-400 px-3 text-xs font-semibold"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              مشاهده فرم پاسخ‌دهی
            </Link>
            <button
              type="button"
              onClick={exportCsv}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Download className="h-3.5 w-3.5" />
              خروجی CSV
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard label="کل پاسخ‌های دریافتی" value={formatNumberFa(data.total_responses)} />
        <KpiCard
          label="شاخص خالص مروجان (NPS)"
          value={data.nps_score !== null ? `${formatNumberFa(data.nps_score)}٪` : "—"}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <KpiCard label="تعداد سؤالات" value={formatNumberFa(data.questions.length)} />
      </div>

      <div className="space-y-4">
        {data.questions.map((q, idx) => {
          const distEntries = Object.entries(q.distribution || {});
          const maxCount = Math.max(1, ...distEntries.map(([, c]) => c));

          return (
            <div key={q.question_id} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <span className="font-mono text-xs text-teal-700 dark:text-teal-400 font-semibold">
                    سؤال {formatNumberFa(idx + 1)} • {q.question_type}
                  </span>
                  <h3 className="mt-1 text-sm font-bold text-slate-900 dark:text-slate-100">{q.question_text}</h3>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-slate-500 dark:text-slate-400">پاسخ: {formatNumberFa(q.response_count)}</span>
                  {q.average !== null && (
                    <span className="rounded-md bg-teal-50 dark:bg-teal-950/40 px-2.5 py-1 font-mono font-bold text-teal-800 dark:text-teal-300">
                      میانگین: {formatNumberFa(q.average)}
                    </span>
                  )}
                  {q.nps !== null && (
                    <span className="rounded-md bg-indigo-50 dark:bg-indigo-950/40 px-2.5 py-1 font-mono font-bold text-indigo-800 dark:text-indigo-300">
                      NPS: {formatNumberFa(q.nps)}
                    </span>
                  )}
                </div>
              </div>

              {distEntries.length > 0 && (
                <div className="space-y-2">
                  {distEntries.map(([label, count]) => {
                    const pct = Math.round((count / maxCount) * 100);
                    return (
                      <div key={label} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-slate-700 dark:text-slate-300">{label}</span>
                          <span className="font-mono text-slate-500 dark:text-slate-400">{formatNumberFa(count)} رأی</span>
                        </div>
                        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div
                            className="h-full rounded-full bg-teal-600 transition-all"
                            style={{ width: `${Math.max(count > 0 ? 6 : 0, pct)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {q.sample_texts.length > 0 && (
                <div className="space-y-1.5 border-t border-slate-100 dark:border-slate-800 pt-3">
                  <div className="text-xs font-semibold text-slate-600 dark:text-slate-400">نمونه پاسخ‌های متنی:</div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {q.sample_texts.map((txt, tIdx) => (
                      <div
                        key={tIdx}
                        className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-2.5 text-xs text-slate-700 dark:text-slate-300"
                      >
                        «{txt}»
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
