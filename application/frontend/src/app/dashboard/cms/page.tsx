"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Building2, CheckCircle2, Edit3, FileText, Globe, Mail, Plus, Rss, Sparkles, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { RssTopicsResult } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { useToast } from "@/components/ui/ToastProvider";
import { formatNumberFa } from "@/lib/formatters";

interface CmsCategory {
  id: string;
  name: string;
  slug: string;
}

interface CmsArticle {
  id: string;
  title: string;
  slug: string;
  article_type: string;
  category: CmsCategory | null;
  summary: string;
  content_body: string;
  cover_image_url?: string;
  language?: string;
  tone?: string;
  target_audience?: string;
  ai_generated?: boolean;
  status: string;
  scheduled_for?: string | null;
  meta_title: string;
  meta_description: string;
  reading_time_minutes: number;
  view_count: number;
  published_at: string | null;
  created_at: string;
  versions?: { version_number: number; change_note: string; edited_by: string; created_at: string }[];
}

interface RedirectRule {
  id: string;
  from_path: string;
  to_path: string;
  status_code: number;
  is_active: boolean;
}

interface CooperationReq {
  id: string;
  tracking_code: string;
  agency_name: string;
  city: string;
  manager_name: string;
  manager_phone: string;
  agents_count: number;
  license_number: string;
  status: string;
  approved_agency_id: string | null;
  created_at: string;
}

interface ContactInquiry {
  id: string;
  tracking_code: string;
  full_name: string;
  phone_number: string;
  inquiry_type: string;
  subject: string;
  message: string;
  status: string;
  staff_response: string;
  created_at: string;
}

