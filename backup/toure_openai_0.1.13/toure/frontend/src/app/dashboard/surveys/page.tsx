"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  ClipboardCheck,
  Copy,
  Edit3,
  ExternalLink,
  Plus,
  Power,
  Trash2,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { DataTable } from "@/components/ui/DataTable";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { StatusText } from "@/components/ui/StatusText";
import { useToast } from "@/components/ui/ToastProvider";
import { formatNumberFa } from "@/lib/formatters";

interface SurveyQuestionItem {
  id: string;
  sort_order: number;
  question_text: string;
  question_type: string;
  options: string[];
  is_required: boolean;
}

interface SurveyItem {
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
  questions: SurveyQuestionItem[];
  created_at: string;
}

interface SurveyCompareItem {
  survey_id: string;
  title: string;
  slug: string;
  responses_count: number;
  overall_avg: number | null;
}

interface DraftQuestion {
  question_text: string;
  question_type: string;
  optionsText: string;
  is_required: boolean;
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

export default function SurveysDashboardPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<SurveyItem | null>(null);

  const canManage = ["SUPER_ADMIN", "AGENCY_MANAGER", "BRANCH_MANAGER"].includes(effectiveRole);

  const [form, setForm] = useState({
    title: "",
    slug: "",
    description: "",
    target_audience: "CUSTOMERS",
    crm_trigger_event: "NONE",
    is_active: true,
    allow_anonymous: true,
  });

  const [editForm, setEditForm] = useState({
    title: "",
    description: "",
    target_audience: "CUSTOMERS",
    crm_trigger_event: "NONE",
    is_active: true,
    allow_anonymous: true,
  });

  const [questions, setQuestions] = useState<DraftQuestion[]>([
    {
      question_text: "رضایت کلی شما از کیفیت مشاوره و پیگیری چقدر بوده است؟",
      question_type: "STARS",
      optionsText: "",
      is_required: true,
    },
    {
      question_text: "چقدر احتمال دارد ما را به دیگران معرفی کنید؟ (NPS)",
      question_type: "NPS",
      optionsText: "",
      is_required: true,
    },
  ]);

