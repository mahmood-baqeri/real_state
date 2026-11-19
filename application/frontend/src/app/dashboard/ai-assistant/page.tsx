// Path: frontend/src/app/dashboard/ai-assistant/page.tsx

"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Check, Copy, FileText, Globe, Sparkles, UserCheck } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
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
  user_name: string;
  created_at: string;
}

export default function AiAssistantPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();

  const [selectedPropId, setSelectedPropId] = useState("");
  const [tone, setTone] = useState("FORMAL");
  const [editableCopy, setEditableCopy] = useState("");

  const [selectedCustId, setSelectedCustId] = useState("");
  const [crmResult, setCrmResult] = useState<CrmSummaryResult | null>(null);

  const [seoInput, setSeoInput] = useState({ title: "", body_excerpt: "", target_city: "تهران" });
  const [seoResult, setSeoResult] = useState<SeoDraftResult | null>(null);
  const [geminiDraft, setGeminiDraft] = useState("");

  const propsQ = useQuery({
    queryKey: ["ai-props", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<AgencyPropertyOption[]>("/api/v1/properties?page_size=50", { token: accessToken, agencyId: activeAgencyId })).data,
  });

  const custsQ = useQuery({
    queryKey: ["ai-customers", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<CustomerOption[]>("/api/v1/customers?page_size=50", { token: accessToken, agencyId: activeAgencyId })).data,
  });

  const insightsQ = useQuery({
    queryKey: ["ai-portfolio", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<PortfolioInsights>("/api/v1/ai/portfolio-insights", { token: accessToken, agencyId: activeAgencyId })).data,
  });

  const logsQ = useQuery({
    queryKey: ["ai-logs", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<AiLogItem[]>("/api/v1/ai/logs", { token: accessToken, agencyId: activeAgencyId })).data,
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
      setEditableCopy(`${data.suggested_title}\n\n${data.suggested_description}\n\nکلیدواژه‌ها: ${data.seo_keywords.join("، ")}`);
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

  const geminiMut = useMutation({
    mutationFn: async (payload: { task: string; context: string }) => {
      const res = await fetch("/api/ai/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.detail || "خطا در ارتباط با Gemini");
      }
      return json.data as { text: string; model: string };
    },
    onSuccess: (data) => {
      setGeminiDraft(data.text);
      toast.success("پیش‌نویس تکمیلی Gemini آماده شد.");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="دستیار هوشمند آژانس (ایزوله و پیش‌نویس‌محور)"
        subtitle="تولید متن آگهی ملک، خلاصه تعاملات CRM و پیشنهاد متادیتای سئو منحصراً بر اساس داده‌های مجاز آژانس جاری"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "دستیار هوشمند" }]}
      />

      {!activeAgencyId ? (
        <div className="rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50 dark:bg-amber-950/30 p-4 text-xs font-medium text-amber-900 dark:text-amber-200">
          برای استفاده از ابزارهای دستیار هوشمند روی فایل‌های ملکی و مشتریان، یک آژانس را از نوار بالای صفحه انتخاب کنید. (ابزار پیش‌نویس سئو بدون انتخاب آژانس نیز فعال است.)
        </div>
      ) : (
        insightsQ.data && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KpiCard label="کل فایل‌های قابل تحلیل آژانس" value={formatNumberFa(insightsQ.data.total_properties)} icon={<Bot className="h-4 w-4" />} />
            <KpiCard label="تعداد معاملات ثبت‌شده" value={formatNumberFa(insightsQ.data.deals_count)} />
            <KpiCard label="حجم کل معاملات آژانس" value={formatMoney(insightsQ.data.deals_volume, "IRT", "IRT")} />
          </div>
        )
      )}

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
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!selectedPropId || propCopyMut.isPending}
              onClick={() => propCopyMut.mutate()}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
            >
              <Sparkles className="h-3.5 w-3.5" />
              تولید پیش‌نویس بومی
            </button>
            <button
              type="button"
              disabled={!editableCopy.trim() || geminiMut.isPending}
              onClick={() => geminiMut.mutate({ task: "PROPERTY_COPY_POLISH", context: editableCopy })}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-xs font-semibold text-slate-800 dark:text-slate-200 disabled:opacity-50"
            >
              بازنویسی تکمیلی با Gemini
            </button>
          </div>
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

        {geminiDraft && (
          <div className="rounded-lg border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/60 dark:bg-indigo-950/30 p-4 text-xs space-y-1.5">
            <div className="font-bold text-indigo-900 dark:text-indigo-300">خروجی پیش‌نویس تکمیلی Gemini:</div>
            <p className="whitespace-pre-wrap leading-relaxed text-slate-800 dark:text-slate-200">{geminiDraft}</p>
          </div>
        )}
      </div>

      {/* 4. Audit Logs */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
        <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">تاریخچه ممیزی درخواست‌های دستیار هوشمند</h2>
        {(logsQ.data || []).length === 0 ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">هنوز درخواستی در این آژانس ثبت نشده است.</p>
        ) : (
          <div className="space-y-2">
            {(logsQ.data || []).slice(0, 8).map((log) => (
              <div
                key={log.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-2 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-teal-700 dark:text-teal-400">{log.tool_type}</span>
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
