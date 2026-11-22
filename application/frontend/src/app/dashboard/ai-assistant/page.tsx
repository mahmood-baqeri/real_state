"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Check, Copy, FileText, Globe, Send, Sparkles, UserCheck } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AiChatMessageResult, AiStatusResponse } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { useToast } from "@/components/ui/ToastProvider";
import { formatMoney, formatNumberFa } from "@/lib/formatters";

interface AgencyPropertyOption {
  id: string;
  property_code: string;
  title: string;
}

interface CustomerOption {
  id: string;
  full_name: string;
  primary_phone: string;
}

interface PropertyDraftResult {
  is_draft: boolean;
  auto_published: boolean;
  property_code: string;
  suggested_title: string;
  suggested_description: string;
  seo_keywords: string[];
}

interface CrmSummaryResult {
  is_draft: boolean;
  customer_name: string;
  lead_score: number;
  readiness_level: string;
  open_tasks_count: number;
  executive_summary: string;
  recommended_next_action: string;
}

interface SeoDraftResult {
  is_draft: boolean;
  auto_published: boolean;
  meta_title: string;
  meta_description: string;
  suggested_slug: string;
  focus_keywords: string[];
}

interface PortfolioInsights {
  total_properties: number;
  deals_count: number;
  deals_volume: string;
  recommendations: string[];
}

interface AiLogItem {
  id: string;
  tool_type: string;
  prompt_summary: string;
  provider: string;
  model_name?: string;
  tokens_used?: number;
  user_name: string;
  created_at: string;
}

interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  meta?: string;
}

interface ContentTopicItem {
  title: string;
  content_type: string;
  keywords: string[];
  audience: string;
}

interface GeneratedContentDraft {
  is_draft: boolean;
  auto_published: boolean;
  title: string;
  slug: string;
  summary: string;
  content_body: string;
  meta_title: string;
  meta_description: string;
  keywords: string[];
  content_type: string;
  language: string;
  tone: string;
  target_audience: string;
  ai_model: string;
  provider: string;
  tokens_used: number;
}

const CONTENT_TYPE_OPTIONS = [
  { value: "ARTICLE", label: "مقاله تخصصی (ARTICLE)" },
  { value: "EDUCATIONAL", label: "محتوای آموزشی (EDUCATIONAL)" },
  { value: "NEWS", label: "خبر و گزارش بازار (NEWS)" },
  { value: "PROMOTIONAL", label: "متن تبلیغاتی (PROMOTIONAL)" },
  { value: "SEO", label: "محتوای سئو (SEO)" },
  { value: "SOCIAL_MEDIA", label: "پست شبکه‌های اجتماعی (SOCIAL_MEDIA)" },
  { value: "LISTING_DESCRIPTION", label: "توضیحات آگهی ملک (LISTING_DESCRIPTION)" },
];

