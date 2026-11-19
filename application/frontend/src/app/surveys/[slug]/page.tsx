// Path: frontend/src/app/surveys/[slug]/page.tsx

"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Star } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { formatNumberFa } from "@/lib/formatters";

interface PublicQuestion {
  id: string;
  sort_order: number;
  question_text: string;
  question_type: string;
  options: string[];
  is_required: boolean;
}

interface PublicSurvey {
  id: string;
  agency_name: string;
  title: string;
  slug: string;
  description: string;
  allow_anonymous: boolean;
  questions: PublicQuestion[];
}

interface AnswerState {
  answer_text: string;
  answer_number: number | null;
  selected_options: string[];
}

export default function PublicSurveyFormPage() {
  const params = useParams();
  const slug = String(params?.slug || "");
  const { accessToken, user } = useAuth();
  const [respondentName, setRespondentName] = useState("");
  const [anonId, setAnonId] = useState("");
  const [answers, setAnswers] = useState<Record<string, AnswerState>>({});
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const key = "bonyan_survey_anon_id";
    let existing = localStorage.getItem(key);
    if (!existing) {
      existing = `browser-${Math.random().toString(36).slice(2)}-${Date.now()}`;
      localStorage.setItem(key, existing);
    }
    setAnonId(existing);
  }, []);

  const surveyQ = useQuery({
    queryKey: ["public-survey", slug],
    enabled: !!slug,
    queryFn: async () => (await apiFetch<PublicSurvey>(`/api/v1/surveys/public/${slug}`)).data,
  });

  const submitMut = useMutation({
    mutationFn: async () => {
      const s = surveyQ.data;
      if (!s) return;
      const formattedAnswers = s.questions
        .map((q) => {
          const state = answers[q.id];
          if (!state) return null;
          return {
            question_id: q.id,
            answer_text: state.answer_text || "",
            answer_number: state.answer_number,
            selected_options: state.selected_options || [],
          };
        })
        .filter(Boolean);

      return apiFetch(`/api/v1/surveys/public/${slug}/submit`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          respondent_identifier: anonId || "guest-session",
          respondent_name: respondentName || user?.full_name || "",
          answers: formattedAnswers,
        }),
      });
    },
    onSuccess: () => setSubmitted(true),
  });

  const setQuestionAnswer = (qid: string, patch: Partial<AnswerState>) => {
    setAnswers((prev) => ({
      ...prev,
      [qid]: {
        answer_text: prev[qid]?.answer_text || "",
        answer_number: prev[qid]?.answer_number ?? null,
        selected_options: prev[qid]?.selected_options || [],
        ...patch,
      },
    }));
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10 sm:px-6">
        {surveyQ.isLoading && <LoadingState message="در حال بارگذاری پرسشنامه..." />}
        {surveyQ.error && (
          <ErrorState
            message={surveyQ.error instanceof Error ? surveyQ.error.message : "نظرسنجی یافت نشد."}
            onRetry={() => surveyQ.refetch()}
          />
        )}

        {surveyQ.data && submitted && (
          <div className="rounded-2xl border border-emerald-200 dark:border-emerald-900/60 bg-white dark:bg-slate-900 p-8 text-center space-y-3">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">پاسخ شما با موفقیت ثبت شد</h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              از زمانی که برای ارتقای کیفیت خدمات «{surveyQ.data.agency_name}» اختصاص دادید سپاسگزاریم.
            </p>
          </div>
        )}

        {surveyQ.data && !submitted && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submitMut.mutate();
            }}
            className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 space-y-6"
          >
            <div className="border-b border-slate-200 dark:border-slate-800 pb-5">
              <div className="text-xs font-semibold text-teal-700 dark:text-teal-400">{surveyQ.data.agency_name}</div>
              <h1 className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100">{surveyQ.data.title}</h1>
              {surveyQ.data.description && (
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">{surveyQ.data.description}</p>
              )}
            </div>

            {!user && (
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  نام و نام خانوادگی (اختیاری)
                </label>
                <input
                  placeholder="در صورت تمایل نام خود را وارد کنید..."
                  value={respondentName}
                  onChange={(e) => setRespondentName(e.target.value)}
                  className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
                />
              </div>
            )}

            <div className="space-y-6">
              {surveyQ.data.questions.map((q, idx) => {
                const cur = answers[q.id] || { answer_text: "", answer_number: null, selected_options: [] };

                return (
                  <div key={q.id} className="space-y-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/30 p-4">
                    <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {formatNumberFa(idx + 1)}. {q.question_text}
                      {q.is_required && <span className="mr-1 text-rose-600">*</span>}
                    </div>

                    {q.question_type === "RATING" && (
                      <div className="flex flex-wrap gap-2">
                        {[1, 2, 3, 4, 5].map((n) => (
                          <button
                            key={n}
                            type="button"
                            onClick={() => setQuestionAnswer(q.id, { answer_number: n })}
                            className={`h-10 w-12 rounded-lg border font-mono text-sm font-bold transition-colors ${
                              cur.answer_number === n
                                ? "border-teal-700 bg-teal-700 text-white"
                                : "border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-200"
                            }`}
                          >
                            {formatNumberFa(n)}
                          </button>
                        ))}
                      </div>
                    )}

                    {q.question_type === "STARS" && (
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((n) => {
                          const active = (cur.answer_number || 0) >= n;
                          return (
                            <button
                              key={n}
                              type="button"
                              onClick={() => setQuestionAnswer(q.id, { answer_number: n })}
                              aria-label={`${n} ستاره`}
                              className="rounded-lg p-1.5 transition-transform hover:scale-105"
                            >
                              <Star
                                className={`h-7 w-7 ${
                                  active ? "fill-amber-400 text-amber-500" : "text-slate-300 dark:text-slate-600"
                                }`}
                              />
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {q.question_type === "SCALE" && (
                      <div className="flex flex-wrap gap-1.5">
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                          <button
                            key={n}
                            type="button"
                            onClick={() => setQuestionAnswer(q.id, { answer_number: n })}
                            className={`h-9 w-9 rounded-lg border font-mono text-xs font-bold ${
                              cur.answer_number === n
                                ? "border-teal-700 bg-teal-700 text-white"
                                : "border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-200"
                            }`}
                          >
                            {formatNumberFa(n)}
                          </button>
                        ))}
                      </div>
                    )}

                    {q.question_type === "NPS" && (
                      <div className="space-y-2">
                        <div className="flex flex-wrap gap-1.5">
                          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                            <button
                              key={n}
                              type="button"
                              onClick={() => setQuestionAnswer(q.id, { answer_number: n })}
                              className={`h-9 w-9 rounded-lg border font-mono text-xs font-bold ${
                                cur.answer_number === n
                                  ? "border-teal-700 bg-teal-700 text-white"
                                  : "border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-200"
                              }`}
                            >
                              {formatNumberFa(n)}
                            </button>
                          ))}
                        </div>
                        <div className="flex justify-between text-[11px] text-slate-500 dark:text-slate-400">
                          <span>۰ — اصلاً توصیه نمی‌کنم</span>
                          <span>۱۰ — قطعاً توصیه می‌کنم</span>
                        </div>
                      </div>
                    )}

                    {q.question_type === "YES_NO" && (
                      <div className="flex gap-3">
                        {[
                          { val: "YES", label: "بله" },
                          { val: "NO", label: "خیر" },
                        ].map((opt) => (
                          <button
                            key={opt.val}
                            type="button"
                            onClick={() => setQuestionAnswer(q.id, { answer_text: opt.val })}
                            className={`h-10 min-w-24 rounded-lg border px-4 text-xs font-semibold ${
                              cur.answer_text === opt.val
                                ? "border-teal-700 bg-teal-700 text-white"
                                : "border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-200"
                            }`}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    )}

                    {q.question_type === "SINGLE_SELECT" && (
                      <div className="space-y-2">
                        {q.options.map((opt) => (
                          <label key={opt} className="flex items-center gap-2.5 text-xs text-slate-800 dark:text-slate-200 cursor-pointer">
                            <input
                              type="radio"
                              name={`q-${q.id}`}
                              checked={cur.selected_options[0] === opt}
                              onChange={() => setQuestionAnswer(q.id, { selected_options: [opt] })}
                              className="accent-teal-700"
                            />
                            <span>{opt}</span>
                          </label>
                        ))}
                      </div>
                    )}

                    {q.question_type === "MULTI_SELECT" && (
                      <div className="space-y-2">
                        {q.options.map((opt) => {
                          const checked = cur.selected_options.includes(opt);
                          return (
                            <label key={opt} className="flex items-center gap-2.5 text-xs text-slate-800 dark:text-slate-200 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => {
                                  const next = e.target.checked
                                    ? [...cur.selected_options, opt]
                                    : cur.selected_options.filter((item) => item !== opt);
                                  setQuestionAnswer(q.id, { selected_options: next });
                                }}
                                className="accent-teal-700"
                              />
                              <span>{opt}</span>
                            </label>
                          );
                        })}
                      </div>
                    )}

                    {q.question_type === "TEXT" && (
                      <textarea
                        rows={3}
                        placeholder="نظر یا پیشنهاد خود را بنویسید..."
                        value={cur.answer_text}
                        onChange={(e) => setQuestionAnswer(q.id, { answer_text: e.target.value })}
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-sm text-slate-900 dark:text-slate-100"
                      />
                    )}
                  </div>
                );
              })}
            </div>

            {submitMut.error && (
              <div className="rounded-lg border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/30 p-3 text-xs font-medium text-rose-800 dark:text-rose-300">
                {submitMut.error instanceof Error ? submitMut.error.message : "خطا در ارسال پاسخ"}
              </div>
            )}

            <button
              type="submit"
              disabled={submitMut.isPending}
              className="h-11 w-full rounded-xl bg-teal-700 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              {submitMut.isPending ? "در حال ثبت پاسخ..." : "ثبت نهایی نظرسنجی"}
            </button>
          </form>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
