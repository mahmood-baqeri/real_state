"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BarChart3,
  Check,
  Copy,
  Download,
  Edit3,
  ExternalLink,
  ListChecks,
  Plus,
  Save,
  Settings2,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { useToast } from "@/components/ui/ToastProvider";
import { formatNumberFa } from "@/lib/formatters";

interface SurveyQuestionDetail {
  id: string;
  sort_order: number;
  question_text: string;
  question_type: string;
  options: string[];
  is_required: boolean;
}

interface SurveyDetail {
  id: string;
  agency_id: string | null;
  agency_name: string;
  title: string;
  slug: string;
  description: string;
  target_audience: string;
  crm_trigger_event: string;
  is_active: boolean;
  allow_anonymous: boolean;
  responses_count: number;
  questions: SurveyQuestionDetail[];
  created_at: string;
}

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

interface SurveyResponseAnswer {
  question_id: string;
  question_text: string;
  question_type: string;
  answer_text: string;
  answer_number: number | null;
  selected_options: string[];
}

interface SurveyResponseRecord {
  id: string;
  respondent_name: string;
  respondent_identifier: string;
  submitted_at: string;
  answers: SurveyResponseAnswer[];
}

const QUESTION_TYPES = [
  { value: "RATING", label: "امتیاز عددی (۱ تا ۵)" },
  { value: "STARS", label: "ستاره‌ای (۱ تا ۵ ستاره)" },
  { value: "NPS", label: "شاخص خالص مروجان (NPS ۰ تا ۱۰)" },
  { value: "SCALE", label: "مقیاس رضایت (۱ تا ۱۰)" },
  { value: "SINGLE_SELECT", label: "تک‌انتخابی (رادیویی)" },
  { value: "MULTI_SELECT", label: "چندانتخابی (چک‌باکس)" },
  { value: "YES_NO", label: "بله / خیر" },
  { value: "SHORT_TEXT", label: "پاسخ متنی کوتاه" },
  { value: "LONG_TEXT", label: "پاسخ متنی تشریحی" },
  { value: "TEXT", label: "پاسخ متنی آزاد" },
];

const QUESTION_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  QUESTION_TYPES.map((q) => [q.value, q.label])
);

const AUDIENCE_LABELS: Record<string, string> = {
  CUSTOMERS: "مشتریان و خریداران",
  PUBLIC: "عمومی پورتال",
  AGENCY_STAFF: "پرسنل و مشاوران آژانس",
  ALL: "همه کاربران",
};

const TRIGGER_LABELS: Record<string, string> = {
  NONE: "ارسال دستی / لینک مستقیم",
  AFTER_VIEWING: "پس از انجام بازدید ملک",
  AFTER_CONTRACT: "پس از امضای قرارداد",
  AFTER_TICKET_CLOSE: "پس از بسته‌شدن تیکت",
};