export default function CmsDashboardPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const isSuper = effectiveRole === "SUPER_ADMIN";

  const [tab, setTab] = useState<"articles" | "redirects" | "cooperation" | "inquiries">("articles");
  const [articleOpen, setArticleOpen] = useState(false);
  const [editingArticleId, setEditingArticleId] = useState<string | null>(null);
  const [scheduleTarget, setScheduleTarget] = useState<CmsArticle | null>(null);
  const [scheduledFor, setScheduledFor] = useState("");
  const [redirectOpen, setRedirectOpen] = useState(false);
  const [activeInquiry, setActiveInquiry] = useState<ContactInquiry | null>(null);
  const [inquiryReply, setInquiryReply] = useState("");
  const [rssUrl, setRssUrl] = useState("");
  const [rssResult, setRssResult] = useState<RssTopicsResult | null>(null);

  const emptyArtForm = {
    title: "",
    slug: "",
    article_type: "ARTICLE",
    category_id: "",
    summary: "",
    content_body: "",
    cover_image_url: "/images/prop-zafaranieh.jpg",
    language: "fa",
    tone: "PROFESSIONAL",
    target_audience: "",
    meta_title: "",
    meta_description: "",
  };
  const [artForm, setArtForm] = useState(emptyArtForm);

  const [redirForm, setRedirForm] = useState({ from_path: "", to_path: "/properties", status_code: 301 });

  const categoriesQ = useQuery({
    queryKey: ["cms-categories"],
    queryFn: async () => (await apiFetch<CmsCategory[]>("/api/v1/cms/public/categories")).data,
  });

  const articlesQ = useQuery({
    queryKey: ["cms-articles"],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<CmsArticle[]>("/api/v1/cms/articles", { token: accessToken, agencyId: activeAgencyId })).data,
  });

  const redirectsQ = useQuery({
    queryKey: ["cms-redirects"],
    enabled: !!accessToken,
    queryFn: async () => (await apiFetch<RedirectRule[]>("/api/v1/seo/redirects", { token: accessToken })).data,
  });

  const coopQ = useQuery({
    queryKey: ["cms-cooperation"],
    enabled: !!accessToken && isSuper,
    queryFn: async () =>
      (await apiFetch<CooperationReq[]>("/api/v1/cms/cooperation-requests", { token: accessToken })).data,
  });

  const inquiriesQ = useQuery({
    queryKey: ["cms-inquiries"],
    enabled: !!accessToken && isSuper,
    queryFn: async () =>
      (await apiFetch<ContactInquiry[]>("/api/v1/cms/contact-inquiries", { token: accessToken })).data,
  });

  const saveArtMut = useMutation({
    mutationFn: async () => {
      if (editingArticleId) {
        return apiFetch(`/api/v1/cms/articles/${editingArticleId}`, {
          method: "PATCH",
          token: accessToken,
          body: JSON.stringify({
            title: artForm.title,
            article_type: artForm.article_type,
            category_id: artForm.category_id || null,
            summary: artForm.summary,
            content_body: artForm.content_body,
            cover_image_url: artForm.cover_image_url,
            language: artForm.language,
            tone: artForm.tone,
            target_audience: artForm.target_audience,
            meta_title: artForm.meta_title,
            meta_description: artForm.meta_description,
            change_note: "ویرایش محتوا از پنل CMS",
          }),
        });
      }
      return apiFetch("/api/v1/cms/articles", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          ...artForm,
          category_id: artForm.category_id || null,
        }),
      });
    },
    onSuccess: () => {
      setArticleOpen(false);
      setEditingArticleId(null);
      setArtForm(emptyArtForm);
      toast.success(editingArticleId ? "تغییرات مقاله ذخیره شد." : "مقاله در وضعیت پیش‌نویس ثبت شد.");
      qc.invalidateQueries({ queryKey: ["cms-articles"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteArtMut = useMutation({
    mutationFn: async (id: string) =>
      apiFetch(`/api/v1/cms/articles/${id}`, {
        method: "DELETE",
        token: accessToken,
      }),
    onSuccess: () => {
      toast.success("محتوا با موفقیت حذف شد.");
      qc.invalidateQueries({ queryKey: ["cms-articles"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rewriteArtMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<{ title: string; summary: string; content_body: string }>("/api/v1/ai/content/rewrite", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({
            title: artForm.title,
            content_body: artForm.content_body || artForm.summary || artForm.title,
            instruction: "بازنویسی حرفه‌ای، خوانا و بهینه برای سئو",
            tone: artForm.tone || "PROFESSIONAL",
            language: artForm.language || "fa",
          }),
        })
      ).data,
    onSuccess: (d) => {
      setArtForm((prev) => ({
        ...prev,
        title: d.title || prev.title,
        summary: d.summary || prev.summary,
        content_body: d.content_body || prev.content_body,
      }));
      toast.success("متن با هوش مصنوعی بازنویسی شد.");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const statusArtMut = useMutation({
    mutationFn: async ({ id, status, scheduled_for }: { id: string; status: string; scheduled_for?: string }) =>
      apiFetch(`/api/v1/cms/articles/${id}/status`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ status, scheduled_for: scheduled_for || null }),
      }),
    onSuccess: () => {
      setScheduleTarget(null);
      setScheduledFor("");
      toast.success("وضعیت گردش کار مقاله به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["cms-articles"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const aiSeoMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<{ meta_title: string; meta_description: string; suggested_slug: string }>("/api/v1/ai/seo-draft", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({
            title: artForm.title,
            body_excerpt: artForm.summary || artForm.content_body.slice(0, 220),
            target_city: "تهران",
          }),
        })
      ).data,
    onSuccess: (d) => {
      setArtForm((prev) => ({
        ...prev,
        meta_title: d.meta_title,
        meta_description: d.meta_description,
        slug: prev.slug || d.suggested_slug,
      }));
      toast.success("پیشنهاد متای سئو در فیلدهای قابل ویرایش درج شد (بدون انتشار خودکار).");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rssMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<RssTopicsResult>("/api/v1/ai/rss-topics", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({ feed_url: rssUrl.trim() || null }),
        })
      ).data,
    onSuccess: (d) => {
      setRssResult(d);
      toast.success("ایده‌های موضوعی بازار مسکن آماده شدند.");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const createRedirMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/seo/redirects", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(redirForm),
      }),
    onSuccess: () => {
      setRedirectOpen(false);
      setRedirForm({ from_path: "", to_path: "/properties", status_code: 301 });
      toast.success("قانون ریدایرکت ثبت شد.");
      qc.invalidateQueries({ queryKey: ["cms-redirects"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const coopMut = useMutation({
    mutationFn: async ({ id, decision }: { id: string; decision: string }) =>
      apiFetch<{ approved_agency_id: string | null }>(`/api/v1/cms/cooperation-requests/${id}/review`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ decision }),
      }),
    onSuccess: (res) => {
      toast.success(
        res.data.approved_agency_id
          ? "درخواست همکاری تایید و آژانس جدید با موفقیت در سامانه ایجاد شد."
          : "وضعیت درخواست همکاری به‌روزرسانی شد."
      );
      qc.invalidateQueries({ queryKey: ["cms-cooperation"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const inquiryMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/cms/contact-inquiries/${id}`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ status, staff_response: inquiryReply }),
      }),
    onSuccess: () => {
      setActiveInquiry(null);
      setInquiryReply("");
      toast.success("پاسخ درخواست ثبت شد.");
      qc.invalidateQueries({ queryKey: ["cms-inquiries"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="مدیریت محتوا (CMS)، سئو و صف درخواست‌های عمومی"
        subtitle="گردش کار تحریریه مجله و اخبار، مدیریت متادیتا و ریدایرکت ۳۰۱/۳۰۲ و بررسی درخواست‌های همکاری آژانس‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "CMS و سئو" }]}
        actions={
          <div className="flex flex-wrap gap-2">
            {isSuper && tab === "redirects" && (
              <button
                type="button"
                onClick={() => setRedirectOpen(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <Plus className="h-4 w-4" />
                ریدایرکت جدید
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                setEditingArticleId(null);
                setArtForm(emptyArtForm);
                setArticleOpen(true);
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Plus className="h-4 w-4" />
              مقاله / محتوای جدید
            </button>
          </div>
        }
      />

      <div className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        {[
          { key: "articles" as const, label: "مقالات و اخبار", icon: <FileText className="h-4 w-4" /> },
          { key: "redirects" as const, label: "ریدایرکت‌های سئو", icon: <Globe className="h-4 w-4" /> },
          ...(isSuper
            ? [
                { key: "cooperation" as const, label: "درخواست همکاری آژانس‌ها", icon: <Building2 className="h-4 w-4" /> },
                { key: "inquiries" as const, label: "درخواست‌های تماس عمومی", icon: <Mail className="h-4 w-4" /> },
              ]
            : []),
        ].map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-3.5 text-xs font-semibold transition-colors ${
              tab === item.key
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
            }`}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>

      {tab === "articles" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-slate-100">
                <Rss className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                ایده‌پرداز هوشمند موضوعات مجله و خبر (RSS / روند بازار)
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  dir="ltr"
                  placeholder="آدرس فید HTTPS اختیاری..."
                  value={rssUrl}
                  onChange={(e) => setRssUrl(e.target.value)}
                  className="h-9 w-64 rounded-lg border border-slate-300 bg-white px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                />
                <button
                  type="button"
                  disabled={rssMut.isPending}
                  onClick={() => rssMut.mutate()}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-teal-700 px-3 text-xs font-semibold text-teal-700 hover:bg-teal-50 dark:border-teal-500 dark:text-teal-400 dark:hover:bg-teal-950/50 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {rssMut.isPending ? "در حال دریافت..." : "دریافت ایده‌های موضوعی"}
                </button>
              </div>
            </div>

            {rssResult && rssResult.topics.length > 0 && (
              <div className="grid grid-cols-1 gap-2.5 pt-2 md:grid-cols-3">
                {rssResult.topics.map((topic, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/50"
                  >
                    <div className="space-y-1">
                      <div className="font-bold text-slate-900 dark:text-slate-100">
                        {topic.title}
                      </div>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400">
                        {topic.angle}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setArtForm((prev) => ({
                          ...prev,
                          title: topic.title,
                          summary: topic.angle,
                        }));
                        setArticleOpen(true);
                      }}
                      className="mt-3 h-8 rounded-md bg-teal-700 text-[11px] font-semibold text-white hover:bg-teal-800"
                    >
                      استفاده در مقاله جدید
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <DataTable
          rows={articlesQ.data || []}
          rowKey={(a) => a.id}
          isLoading={articlesQ.isLoading}
          error={articlesQ.error instanceof Error ? articlesQ.error.message : null}
          onRetry={() => articlesQ.refetch()}
          searchPlaceholder="جستجو در عنوان یا اسلاگ مقاله..."
          exportFileName="cms-articles"
          columns={[
            {
              key: "title",
              header: "عنوان و اسلاگ",
              render: (a) => (
                <div>
                  <div className="font-semibold text-slate-900 dark:text-slate-100">{a.title}</div>
                  <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                    /{a.slug} • {a.article_type}
                  </div>
                </div>
              ),
            },
            { key: "cat", header: "دسته‌بندی", render: (a) => a.category?.name || "عمومی" },
            { key: "status", header: "وضعیت", render: (a) => <StatusText status={a.status} /> },
            { key: "views", header: "بازدید", render: (a) => <span className="font-mono">{formatNumberFa(a.view_count)}</span> },
            { key: "dt", header: "ایجاد", render: (a) => <DateDisplay value={a.created_at} /> },
            {
              key: "act",
              header: "گردش کار و عملیات",
              render: (a) => (
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingArticleId(a.id);
                      setArtForm({
                        title: a.title,
                        slug: a.slug,
                        article_type: a.article_type,
                        category_id: a.category?.id || "",
                        summary: a.summary || "",
                        content_body: a.content_body || "",
                        cover_image_url: a.cover_image_url || "/images/prop-zafaranieh.jpg",
                        language: a.language || "fa",
                        tone: a.tone || "PROFESSIONAL",
                        target_audience: a.target_audience || "",
                        meta_title: a.meta_title || "",
                        meta_description: a.meta_description || "",
                      });
                      setArticleOpen(true);
                    }}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-semibold"
                  >
                    <Edit3 className="h-3 w-3" />
                    ویرایش
                  </button>
                  {a.status === "DRAFT" && (
                    <button
                      type="button"
                      onClick={() => statusArtMut.mutate({ id: a.id, status: "REVIEW" })}
                      className="rounded-md bg-amber-600 px-2.5 py-1 text-xs font-semibold text-white"
                    >
                      ارسال به بازبینی
                    </button>
                  )}
                  {a.status === "REVIEW" && (
                    <button
                      type="button"
                      onClick={() => statusArtMut.mutate({ id: a.id, status: "DRAFT" })}
                      className="rounded-md border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-semibold"
                    >
                      بازگشت به پیش‌نویس
                    </button>
                  )}
                  {isSuper && a.status === "REVIEW" && (
                    <button
                      type="button"
                      onClick={() => statusArtMut.mutate({ id: a.id, status: "APPROVED" })}
                      className="rounded-md bg-indigo-700 px-2.5 py-1 text-xs font-semibold text-white"
                    >
                      تایید نهایی
                    </button>
                  )}
                  {isSuper && (a.status === "APPROVED" || a.status === "SCHEDULED") && (
                    <>
                      <button
                        type="button"
                        onClick={() => statusArtMut.mutate({ id: a.id, status: "PUBLISHED" })}
                        className="rounded-md bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white"
                      >
                        انتشار در پورتال
                      </button>
                      <button
                        type="button"
                        onClick={() => setScheduleTarget(a)}
                        className="rounded-md border border-teal-700 px-2 py-1 text-xs font-semibold text-teal-700 dark:text-teal-400"
                      >
                        زمان‌بندی
                      </button>
                    </>
                  )}
                  {isSuper && a.status === "PUBLISHED" && (
                    <button
                      type="button"
                      onClick={() => statusArtMut.mutate({ id: a.id, status: "ARCHIVED" })}
                      className="rounded-md border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-semibold"
                    >
                      بایگانی
                    </button>
                  )}
                  {a.status === "PUBLISHED" && (
                    <Link
                      href={`/blog/${a.slug}`}
                      className="inline-flex items-center gap-1 rounded-md border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-semibold text-teal-700 dark:text-teal-400"
                    >
                      مشاهده
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                  {(a.status !== "PUBLISHED" || isSuper) && (
                    <button
                      type="button"
                      onClick={() => deleteArtMut.mutate(a.id)}
                      className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                      title="حذف"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
        </div>
      )}

      {tab === "redirects" && (
        <DataTable
          rows={redirectsQ.data || []}
          rowKey={(r) => r.id}
          isLoading={redirectsQ.isLoading}
          searchPlaceholder="جستجوی مسیر ریدایرکت..."
          exportFileName="seo-redirects"
          columns={[
            { key: "from", header: "مسیر مبدأ", render: (r) => <span className="font-mono text-xs" dir="ltr">{r.from_path}</span> },
            { key: "to", header: "مسیر مقصد", render: (r) => <span className="font-mono text-xs text-teal-700 dark:text-teal-400" dir="ltr">{r.to_path}</span> },
            { key: "code", header: "کد HTTP", render: (r) => <span className="font-mono font-bold">{r.status_code}</span> },
            { key: "act", header: "وضعیت", render: (r) => <StatusText status={r.is_active ? "ACTIVE" : "SUSPENDED"} /> },
          ]}
        />
      )}

      {tab === "cooperation" && isSuper && (
        <DataTable
          rows={coopQ.data || []}
          rowKey={(c) => c.id}
          isLoading={coopQ.isLoading}
          searchPlaceholder="جستجوی نام آژانس یا کد رهگیری..."
          exportFileName="agency-cooperation"
          columns={[
            { key: "code", header: "کد رهگیری", render: (c) => <span className="font-mono text-xs font-bold">{c.tracking_code}</span> },
            { key: "name", header: "نام آژانس و شهر", render: (c) => `${c.agency_name} (${c.city})` },
            { key: "mgr", header: "مدیر و تماس", render: (c) => `${c.manager_name} — ${c.manager_phone}` },
            { key: "cnt", header: "مشاوران", render: (c) => formatNumberFa(c.agents_count) },
            { key: "status", header: "وضعیت", render: (c) => <StatusText status={c.status} /> },
            {
              key: "act",
              header: "بررسی",
              render: (c) =>
                c.status !== "APPROVED" ? (
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      onClick={() => coopMut.mutate({ id: c.id, decision: "APPROVED" })}
                      className="inline-flex items-center gap-1 rounded-md bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      تایید و ساخت آژانس
                    </button>
                    <button
                      type="button"
                      onClick={() => coopMut.mutate({ id: c.id, decision: "REJECTED" })}
                      className="rounded-md bg-rose-700 px-2.5 py-1 text-xs font-semibold text-white"
                    >
                      رد
                    </button>
                  </div>
                ) : (
                  <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">آژانس فعال شد</span>
                ),
            },
          ]}
        />
      )}

      {tab === "inquiries" && isSuper && (
        <DataTable
          rows={inquiriesQ.data || []}
          rowKey={(i) => i.id}
          isLoading={inquiriesQ.isLoading}
          searchPlaceholder="جستجو در کد رهگیری یا موضوع..."
          exportFileName="contact-inquiries"
          columns={[
            { key: "code", header: "کد رهگیری", render: (i) => <span className="font-mono text-xs font-bold">{i.tracking_code}</span> },
            { key: "name", header: "نام و موبایل", render: (i) => `${i.full_name} (${i.phone_number})` },
            { key: "subject", header: "موضوع", render: (i) => i.subject },
            { key: "status", header: "وضعیت", render: (i) => <StatusText status={i.status} /> },
            { key: "dt", header: "ثبت", render: (i) => <DateDisplay value={i.created_at} /> },
            {
              key: "act",
              header: "پاسخگویی",
              render: (i) => (
                <button
                  type="button"
                  onClick={() => {
                    setActiveInquiry(i);
                    setInquiryReply(i.staff_response || "");
                  }}
                  className="rounded-md border border-slate-300 dark:border-slate-700 px-2.5 py-1 text-xs font-semibold"
                >
                  پاسخ و تغییر وضعیت
                </button>
              ),
            },
          ]}
        />
      )}

      <ModalDrawer
        open={articleOpen}
        onClose={() => {
          setArticleOpen(false);
          setEditingArticleId(null);
        }}
        title={editingArticleId ? "ویرایش مقاله / محتوا" : "ایجاد مقاله یا محتوای جدید"}
        widthClass="max-w-2xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveArtMut.mutate();
          }}
          className="space-y-3"
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              required
              placeholder="عنوان مقاله یا خبر..."
              value={artForm.title}
              onChange={(e) => setArtForm({ ...artForm, title: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm text-slate-900 dark:text-slate-100"
            />
            <input
              required
              disabled={!!editingArticleId}
              dir="ltr"
              placeholder="article-slug-en"
              value={artForm.slug}
              onChange={(e) => setArtForm({ ...artForm, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm text-slate-900 dark:text-slate-100 disabled:opacity-60"
            />
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <select
              value={artForm.article_type}
              onChange={(e) => setArtForm({ ...artForm, article_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            >
              <option value="ARTICLE">مقاله تخصصی</option>
              <option value="EDUCATIONAL">محتوای آموزشی</option>
              <option value="NEWS">خبر و گزارش بازار</option>
              <option value="PROMOTIONAL">تبلیغاتی</option>
              <option value="SEO">سئو</option>
              <option value="SOCIAL_MEDIA">شبکه‌های اجتماعی</option>
              <option value="LISTING_DESCRIPTION">توضیحات آگهی</option>
            </select>
            <select
              value={artForm.language}
              onChange={(e) => setArtForm({ ...artForm, language: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            >
              <option value="fa">فارسی</option>
              <option value="en">انگلیسی</option>
              <option value="ar">عربی</option>
            </select>
            <select
              value={artForm.category_id}
              onChange={(e) => setArtForm({ ...artForm, category_id: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            >
              <option value="">انتخاب دسته‌بندی...</option>
              {(categoriesQ.data || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <input
            placeholder="چکیده کوتاه مقاله..."
            value={artForm.summary}
            onChange={(e) => setArtForm({ ...artForm, summary: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
          />

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">متن کامل محتوا</span>
              <button
                type="button"
                disabled={rewriteArtMut.isPending || (!artForm.content_body.trim() && !artForm.title.trim())}
                onClick={() => rewriteArtMut.mutate()}
                className="inline-flex h-7 items-center gap-1 rounded-md border border-teal-700 px-2.5 text-[11px] font-semibold text-teal-700 dark:text-teal-400 disabled:opacity-50"
              >
                <Sparkles className="h-3 w-3" />
                {rewriteArtMut.isPending ? "در حال بازنویسی..." : "بازنویسی با AI"}
              </button>
            </div>
            <textarea
              required
              rows={6}
              placeholder="متن کامل مقاله یا گزارش تحلیلی..."
              value={artForm.content_body}
              onChange={(e) => setArtForm({ ...artForm, content_body: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-xs leading-relaxed text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 dark:text-slate-200">تنظیمات سئو (قابل ویرایش)</span>
              <button
                type="button"
                disabled={!artForm.title.trim() || aiSeoMut.isPending}
                onClick={() => aiSeoMut.mutate()}
                className="inline-flex h-8 items-center gap-1.5 rounded-md border border-teal-700 px-2.5 text-xs font-semibold text-teal-700 dark:text-teal-400 disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                پیشنهاد هوشمند سئو
              </button>
            </div>
            <input
              placeholder="Meta Title"
              value={artForm.meta_title}
              onChange={(e) => setArtForm({ ...artForm, meta_title: e.target.value })}
              className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
            />
            <textarea
              rows={2}
              placeholder="Meta Description"
              value={artForm.meta_description}
              onChange={(e) => setArtForm({ ...artForm, meta_description: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>

          <button type="submit" disabled={saveArtMut.isPending} className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            {editingArticleId ? "ذخیره تغییرات مقاله" : "ثبت پیش‌نویس مقاله"}
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={!!scheduleTarget} onClose={() => setScheduleTarget(null)} title="زمان‌بندی انتشار مقاله">
        {scheduleTarget && (
          <div className="space-y-3 text-xs">
            <div className="font-bold">{scheduleTarget.title}</div>
            <input
              type="datetime-local"
              dir="ltr"
              value={scheduledFor}
              onChange={(e) => setScheduledFor(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-xs"
            />
            <button
              type="button"
              disabled={!scheduledFor || statusArtMut.isPending}
              onClick={() =>
                statusArtMut.mutate({
                  id: scheduleTarget.id,
                  status: "SCHEDULED",
                  scheduled_for: new Date(scheduledFor).toISOString(),
                })
              }
              className="h-10 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white disabled:opacity-50"
            >
              تثبیت زمان انتشار
            </button>
          </div>
        )}
      </ModalDrawer>

      <ModalDrawer open={redirectOpen} onClose={() => setRedirectOpen(false)} title="ثبت ریدایرکت ۳۰۱/۳۰۲">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createRedirMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            dir="ltr"
            placeholder="/old-path"
            value={redirForm.from_path}
            onChange={(e) => setRedirForm({ ...redirForm, from_path: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-xs text-slate-900 dark:text-slate-100"
          />
          <input
            required
            dir="ltr"
            placeholder="/new-path"
            value={redirForm.to_path}
            onChange={(e) => setRedirForm({ ...redirForm, to_path: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-xs text-slate-900 dark:text-slate-100"
          />
          <select
            value={redirForm.status_code}
            onChange={(e) => setRedirForm({ ...redirForm, status_code: Number(e.target.value) })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs text-slate-900 dark:text-slate-100"
          >
            <option value={301}>301 — انتقال دائمی (Permanent)</option>
            <option value={302}>302 — انتقال موقت (Temporary)</option>
          </select>
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ذخیره ریدایرکت
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={!!activeInquiry} onClose={() => setActiveInquiry(null)} title={activeInquiry ? `درخواست ${activeInquiry.tracking_code}` : ""}>
        {activeInquiry && (
          <div className="space-y-3 text-xs">
            <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3 space-y-1">
              <div className="font-bold text-slate-900 dark:text-slate-100">{activeInquiry.subject}</div>
              <p className="text-slate-700 dark:text-slate-300">{activeInquiry.message}</p>
            </div>
            <textarea
              rows={3}
              placeholder="پاسخ رسمی کارشناس (قابل مشاهده با کد رهگیری)..."
              value={inquiryReply}
              onChange={(e) => setInquiryReply(e.target.value)}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-xs text-slate-900 dark:text-slate-100"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => inquiryMut.mutate({ id: activeInquiry.id, status: "IN_PROGRESS" })}
                className="h-9 flex-1 rounded-lg bg-amber-600 font-semibold text-white"
              >
                در حال پیگیری
              </button>
              <button
                type="button"
                onClick={() => inquiryMut.mutate({ id: activeInquiry.id, status: "RESOLVED" })}
                className="h-9 flex-1 rounded-lg bg-emerald-700 font-semibold text-white"
              >
                پاسخ‌داده‌شده / حل‌شده
              </button>
            </div>
          </div>
        )}
      </ModalDrawer>
    </div>
  );
}