  const surveysQ = useQuery({
    queryKey: ["surveys", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SurveyItem[]>("/api/v1/surveys", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const compareQ = useQuery({
    queryKey: ["surveys-compare", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SurveyCompareItem[]>("/api/v1/surveys/analytics/compare", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const createMut = useMutation({
    mutationFn: async () => {
      const payload = {
        ...form,
        questions: questions.map((q, idx) => ({
          sort_order: idx + 1,
          question_text: q.question_text,
          question_type: q.question_type,
          options: ["SINGLE_SELECT", "MULTI_SELECT"].includes(q.question_type)
            ? q.optionsText
                .split(/[\n,،]+/)
                .map((s) => s.trim())
                .filter(Boolean)
            : [],
          is_required: q.is_required,
        })),
      };
      return apiFetch<SurveyItem>("/api/v1/surveys", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      setCreateOpen(false);
      setForm({
        title: "",
        slug: "",
        description: "",
        target_audience: "CUSTOMERS",
        crm_trigger_event: "NONE",
        is_active: true,
        allow_anonymous: true,
      });
      toast.success("فرم نظرسنجی با موفقیت ایجاد شد.");
      qc.invalidateQueries({ queryKey: ["surveys"] });
      qc.invalidateQueries({ queryKey: ["surveys-compare"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: async ({
      id,
      agencyId,
      body,
    }: {
      id: string;
      agencyId?: string | null;
      body: Record<string, unknown>;
    }) =>
      apiFetch<SurveyItem>(`/api/v1/surveys/${id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId || agencyId || undefined,
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      setEditTarget(null);
      toast.success("تنظیمات نظرسنجی با موفقیت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["surveys"] });
      qc.invalidateQueries({ queryKey: ["surveys-compare"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const openEdit = (s: SurveyItem) => {
    setEditTarget(s);
    setEditForm({
      title: s.title,
      description: s.description || "",
      target_audience: s.target_audience,
      crm_trigger_event: s.crm_trigger_event,
      is_active: s.is_active,
      allow_anonymous: s.allow_anonymous,
    });
  };

  const copyPublicLink = async (slug: string) => {
    const url = `${window.location.origin}/surveys/${slug}`;
    try {
      await navigator.clipboard.writeText(url);
      toast.success("لینک عمومی نظرسنجی در کلیپ‌بورد کپی شد.");
    } catch {
      toast.info(`آدرس فرم: /surveys/${slug}`);
    }
  };

  const totalResponses = (surveysQ.data || []).reduce((sum, s) => sum + s.responses_count, 0);
  const activeCount = (surveysQ.data || []).filter((s) => s.is_active).length;
  const avgList = (compareQ.data || [])
    .filter((c) => c.overall_avg !== null)
    .map((c) => c.overall_avg as number);
  const overallAvg =
    avgList.length > 0 ? (avgList.reduce((a, b) => a + b, 0) / avgList.length).toFixed(2) : "—";

  return (
    <div className="space-y-6">
      <PageHeader
        title="فرم‌ساز نظرسنجی و سنجش رضایت (NPS)"
        subtitle="طراحی پرسشنامه‌های ۱۰گانه، مدیریت سؤالات، اتصال خودکار به رویدادهای CRM و پایش تحلیلی بازخورد مشتریان"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "نظرسنجی و NPS" }]}
        actions={
          canManage ? (
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
            >
              <Plus className="h-4 w-4" />
              ساخت نظرسنجی جدید
            </button>
          ) : null
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          label="نظرسنجی‌های فعال"
          value={formatNumberFa(activeCount)}
          icon={<ClipboardCheck className="h-4 w-4" />}
        />
        <KpiCard label="مجموع پاسخ‌های ثبت‌شده" value={formatNumberFa(totalResponses)} />
        <KpiCard
          label="میانگین امتیاز کل"
          value={overallAvg === "—" ? "—" : formatNumberFa(overallAvg)}
        />
      </div>

      {(compareQ.data || []).length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              مقایسه عملکرد نظرسنجی‌ها
            </h2>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {(compareQ.data || []).slice(0, 6).map((c) => (
              <Link
                key={c.survey_id}
                href={`/dashboard/surveys/${c.survey_id}`}
                className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3.5 transition-colors hover:border-teal-600"
              >
                <div className="truncate text-xs font-bold text-slate-900 dark:text-slate-100">{c.title}</div>
                <div className="mt-2 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
                  <span>پاسخ: {formatNumberFa(c.responses_count)}</span>
                  <span className="font-mono font-bold text-teal-700 dark:text-teal-400 tabular-nums">
                    میانگین: {c.overall_avg !== null ? formatNumberFa(c.overall_avg) : "—"}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <DataTable
        rows={surveysQ.data || []}
        rowKey={(s) => s.id}
        isLoading={surveysQ.isLoading}
        error={surveysQ.error instanceof Error ? surveysQ.error.message : null}
        onRetry={() => surveysQ.refetch()}
        searchPlaceholder="جستجو در عنوان یا اسلاگ نظرسنجی..."
        exportFileName="surveys"
        columns={[
          {
            key: "title",
            header: "عنوان نظرسنجی",
            render: (s) => (
              <div>
                <Link
                  href={`/dashboard/surveys/${s.id}`}
                  className="font-semibold text-slate-900 dark:text-slate-100 hover:underline"
                >
                  {s.title}
                </Link>
                <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                  /{s.slug} {!activeAgencyId && s.agency_name ? `· ${s.agency_name}` : ""}
                </div>
              </div>
            ),
          },
          { key: "audience", header: "مخاطب", render: (s) => AUDIENCE_LABELS[s.target_audience] || s.target_audience },
          {
            key: "trigger",
            header: "رویداد محرک CRM",
            render: (s) => TRIGGER_LABELS[s.crm_trigger_event] || s.crm_trigger_event,
          },
          {
            key: "status",
            header: "وضعیت",
            render: (s) => <StatusText status={s.is_active ? "ACTIVE" : "INACTIVE"} />,
          },
          { key: "qs", header: "سؤال", render: (s) => formatNumberFa(s.questions.length) },
          {
            key: "resp",
            header: "پاسخ‌ها",
            render: (s) => <span className="font-mono font-bold tabular-nums">{formatNumberFa(s.responses_count)}</span>,
          },
          { key: "dt", header: "تاریخ ایجاد", render: (s) => <DateDisplay value={s.created_at} /> },
          {
            key: "actions",
            header: "عملیات",
            render: (s) => (
              <div className="flex flex-wrap items-center gap-1.5">
                <Link
                  href={`/dashboard/surveys/${s.id}`}
                  className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  تحلیل و ویرایشگر
                </Link>
                {canManage && (
                  <>
                    <button
                      type="button"
                      onClick={() => openEdit(s)}
                      title="ویرایش مشخصات فرم"
                      className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      <Edit3 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      disabled={updateMut.isPending}
                      onClick={() =>
                        updateMut.mutate({
                          id: s.id,
                          agencyId: s.agency_id,
                          body: { is_active: !s.is_active },
                        })
                      }
                      title={s.is_active ? "غیرفعال‌سازی نظرسنجی" : "فعال‌سازی نظرسنجی"}
                      className={`inline-flex h-7 w-7 items-center justify-center rounded-md border ${
                        s.is_active
                          ? "border-amber-300 text-amber-700 hover:bg-amber-50 dark:border-amber-800 dark:text-amber-300"
                          : "border-emerald-300 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-800 dark:text-emerald-300"
                      }`}
                    >
                      <Power className="h-3.5 w-3.5" />
                    </button>
                  </>
                )}
                <button
                  type="button"
                  onClick={() => copyPublicLink(s.slug)}
                  title="کپی لینک عمومی فرم"
                  className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
                <Link
                  href={`/surveys/${s.slug}`}
                  title="مشاهده فرم عمومی"
                  className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-300 dark:border-slate-700 text-teal-700 dark:text-teal-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              </div>
            ),
          },
        ]}
      />

      {/* Create Survey Modal */}
      <ModalDrawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="طراحی فرم نظرسنجی جدید"
        widthClass="max-w-2xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">عنوان نظرسنجی</label>
              <input
                required
                placeholder="مثلاً: ارزیابی کیفیت بازدید حضوری"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">شناسه یکتا (Slug انگلیسی)</label>
              <input
                required
                dir="ltr"
                placeholder="e.g. post-viewing-feedback"
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <textarea
            rows={2}
            placeholder="توضیحات کوتاه بالای فرم نظرسنجی..."
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-xs text-slate-900 dark:text-slate-100"
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">جامعه هدف</label>
              <select
                value={form.target_audience}
                onChange={(e) => setForm({ ...form, target_audience: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
              >
                {Object.entries(AUDIENCE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">رویداد محرک خودکار CRM</label>
              <select
                value={form.crm_trigger_event}
                onChange={(e) => setForm({ ...form, crm_trigger_event: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
              >
                {Object.entries(TRIGGER_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 text-xs text-slate-700 dark:text-slate-300">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                className="accent-teal-700"
              />
              نظرسنجی فعال باشد
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.allow_anonymous}
                onChange={(e) => setForm({ ...form, allow_anonymous: e.target.checked })}
                className="accent-teal-700"
              />
              امکان ثبت پاسخ ناشناس
            </label>
          </div>

          <div className="space-y-3 border-t border-slate-200 dark:border-slate-800 pt-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">سؤالات پرسشنامه</h3>
              <button
                type="button"
                onClick={() =>
                  setQuestions((prev) => [
                    ...prev,
                    { question_text: "", question_type: "RATING", optionsText: "", is_required: true },
                  ])
                }
                className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 dark:border-slate-700 px-2.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <Plus className="h-3.5 w-3.5" />
                افزودن سؤال
              </button>
            </div>

            {questions.map((q, idx) => (
              <div
                key={idx}
                className="space-y-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    سؤال {formatNumberFa(idx + 1)}
                  </span>
                  {questions.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setQuestions((prev) => prev.filter((_, i) => i !== idx))}
                      className="text-rose-600 hover:text-rose-700"
                      title="حذف سؤال"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <input
                  required
                  placeholder="متن سؤال..."
                  value={q.question_text}
                  onChange={(e) =>
                    setQuestions((prev) =>
                      prev.map((item, i) => (i === idx ? { ...item, question_text: e.target.value } : item))
                    )
                  }
                  className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
                />
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <select
                    value={q.question_type}
                    onChange={(e) =>
                      setQuestions((prev) =>
                        prev.map((item, i) => (i === idx ? { ...item, question_type: e.target.value } : item))
                      )
                    }
                    className="h-9 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs text-slate-900 dark:text-slate-100"
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
                      checked={q.is_required}
                      onChange={(e) =>
                        setQuestions((prev) =>
                          prev.map((item, i) => (i === idx ? { ...item, is_required: e.target.checked } : item))
                        )
                      }
                      className="accent-teal-700"
                    />
                    پاسخ الزامی باشد
                  </label>
                </div>
                {["SINGLE_SELECT", "MULTI_SELECT"].includes(q.question_type) && (
                  <input
                    required
                    placeholder="گزینه‌ها را با ویرگول (،) جدا کنید؛ مثلاً: عالی، خوب، نیازمند بهبود"
                    value={q.optionsText}
                    onChange={(e) =>
                      setQuestions((prev) =>
                        prev.map((item, i) => (i === idx ? { ...item, optionsText: e.target.value } : item))
                      )
                    }
                    className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
                  />
                )}
              </div>
            ))}
          </div>

          <button
            type="submit"
            disabled={createMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {createMut.isPending ? "در حال ذخیره..." : "انتشار و ذخیره نظرسنجی"}
          </button>
        </form>
      </ModalDrawer>

      {/* Edit Survey Metadata Modal */}
      <ModalDrawer
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        title={`ویرایش فرم نظرسنجی — ${editTarget?.title || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!editTarget) return;
            updateMut.mutate({
              id: editTarget.id,
              agencyId: editTarget.agency_id,
              body: editForm,
            });
          }}
          className="space-y-4"
        >
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">عنوان نظرسنجی</label>
            <input
              required
              value={editForm.title}
              onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">توضیحات</label>
            <textarea
              rows={3}
              value={editForm.description}
              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">جامعه هدف</label>
              <select
                value={editForm.target_audience}
                onChange={(e) => setEditForm({ ...editForm, target_audience: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
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
                value={editForm.crm_trigger_event}
                onChange={(e) => setEditForm({ ...editForm, crm_trigger_event: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
              >
                {Object.entries(TRIGGER_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-slate-700 dark:text-slate-300">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                className="accent-teal-700"
              />
              نظرسنجی فعال باشد
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={editForm.allow_anonymous}
                onChange={(e) => setEditForm({ ...editForm, allow_anonymous: e.target.checked })}
                className="accent-teal-700"
              />
              پاسخ ناشناس مجاز باشد
            </label>
          </div>
          <div className="flex items-center justify-between gap-2 pt-2">
            {editTarget && (
              <Link
                href={`/dashboard/surveys/${editTarget.id}`}
                className="text-xs font-semibold text-teal-700 dark:text-teal-400 hover:underline"
              >
                ورود به ویرایشگر کامل سؤالات و پاسخ‌ها
              </Link>
            )}
            <button
              type="submit"
              disabled={updateMut.isPending}
              className="h-10 rounded-lg bg-teal-700 px-5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              {updateMut.isPending ? "در حال ذخیره..." : "ذخیره تغییرات"}
            </button>
          </div>
        </form>
      </ModalDrawer>
    </div>
  );
}