export default function SurveyAnalyticsDetailPage() {
  const params = useParams();
  const surveyId = String(params?.id || "");
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();

  const canManage = ["SUPER_ADMIN", "AGENCY_MANAGER", "BRANCH_MANAGER"].includes(effectiveRole);
  const [tab, setTab] = useState<"analytics" | "responses" | "builder">("analytics");

  const surveyQ = useQuery({
    queryKey: ["survey-detail", surveyId, activeAgencyId],
    enabled: !!accessToken && !!surveyId,
    queryFn: async () =>
      (
        await apiFetch<SurveyDetail>(`/api/v1/surveys/${surveyId}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

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

  const responsesQ = useQuery({
    queryKey: ["survey-responses", surveyId, activeAgencyId],
    enabled: !!accessToken && !!surveyId,
    queryFn: async () =>
      (
        await apiFetch<SurveyResponseRecord[]>(`/api/v1/surveys/${surveyId}/responses`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const [metaForm, setMetaForm] = useState({
    title: "",
    description: "",
    target_audience: "CUSTOMERS",
    crm_trigger_event: "NONE",
    is_active: true,
    allow_anonymous: true,
  });

  useEffect(() => {
    if (surveyQ.data) {
      setMetaForm({
        title: surveyQ.data.title,
        description: surveyQ.data.description || "",
        target_audience: surveyQ.data.target_audience,
        crm_trigger_event: surveyQ.data.crm_trigger_event,
        is_active: surveyQ.data.is_active,
        allow_anonymous: surveyQ.data.allow_anonymous,
      });
    }
  }, [surveyQ.data]);

  const [newQ, setNewQ] = useState({
    question_text: "",
    question_type: "RATING",
    optionsText: "",
    is_required: true,
  });

  const [editingQId, setEditingQId] = useState<string | null>(null);
  const [editQForm, setEditQForm] = useState({
    question_text: "",
    question_type: "RATING",
    optionsText: "",
    is_required: true,
  });

  const targetAgencyId = activeAgencyId || surveyQ.data?.agency_id || undefined;

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["survey-detail", surveyId] });
    qc.invalidateQueries({ queryKey: ["survey-analytics", surveyId] });
    qc.invalidateQueries({ queryKey: ["survey-responses", surveyId] });
    qc.invalidateQueries({ queryKey: ["surveys"] });
  };

  const updateMetaMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/surveys/${surveyId}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: targetAgencyId,
        body: JSON.stringify(metaForm),
      }),
    onSuccess: () => {
      toast.success("تنظیمات نظرسنجی ذخیره شد.");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const addQuestionMut = useMutation({
    mutationFn: async () => {
      const options = ["SINGLE_SELECT", "MULTI_SELECT"].includes(newQ.question_type)
        ? newQ.optionsText
            .split(/[\n,،]+/)
            .map((s) => s.trim())
            .filter(Boolean)
        : [];
      return apiFetch(`/api/v1/surveys/${surveyId}/questions`, {
        method: "POST",
        token: accessToken,
        agencyId: targetAgencyId,
        body: JSON.stringify({
          sort_order: (surveyQ.data?.questions.length || 0) + 1,
          question_text: newQ.question_text,
          question_type: newQ.question_type,
          options,
          is_required: newQ.is_required,
        }),
      });
    },
    onSuccess: () => {
      setNewQ({ question_text: "", question_type: "RATING", optionsText: "", is_required: true });
      toast.success("سؤال جدید به نظرسنجی اضافه شد.");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateQuestionMut = useMutation({
    mutationFn: async (qid: string) => {
      const options = ["SINGLE_SELECT", "MULTI_SELECT"].includes(editQForm.question_type)
        ? editQForm.optionsText
            .split(/[\n,،]+/)
            .map((s) => s.trim())
            .filter(Boolean)
        : [];
      return apiFetch(`/api/v1/surveys/${surveyId}/questions/${qid}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: targetAgencyId,
        body: JSON.stringify({
          question_text: editQForm.question_text,
          question_type: editQForm.question_type,
          options,
          is_required: editQForm.is_required,
        }),
      });
    },
    onSuccess: () => {
      setEditingQId(null);
      toast.success("سؤال با موفقیت ویرایش شد.");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteQuestionMut = useMutation({
    mutationFn: async (qid: string) =>
      apiFetch(`/api/v1/surveys/${surveyId}/questions/${qid}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: targetAgencyId,
      }),
    onSuccess: () => {
      toast.success("سؤال حذف شد.");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const reorderMut = useMutation({
    mutationFn: async (questionIds: string[]) =>
      apiFetch(`/api/v1/surveys/${surveyId}/questions/reorder`, {
        method: "POST",
        token: accessToken,
        agencyId: targetAgencyId,
        body: JSON.stringify({ question_ids: questionIds }),
      }),
    onSuccess: () => {
      toast.success("ترتیب سؤالات به‌روزرسانی شد.");
      invalidateAll();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const moveQuestion = (index: number, direction: -1 | 1) => {
    const qs = [...(surveyQ.data?.questions || [])].sort((a, b) => a.sort_order - b.sort_order);
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= qs.length) return;
    const [moved] = qs.splice(index, 1);
    qs.splice(targetIndex, 0, moved);
    reorderMut.mutate(qs.map((q) => q.id));
  };

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

  if (analyticsQ.isLoading || surveyQ.isLoading) {
    return <LoadingState message="در حال محاسبه آمار و بارگذاری پرسشنامه..." />;
  }
  if (analyticsQ.error || surveyQ.error) {
    const err = analyticsQ.error || surveyQ.error;
    return (
      <ErrorState
        message={err instanceof Error ? err.message : "خطا در بارگذاری نظرسنجی"}
        onRetry={() => {
          surveyQ.refetch();
          analyticsQ.refetch();
        }}
      />
    );
  }

  const data = analyticsQ.data;
  const survey = surveyQ.data;
  if (!data || !survey) return null;

  const sortedQuestions = [...survey.questions].sort((a, b) => a.sort_order - b.sort_order);
  const responses = responsesQ.data || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={`مدیریت و تحلیل نظرسنجی: ${survey.title}`}
        subtitle={`شناسه عمومی فرم: /surveys/${survey.slug} · ${survey.agency_name}`}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "نظرسنجی‌ها", href: "/dashboard/surveys" },
          { label: survey.title },
        ]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusText status={survey.is_active ? "ACTIVE" : "INACTIVE"} />
            <Link
              href="/dashboard/surveys"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت
            </Link>
            <button
              type="button"
              onClick={async () => {
                await navigator.clipboard.writeText(`${window.location.origin}/surveys/${survey.slug}`).catch(() => {});
                toast.success("لینک فرم عمومی کپی شد.");
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap"
            >
              <Copy className="h-3.5 w-3.5" />
              کپی لینک
            </button>
            <Link
              href={`/surveys/${survey.slug}`}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-teal-700 text-teal-700 dark:text-teal-400 px-3 text-xs font-semibold whitespace-nowrap"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              فرم پاسخ‌دهی
            </Link>
            <button
              type="button"
              onClick={exportCsv}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
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
        <KpiCard label="تعداد سؤالات" value={formatNumberFa(sortedQuestions.length)} />
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        <button
          type="button"
          onClick={() => setTab("analytics")}
          className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-4 text-xs font-semibold whitespace-nowrap ${
            tab === "analytics"
              ? "border-teal-700 bg-teal-700 text-white"
              : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
          }`}
        >
          <BarChart3 className="h-3.5 w-3.5" />
          تحلیل و آمار
        </button>
        <button
          type="button"
          onClick={() => setTab("responses")}
          className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-4 text-xs font-semibold whitespace-nowrap ${
            tab === "responses"
              ? "border-teal-700 bg-teal-700 text-white"
              : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
          }`}
        >
          <ListChecks className="h-3.5 w-3.5" />
          پاسخ‌های ثبت‌شده ({formatNumberFa(responses.length)})
        </button>
        {canManage && (
          <button
            type="button"
            onClick={() => setTab("builder")}
            className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-4 text-xs font-semibold whitespace-nowrap ${
              tab === "builder"
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
            }`}
          >
            <Settings2 className="h-3.5 w-3.5" />
            مدیریت تنظیمات و سؤالات ({formatNumberFa(sortedQuestions.length)})
          </button>
        )}
      </div>

      {/* Tab 1: Analytics */}
      {tab === "analytics" && (
        <div className="space-y-4">
          {data.questions.map((q, idx) => {
            const distEntries = Object.entries(q.distribution || {});
            const maxCount = Math.max(1, ...distEntries.map(([, c]) => c));

            return (
              <div
                key={q.question_id}
                className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <span className="font-mono text-xs text-teal-700 dark:text-teal-400 font-semibold">
                      سؤال {formatNumberFa(idx + 1)} · {QUESTION_TYPE_LABELS[q.question_type] || q.question_type}
                    </span>
                    <h3 className="mt-1 text-sm font-bold text-slate-900 dark:text-slate-100">{q.question_text}</h3>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-slate-500 dark:text-slate-400">پاسخ: {formatNumberFa(q.response_count)}</span>
                    {q.average !== null && (
                      <span className="rounded-md bg-teal-50 dark:bg-teal-950/40 px-2.5 py-1 font-mono font-bold text-teal-800 dark:text-teal-300 tabular-nums">
                        میانگین: {formatNumberFa(q.average)}
                      </span>
                    )}
                    {q.nps !== null && (
                      <span className="rounded-md bg-indigo-50 dark:bg-indigo-950/40 px-2.5 py-1 font-mono font-bold text-indigo-800 dark:text-indigo-300 tabular-nums">
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
                            <span className="font-medium text-slate-700 dark:text-slate-300">
                              {label === "YES" ? "بله" : label === "NO" ? "خیر" : label}
                            </span>
                            <span className="font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                              {formatNumberFa(count)} رأی
                            </span>
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
      )}

      {/* Tab 2: Individual Responses */}
      {tab === "responses" && (
        <div className="space-y-4">
          {responsesQ.isLoading ? (
            <LoadingState message="در حال بارگذاری فهرست پاسخ‌ها..." />
          ) : responses.length === 0 ? (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 text-center text-xs text-slate-500 dark:text-slate-400">
              هنوز هیچ پاسخی برای این نظرسنجی ثبت نشده است.
            </div>
          ) : (
            responses.map((resp, rIdx) => (
              <div
                key={resp.id}
                className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-mono text-slate-400">#{formatNumberFa(rIdx + 1)}</span>
                    <span className="font-bold text-slate-900 dark:text-slate-100">
                      {resp.respondent_name || "کاربر مهمان"}
                    </span>
                    <span className="font-mono text-[11px] text-slate-400">({resp.respondent_identifier})</span>
                  </div>
                  <DateDisplay value={resp.submitted_at} withTime className="text-xs text-slate-500 dark:text-slate-400" />
                </div>
                <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
                  {resp.answers.map((ans) => {
                    let displayAnswer = "—";
                    if (ans.answer_number !== null && ans.answer_number !== undefined) {
                      displayAnswer = formatNumberFa(ans.answer_number);
                    } else if (ans.selected_options && ans.selected_options.length > 0) {
                      displayAnswer = ans.selected_options.join("، ");
                    } else if (ans.answer_text) {
                      displayAnswer =
                        ans.answer_text === "YES"
                          ? "بله"
                          : ans.answer_text === "NO"
                          ? "خیر"
                          : ans.answer_text;
                    }
                    return (
                      <div
                        key={ans.question_id}
                        className="rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3 text-xs space-y-1"
                      >
                        <div className="text-slate-500 dark:text-slate-400">{ans.question_text}</div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{displayAnswer}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 3: Survey Settings & Question Builder */}
      {tab === "builder" && canManage && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Metadata Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              updateMetaMut.mutate();
            }}
            className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4 lg:col-span-4 h-fit"
          >
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-3">
              تنظیمات کلی نظرسنجی
            </h2>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">عنوان</label>
              <input
                required
                value={metaForm.title}
                onChange={(e) => setMetaForm({ ...metaForm, title: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">توضیحات</label>
              <textarea
                rows={3}
                value={metaForm.description}
                onChange={(e) => setMetaForm({ ...metaForm, description: e.target.value })}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-xs"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">جامعه هدف</label>
              <select
                value={metaForm.target_audience}
                onChange={(e) => setMetaForm({ ...metaForm, target_audience: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs"
              >
                {Object.entries(AUDIENCE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">رویداد محرک CRM</label>
              <select
                value={metaForm.crm_trigger_event}
                onChange={(e) => setMetaForm({ ...metaForm, crm_trigger_event: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs"
              >
                {Object.entries(TRIGGER_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={metaForm.is_active}
                  onChange={(e) => setMetaForm({ ...metaForm, is_active: e.target.checked })}
                  className="accent-teal-700"
                />
                نظرسنجی فعال باشد (قابل پاسخ‌دهی)
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={metaForm.allow_anonymous}
                  onChange={(e) => setMetaForm({ ...metaForm, allow_anonymous: e.target.checked })}
                  className="accent-teal-700"
                />
                ثبت پاسخ بدون ورود (ناشناس) مجاز باشد
              </label>
            </div>
            <button
              type="submit"
              disabled={updateMetaMut.isPending}
              className="inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              {updateMetaMut.isPending ? "در حال ذخیره..." : "ذخیره تنظیمات نظرسنجی"}
            </button>
          </form>

          {/* Question List + Add Form */}
          <div className="space-y-4 lg:col-span-8">
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                سؤالات پرسشنامه (مرتب‌سازی و ویرایش)
              </h2>

              <div className="space-y-3">
                {sortedQuestions.map((q, idx) => {
                  const isEditing = editingQId === q.id;
                  return (
                    <div
                      key={q.id}
                      className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 p-3.5 space-y-2"
                    >
                      {!isEditing ? (
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 text-[11px] font-semibold text-teal-700 dark:text-teal-400">
                              <span className="font-mono">#{formatNumberFa(idx + 1)}</span>
                              <span>{QUESTION_TYPE_LABELS[q.question_type] || q.question_type}</span>
                              {q.is_required && <span className="text-rose-600">(الزامی)</span>}
                            </div>
                            <div className="text-xs font-bold text-slate-900 dark:text-slate-100">{q.question_text}</div>
                            {q.options && q.options.length > 0 && (
                              <div className="text-[11px] text-slate-500 dark:text-slate-400">
                                گزینه‌ها: {q.options.join(" | ")}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              disabled={idx === 0 || reorderMut.isPending}
                              onClick={() => moveQuestion(idx, -1)}
                              title="انتقال به بالا"
                              className="inline-flex h-7 w-7 items-center justify-center rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-600 disabled:opacity-40"
                            >
                              <ArrowUp className="h-3.5 w-3.5" />
                            </button>
                            <button
                              type="button"
                              disabled={idx === sortedQuestions.length - 1 || reorderMut.isPending}
                              onClick={() => moveQuestion(idx, 1)}
                              title="انتقال به پایین"
                              className="inline-flex h-7 w-7 items-center justify-center rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-600 disabled:opacity-40"
                            >
                              <ArrowDown className="h-3.5 w-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setEditingQId(q.id);
                                setEditQForm({
                                  question_text: q.question_text,
                                  question_type: q.question_type,
                                  optionsText: (q.options || []).join("، "),
                                  is_required: q.is_required,
                                });
                              }}
                              title="ویرایش سؤال"
                              className="inline-flex h-7 w-7 items-center justify-center rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-teal-700 dark:text-teal-400"
                            >
                              <Edit3 className="h-3.5 w-3.5" />
                            </button>
                            <button
                              type="button"
                              disabled={sortedQuestions.length <= 1 || deleteQuestionMut.isPending}
                              onClick={() => deleteQuestionMut.mutate(q.id)}
                              title={
                                sortedQuestions.length <= 1
                                  ? "نظرسنجی باید حداقل یک سؤال داشته باشد"
                                  : "حذف سؤال"
                              }
                              className="inline-flex h-7 w-7 items-center justify-center rounded border border-rose-200 dark:border-rose-900 bg-white dark:bg-slate-900 text-rose-600 disabled:opacity-40"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      ) : (
                        <form
                          onSubmit={(e) => {
                            e.preventDefault();
                            updateQuestionMut.mutate(q.id);
                          }}
                          className="space-y-2.5"
                        >
                          <input
                            required
                            value={editQForm.question_text}
                            onChange={(e) => setEditQForm({ ...editQForm, question_text: e.target.value })}
                            className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs"
                          />
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            <select
                              value={editQForm.question_type}
                              onChange={(e) => setEditQForm({ ...editQForm, question_type: e.target.value })}
                              className="h-9 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs"
                            >
                              {QUESTION_TYPES.map((t) => (
                                <option key={t.value} value={t.value}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                            <label className="flex items-center gap-2 text-xs">
                              <input
                                type="checkbox"
                                checked={editQForm.is_required}
                                onChange={(e) => setEditQForm({ ...editQForm, is_required: e.target.checked })}
                                className="accent-teal-700"
                              />
                              پاسخ الزامی
                            </label>
                          </div>
                          {["SINGLE_SELECT", "MULTI_SELECT"].includes(editQForm.question_type) && (
                            <input
                              required
                              placeholder="گزینه‌ها (جداشده با ویرگول)"
                              value={editQForm.optionsText}
                              onChange={(e) => setEditQForm({ ...editQForm, optionsText: e.target.value })}
                              className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs"
                            />
                          )}
                          <div className="flex gap-2">
                            <button
                              type="submit"
                              disabled={updateQuestionMut.isPending}
                              className="inline-flex h-8 items-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white"
                            >
                              <Check className="h-3.5 w-3.5" />
                              ذخیره سؤال
                            </button>
                            <button
                              type="button"
                              onClick={() => setEditingQId(null)}
                              className="h-8 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-xs"
                            >
                              انصراف
                            </button>
                          </div>
                        </form>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Add Question Card */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                addQuestionMut.mutate();
              }}
              className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3"
            >
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">افزودن سؤال جدید به فرم</h3>
              <input
                required
                placeholder="متن سؤال جدید..."
                value={newQ.question_text}
                onChange={(e) => setNewQ({ ...newQ, question_text: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs"
              />
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <select
                  value={newQ.question_type}
                  onChange={(e) => setNewQ({ ...newQ, question_type: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs"
                >
                  {QUESTION_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={newQ.is_required}
                    onChange={(e) => setNewQ({ ...newQ, is_required: e.target.checked })}
                    className="accent-teal-700"
                  />
                  پاسخ الزامی باشد
                </label>
              </div>
              {["SINGLE_SELECT", "MULTI_SELECT"].includes(newQ.question_type) && (
                <input
                  required
                  placeholder="گزینه‌ها را با ویرگول (،) جدا کنید؛ مثلاً: عالی، خوب، ضعیف"
                  value={newQ.optionsText}
                  onChange={(e) => setNewQ({ ...newQ, optionsText: e.target.value })}
                  className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs"
                />
              )}
              <button
                type="submit"
                disabled={addQuestionMut.isPending}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" />
                {addQuestionMut.isPending ? "در حال افزودن..." : "افزودن سؤال"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