export default function AiAssistantPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();

  const [selectedModel, setSelectedModel] = useState("gpt-4o");
  const [taskMode, setTaskMode] = useState("GENERAL");
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatTurn[]>([]);

  // Content Studio state
  const [contentForm, setContentForm] = useState({
    topic: "",
    content_type: "ARTICLE",
    language: "fa",
    tone: "PROFESSIONAL",
    target_audience: "خریداران و سرمایه‌گذاران املاک",
    keywordsText: "خرید ملک، مشاوره املاک، سرمایه‌گذاری",
    focus_city: "تهران",
    custom_instructions: "",
  });
  const [suggestedTopics, setSuggestedTopics] = useState<ContentTopicItem[]>([]);
  const [contentDraft, setContentDraft] = useState<{
    title: string;
    slug: string;
    summary: string;
    content_body: string;
    meta_title: string;
    meta_description: string;
    ai_model: string;
    tokens_used: number;
  } | null>(null);
  const [rewriteInstruction, setRewriteInstruction] = useState("بهبود ساختار، خوانایی و جذابیت برای مخاطب");

  const [selectedPropId, setSelectedPropId] = useState("");
  const [tone, setTone] = useState("FORMAL");
  const [editableCopy, setEditableCopy] = useState("");

  const [selectedCustId, setSelectedCustId] = useState("");
  const [crmResult, setCrmResult] = useState<CrmSummaryResult | null>(null);

  const [seoInput, setSeoInput] = useState({ title: "", body_excerpt: "", target_city: "تهران" });
  const [seoResult, setSeoResult] = useState<SeoDraftResult | null>(null);

  const statusQ = useQuery({
    queryKey: ["ai-status", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<AiStatusResponse>("/api/v1/ai/status", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const propsQ = useQuery({
    queryKey: ["ai-props", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<AgencyPropertyOption[]>("/api/v1/properties?page_size=50", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const custsQ = useQuery({
    queryKey: ["ai-customers", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<CustomerOption[]>("/api/v1/customers?page_size=50", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const insightsQ = useQuery({
    queryKey: ["ai-portfolio", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<PortfolioInsights>("/api/v1/ai/portfolio-insights", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const logsQ = useQuery({
    queryKey: ["ai-logs", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<AiLogItem[]>("/api/v1/ai/logs", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const chatMut = useMutation({
    mutationFn: async (msgText: string) =>
      (
        await apiFetch<AiChatMessageResult>("/api/v1/ai/assistant/chat", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({
            message: msgText,
            task_mode: taskMode,
            model: selectedModel,
            history: chatHistory.slice(-6).map((h) => ({ role: h.role, content: h.content })),
          }),
        })
      ).data,
    onSuccess: (res, msgText) => {
      setChatHistory((prev) => [
        ...prev,
        { role: "user", content: msgText },
        {
          role: "assistant",
          content: res.reply,
          meta: `${res.provider} · ${res.model} · ${formatNumberFa(res.latency_ms)}ms`,
        },
      ]);
      setChatInput("");
      qc.invalidateQueries({ queryKey: ["ai-logs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const topicsMut = useMutation({
    mutationFn: async () => {
      const qs = new URLSearchParams({
        content_type: contentForm.content_type,
        focus_city: contentForm.focus_city,
        audience: contentForm.target_audience,
      });
      return (
        await apiFetch<{ topics: ContentTopicItem[] }>(`/api/v1/ai/content/topics?${qs.toString()}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
    onSuccess: (d) => {
      setSuggestedTopics(d.topics || []);
      toast.success("موضوعات تخصصی املاک پیشنهاد شدند.");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const generateContentMut = useMutation({
    mutationFn: async () => {
      const keywords = contentForm.keywordsText
        .split(/[,،]+/)
        .map((k) => k.trim())
        .filter(Boolean);
      return (
        await apiFetch<GeneratedContentDraft>("/api/v1/ai/content/generate", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({
            topic: contentForm.topic,
            content_type: contentForm.content_type,
            language: contentForm.language,
            tone: contentForm.tone,
            target_audience: contentForm.target_audience,
            keywords,
            custom_instructions: contentForm.custom_instructions,
            model: selectedModel,
          }),
        })
      ).data;
    },
    onSuccess: (d) => {
      setContentDraft({
        title: d.title,
        slug: d.slug,
        summary: d.summary,
        content_body: d.content_body,
        meta_title: d.meta_title,
        meta_description: d.meta_description,
        ai_model: d.ai_model || selectedModel,
        tokens_used: d.tokens_used || 0,
      });
      toast.success("پیش‌نویس محتوا تولید شد (بدون انتشار خودکار؛ قابل ویرایش و ذخیره در CMS).");
      qc.invalidateQueries({ queryKey: ["ai-logs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rewriteContentMut = useMutation({
    mutationFn: async () => {
      if (!contentDraft) throw new Error("ابتدا محتوایی تولید یا وارد کنید.");
      const keywords = contentForm.keywordsText
        .split(/[,،]+/)
        .map((k) => k.trim())
        .filter(Boolean);
      return (
        await apiFetch<{ title: string; summary: string; content_body: string; ai_model?: string; tokens_used?: number }>(
          "/api/v1/ai/content/rewrite",
          {
            method: "POST",
            token: accessToken,
            agencyId: activeAgencyId,
            body: JSON.stringify({
              title: contentDraft.title,
              content_body: contentDraft.content_body,
              instruction: rewriteInstruction,
              tone: contentForm.tone,
              language: contentForm.language,
              keywords,
              model: selectedModel,
            }),
          }
        )
      ).data;
    },
    onSuccess: (d) => {
      setContentDraft((prev) =>
        prev
          ? {
              ...prev,
              title: d.title || prev.title,
              summary: d.summary || prev.summary,
              content_body: d.content_body,
              ai_model: d.ai_model || prev.ai_model,
              tokens_used: d.tokens_used || prev.tokens_used,
            }
          : prev
      );
      toast.success("محتوا با دستور جدید بازنویسی شد.");
      qc.invalidateQueries({ queryKey: ["ai-logs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const saveContentDraftMut = useMutation({
    mutationFn: async () => {
      if (!contentDraft) throw new Error("پیش‌نویسی برای ذخیره وجود ندارد.");
      const keywords = contentForm.keywordsText
        .split(/[,،]+/)
        .map((k) => k.trim())
        .filter(Boolean);
      return (
        await apiFetch<{ id: string; status: string }>("/api/v1/ai/content/save-draft", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({
            title: contentDraft.title,
            slug: contentDraft.slug,
            article_type: contentForm.content_type,
            summary: contentDraft.summary,
            content_body: contentDraft.content_body,
            language: contentForm.language,
            tone: contentForm.tone,
            target_audience: contentForm.target_audience,
            keywords,
            ai_model: contentDraft.ai_model,
            ai_tokens_used: contentDraft.tokens_used,
            meta_title: contentDraft.meta_title,
            meta_description: contentDraft.meta_description,
            tags: keywords.slice(0, 5),
          }),
        })
      ).data;
    },
    onSuccess: () => {
      toast.success("محتوا به‌عنوان پیش‌نویس (DRAFT) در بخش CMS ذخیره شد و آماده بازبینی و انتشار است.");
      qc.invalidateQueries({ queryKey: ["cms-articles"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const propCopyMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<PropertyDraftResult>("/api/v1/ai/property-copy", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({ property_id: selectedPropId, tone }),
        })
      ).data,
    onSuccess: (data) => {
      setEditableCopy(
        `${data.suggested_title}\n\n${data.suggested_description}\n\nکلیدواژه‌ها: ${data.seo_keywords.join("، ")}`
      );
      toast.success("پیش‌نویس آگهی تولید شد (قابل ویرایش، بدون انتشار خودکار).");
      qc.invalidateQueries({ queryKey: ["ai-logs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const crmMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<CrmSummaryResult>("/api/v1/ai/crm-summary", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({ customer_id: selectedCustId }),
        })
      ).data,
    onSuccess: (data) => {
      setCrmResult(data);
      toast.success("تحلیل خلاصه CRM آماده شد.");
      qc.invalidateQueries({ queryKey: ["ai-logs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const seoMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<SeoDraftResult>("/api/v1/ai/seo-draft", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify(seoInput),
        })
      ).data,
    onSuccess: (data) => {
      setSeoResult(data);
      toast.success("متادیتای سئو تولید شد.");
      qc.invalidateQueries({ queryKey: ["ai-logs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rawModels = statusQ.data?.supported_models || [
    { id: "gpt-4o", label: "GPT-4o (توصیه‌شده متعادل)" },
    { id: "gpt-5.6", label: "GPT-5.6 (تحلیل پیشرفته)" },
    { id: "gpt-6.2-sol", label: "GPT-6.2 Sol (استدلال عمیق)" },
    { id: "claude-sonnet", label: "Claude Sonnet (نگارش فارسی روان)" },
    { id: "gemini-flash", label: "Gemini Flash (پاسخ سریع)" },
    { id: "deepseek-v4", label: "DeepSeek V4 (اقتصادی و تحلیلی)" },
  ];
  const models = rawModels.map((m) =>
    typeof m === "string" ? { id: m, label: m } : m
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="دستیار هوشمند آژانس (متصل به GapGPT)"
        subtitle="استودیو تولید محتوای متنی، مشاوره تخصصی مبتنی بر داده‌های مجاز، تولید متن آگهی و تحلیل سئو"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "دستیار هوشمند" }]}
      />

      {statusQ.data && (
        <div
          className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 text-xs ${
            statusQ.data.configured
              ? "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200"
              : "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200"
          }`}
        >
          <div className="flex items-center gap-2 font-semibold">
            <Bot className="h-4 w-4 shrink-0" />
            <span>
              سرویس‌دهنده فعال: {statusQ.data.provider} ({statusQ.data.status}) — {statusQ.data.message}
            </span>
          </div>
          <span className="font-mono text-[11px]">{statusQ.data.base_url}</span>
        </div>
      )}

      {!activeAgencyId ? (
        <div className="rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50 dark:bg-amber-950/30 p-4 text-xs font-medium text-amber-900 dark:text-amber-200">
          برای استفاده از ابزارهای دستیار هوشمند روی فایل‌های ملکی و مشتریان، یک آژانس را از نوار بالای صفحه انتخاب کنید.
        </div>
      ) : (
        insightsQ.data && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KpiCard
              label="کل فایل‌های قابل تحلیل آژانس"
              value={formatNumberFa(insightsQ.data.total_properties)}
              icon={<Bot className="h-4 w-4" />}
            />
            <KpiCard label="تعداد معاملات ثبت‌شده" value={formatNumberFa(insightsQ.data.deals_count)} />
            <KpiCard label="حجم کل معاملات آژانس" value={formatMoney(insightsQ.data.deals_volume, "IRT", "IRT")} />
          </div>
        )
      )}

      {/* AI Content Generation Studio */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
              <FileText className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              استودیو تولید و بازنویسی محتوای متنی املاک با هوش مصنوعی
            </div>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              پیشنهاد موضوع، تولید محتوای ساختاریافته (مقاله، آموزشی، خبر، تبلیغاتی، سئو، شبکه اجتماعی، توضیحات آگهی) و ذخیره پیش‌نویس در CMS بدون انتشار خودکار
            </p>
          </div>
          <button
            type="button"
            disabled={topicsMut.isPending}
            onClick={() => topicsMut.mutate()}
            className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-teal-700 px-3.5 text-xs font-semibold text-teal-700 hover:bg-teal-50 dark:border-teal-500 dark:text-teal-300 dark:hover:bg-teal-950/40 disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {topicsMut.isPending ? "در حال پیشنهاد..." : "پیشنهاد موضوعات املاک"}
          </button>
        </div>

        {suggestedTopics.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">
              موضوعات پیشنهادی (برای انتخاب کلیک کنید):
            </div>
            <div className="flex flex-wrap gap-2">
              {suggestedTopics.map((t, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() =>
                    setContentForm((prev) => ({
                      ...prev,
                      topic: t.title,
                      content_type: t.content_type || prev.content_type,
                      target_audience: t.audience || prev.target_audience,
                      keywordsText: (t.keywords || []).join("، ") || prev.keywordsText,
                    }))
                  }
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-right text-xs text-slate-800 hover:border-teal-600 hover:bg-teal-50 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200 dark:hover:border-teal-500"
                >
                  {t.title}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div className="md:col-span-2">
            <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              موضوع دلخواه یا انتخاب‌شده
            </label>
            <input
              value={contentForm.topic}
              onChange={(e) => setContentForm({ ...contentForm, topic: e.target.value })}
              placeholder="مثال: راهنمای کامل بررسی اصالت سند تک‌برگ پیش از معامله..."
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              نوع محتوا
            </label>
            <select
              value={contentForm.content_type}
              onChange={(e) => setContentForm({ ...contentForm, content_type: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs text-slate-900 dark:text-slate-100"
            >
              {CONTENT_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              زبان خروجی
            </label>
            <select
              value={contentForm.language}
              onChange={(e) => setContentForm({ ...contentForm, language: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs text-slate-900 dark:text-slate-100"
            >
              <option value="fa">فارسی (fa)</option>
              <option value="en">انگلیسی (en)</option>
              <option value="ar">عربی (ar)</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div>
            <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              لحن نگارش
            </label>
            <select
              value={contentForm.tone}
              onChange={(e) => setContentForm({ ...contentForm, tone: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs text-slate-900 dark:text-slate-100"
            >
              <option value="PROFESSIONAL">حرفه‌ای و تخصصی</option>
              <option value="FORMAL">رسمی و اداری</option>
              <option value="FRIENDLY">صمیمی و روان</option>
              <option value="EDUCATIONAL">آموزشی و راهنما</option>
              <option value="PERSUASIVE">تبلیغاتی و متقاعدکننده</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              مخاطب هدف
            </label>
            <input
              value={contentForm.target_audience}
              onChange={(e) => setContentForm({ ...contentForm, target_audience: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              شهر / منطقه تمرکز
            </label>
            <input
              value={contentForm.focus_city}
              onChange={(e) => setContentForm({ ...contentForm, focus_city: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              کلمات کلیدی (جداشده با ویرگول)
            </label>
            <input
              value={contentForm.keywordsText}
              onChange={(e) => setContentForm({ ...contentForm, keywordsText: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input
            value={contentForm.custom_instructions}
            onChange={(e) => setContentForm({ ...contentForm, custom_instructions: e.target.value })}
            placeholder="دستور تکمیلی اختیاری برای هوش مصنوعی (مثلاً اشاره به تور مجازی و مدارک هویتی)..."
            className="h-10 flex-1 min-w-[240px] rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
          />
          <button
            type="button"
            disabled={contentForm.topic.trim().length < 3 || generateContentMut.isPending}
            onClick={() => generateContentMut.mutate()}
            className="inline-flex h-10 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {generateContentMut.isPending ? "در حال تولید محتوا..." : "تولید پیش‌نویس محتوا"}
          </button>
        </div>

        {contentDraft && (
          <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/60">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                پیش‌نویس قابل ویرایش (وضعیت: DRAFT — بدون انتشار خودکار)
              </span>
              <span className="font-mono text-[11px] text-slate-500">
                {contentDraft.ai_model} · {formatNumberFa(contentDraft.tokens_used)} tokens
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <input
                value={contentDraft.title}
                onChange={(e) => setContentDraft({ ...contentDraft, title: e.target.value })}
                placeholder="عنوان"
                className="h-9 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-bold"
              />
              <input
                dir="ltr"
                value={contentDraft.slug}
                onChange={(e) =>
                  setContentDraft({
                    ...contentDraft,
                    slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"),
                  })
                }
                placeholder="url-slug"
                className="h-9 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 font-mono text-xs"
              />
            </div>

            <input
              value={contentDraft.summary}
              onChange={(e) => setContentDraft({ ...contentDraft, summary: e.target.value })}
              placeholder="چکیده محتوا"
              className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs"
            />

            <textarea
              rows={7}
              value={contentDraft.content_body}
              onChange={(e) => setContentDraft({ ...contentDraft, content_body: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-3 text-xs leading-6"
            />

            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              <input
                value={contentDraft.meta_title}
                onChange={(e) => setContentDraft({ ...contentDraft, meta_title: e.target.value })}
                placeholder="Meta Title"
                className="h-9 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs"
              />
              <input
                value={contentDraft.meta_description}
                onChange={(e) => setContentDraft({ ...contentDraft, meta_description: e.target.value })}
                placeholder="Meta Description"
                className="h-9 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <input
                value={rewriteInstruction}
                onChange={(e) => setRewriteInstruction(e.target.value)}
                placeholder="دستور بازنویسی..."
                className="h-9 flex-1 min-w-[200px] rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs"
              />
              <button
                type="button"
                disabled={rewriteContentMut.isPending}
                onClick={() => rewriteContentMut.mutate()}
                className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {rewriteContentMut.isPending ? "در حال بازنویسی..." : "بازنویسی مجدد"}
              </button>
              <button
                type="button"
                onClick={async () => {
                  await navigator.clipboard.writeText(`${contentDraft.title}\n\n${contentDraft.content_body}`).catch(() => {});
                  toast.success("متن محتوا کپی شد.");
                }}
                className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-semibold"
              >
                <Copy className="h-3.5 w-3.5" />
                کپی
              </button>
              <button
                type="button"
                disabled={saveContentDraftMut.isPending}
                onClick={() => saveContentDraftMut.mutate()}
                className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg bg-emerald-700 px-4 text-xs font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" />
                {saveContentDraftMut.isPending ? "در حال ذخیره..." : "ذخیره به‌عنوان پیش‌نویس در CMS"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Grounded Agency Chat Workspace */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            <Sparkles className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            گفتگوی هوشمند با دستیار اختصاصی آژانس (GapGPT + ایزوله‌سازی RBAC)
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
            <select
              value={taskMode}
              onChange={(e) => setTaskMode(e.target.value)}
              className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 dark:border-slate-700 dark:bg-slate-950"
            >
              <option value="GENERAL">تحلیل عمومی و پاسخ مدیریتی</option>
              <option value="PROPERTY_MATCH">پیشنهاد تطبیق فایل و خریدار</option>
              <option value="LEAD_FOLLOWUP">اولویت‌بندی پیگیری سرنخ‌ها</option>
              <option value="NEGOTIATION_ADVICE">استراتژی مذاکره قیمتی</option>
              <option value="AD_COPY">تولید متن تبلیغاتی آگهی</option>
            </select>
          </div>
        </div>

        <div className="max-h-80 space-y-3 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/60">
          {chatHistory.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400">
              سؤال خود را بپرسید؛ مثلاً «کدام مشتریان آماده بازدید این هفته هستند؟» یا «برای فایل‌های زعفرانیه چه راهکار قیمت‌گذاری پیشنهاد می‌کنی؟»
            </div>
          ) : (
            chatHistory.map((turn, idx) => (
              <div
                key={idx}
                className={`rounded-xl p-3.5 text-xs leading-relaxed ${
                  turn.role === "user"
                    ? "mr-8 bg-teal-700 text-white"
                    : "ml-8 border border-slate-200 bg-white text-slate-800 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                }`}
              >
                <div className="whitespace-pre-line">{turn.content}</div>
                {turn.meta && (
                  <div className="mt-2 font-mono text-[10px] text-slate-400">{turn.meta}</div>
                )}
              </div>
            ))
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!chatInput.trim()) return;
            chatMut.mutate(chatInput.trim());
          }}
          className="flex gap-2"
        >
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="پرسش یا دستور تحلیلی برای دستیار هوشمند آژانس..."
            className="h-10 flex-1 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          />
          <button
            type="submit"
            disabled={chatMut.isPending || !chatInput.trim()}
            className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            <Send className="h-3.5 w-3.5" />
            {chatMut.isPending ? "در حال پردازش..." : "ارسال به دستیار"}
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 1. Property Copy Draft */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            <FileText className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            تولید پیش‌نویس متن آگهی ملک
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <select
              disabled={!activeAgencyId}
              value={selectedPropId}
              onChange={(e) => setSelectedPropId(e.target.value)}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100 disabled:opacity-50"
            >
              <option value="">انتخاب فایل ملکی...</option>
              {(propsQ.data || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.property_code} — {p.title}
                </option>
              ))}
            </select>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            >
              <option value="FORMAL">لحن رسمی و استاندارد دفتر املاک</option>
              <option value="INVESTMENT">لحن تحلیلی و سرمایه‌گذاری</option>
            </select>
          </div>
          <button
            type="button"
            disabled={!selectedPropId || propCopyMut.isPending}
            onClick={() => propCopyMut.mutate()}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5" />
            تولید پیش‌نویس آگهی
          </button>
          <textarea
            rows={5}
            placeholder="پیش‌نویس قابل ویرایش آگهی اینجا نمایش داده می‌شود..."
            value={editableCopy}
            onChange={(e) => setEditableCopy(e.target.value)}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 p-3 text-xs leading-relaxed text-slate-900 dark:text-slate-100"
          />
          {editableCopy && (
            <button
              type="button"
              onClick={async () => {
                await navigator.clipboard.writeText(editableCopy).catch(() => {});
                toast.success("متن پیش‌نویس کپی شد.");
              }}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-300 dark:border-slate-700 px-2.5 text-xs font-semibold"
            >
              <Copy className="h-3.5 w-3.5" />
              کپی متن پیش‌نویس
            </button>
          )}
        </div>

        {/* 2. CRM Summary */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            <UserCheck className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            خلاصه‌سازی پرونده مشتری CRM
          </div>
          <div className="flex gap-2">
            <select
              disabled={!activeAgencyId}
              value={selectedCustId}
              onChange={(e) => setSelectedCustId(e.target.value)}
              className="h-10 flex-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100 disabled:opacity-50"
            >
              <option value="">انتخاب مشتری آژانس...</option>
              {(custsQ.data || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name} ({c.primary_phone})
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={!selectedCustId || crmMut.isPending}
              onClick={() => crmMut.mutate()}
              className="h-10 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              تحلیل پرونده
            </button>
          </div>
          {crmResult ? (
            <div className="space-y-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-4 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 dark:text-slate-100">{crmResult.customer_name}</span>
                <span className="font-mono font-semibold text-teal-700 dark:text-teal-400">
                  امتیاز آمادگی: {formatNumberFa(crmResult.lead_score)} ({crmResult.readiness_level})
                </span>
              </div>
              <p className="leading-relaxed text-slate-700 dark:text-slate-300">{crmResult.executive_summary}</p>
              <div className="rounded-md bg-teal-50 dark:bg-teal-950/40 p-2.5 font-semibold text-teal-900 dark:text-teal-200 flex items-center gap-1.5">
                <Check className="h-4 w-4 shrink-0" />
                اقدام پیشنهادی بعدی: {crmResult.recommended_next_action}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-slate-300 dark:border-slate-700 p-6 text-center text-xs text-slate-500 dark:text-slate-400">
              یک مشتری از آژانس انتخاب کنید تا خلاصه تعاملات، کارهای باز و گام پیشنهادی بعدی استخراج شود.
            </div>
          )}
        </div>
      </div>

      {/* 3. SEO Draft */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
          <Globe className="h-4 w-4 text-teal-700 dark:text-teal-400" />
          دستیار پیش‌نویس متادیتای سئو (SEO) برای صفحات و مقالات
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            placeholder="عنوان صفحه یا مقاله..."
            value={seoInput.title}
            onChange={(e) => setSeoInput({ ...seoInput, title: e.target.value })}
            className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
          />
          <input
            placeholder="شهر هدف (مثلاً تهران)"
            value={seoInput.target_city}
            onChange={(e) => setSeoInput({ ...seoInput, target_city: e.target.value })}
            className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
          />
          <button
            type="button"
            disabled={!seoInput.title.trim() || seoMut.isPending}
            onClick={() => seoMut.mutate()}
            className="h-10 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            تولید متای سئو (بدون انتشار خودکار)
          </button>
        </div>
        <textarea
          rows={2}
          placeholder="خلاصه محتوای مقاله یا توضیحات ملک..."
          value={seoInput.body_excerpt}
          onChange={(e) => setSeoInput({ ...seoInput, body_excerpt: e.target.value })}
          className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-xs text-slate-900 dark:text-slate-100"
        />

        {seoResult && (
          <div className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-4 text-xs md:grid-cols-2">
            <div>
              <span className="font-semibold text-slate-500 dark:text-slate-400">Meta Title پیشنهادی:</span>
              <div className="mt-1 font-bold text-slate-900 dark:text-slate-100">{seoResult.meta_title}</div>
            </div>
            <div>
              <span className="font-semibold text-slate-500 dark:text-slate-400">Slug پیشنهادی:</span>
              <div className="mt-1 font-mono text-teal-700 dark:text-teal-400">{seoResult.suggested_slug}</div>
            </div>
            <div className="md:col-span-2">
              <span className="font-semibold text-slate-500 dark:text-slate-400">Meta Description پیشنهادی:</span>
              <div className="mt-1 text-slate-700 dark:text-slate-300">{seoResult.meta_description}</div>
            </div>
          </div>
        )}
      </div>

      {/* 4. Audit Logs */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
        <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
          تاریخچه ممیزی درخواست‌های دستیار هوشمند
        </h2>
        {(logsQ.data || []).length === 0 ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">هنوز درخواستی در این آژانس ثبت نشده است.</p>
        ) : (
          <div className="space-y-2">
            {(logsQ.data || []).slice(0, 10).map((log) => (
              <div
                key={log.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-2 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-teal-700 dark:text-teal-400">{log.tool_type}</span>
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    {log.provider}
                    {log.model_name ? `/${log.model_name}` : ""}
                  </span>
                  <span className="text-slate-700 dark:text-slate-300">{log.prompt_summary}</span>
                </div>
                <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
                  <span>{log.user_name}</span>
                  <DateDisplay value={log.created_at} withTime />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
