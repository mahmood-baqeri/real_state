"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Clock, Search } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
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
  author: { display_name: string; role_title: string } | null;
  summary: string;
  cover_image_url: string;
  reading_time_minutes: number;
  published_at: string | null;
}

export default function BlogIndexPage() {
  const [selectedCat, setSelectedCat] = useState("");
  const [articleType, setArticleType] = useState("");
  const [q, setQ] = useState("");

  const catsQ = useQuery({
    queryKey: ["public-blog-categories"],
    queryFn: async () => (await apiFetch<CmsCategory[]>("/api/v1/cms/public/categories")).data,
  });

  const articlesQ = useQuery({
    queryKey: ["public-blog-articles", selectedCat, articleType, q],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedCat) params.set("category", selectedCat);
      if (articleType) params.set("article_type", articleType);
      if (q) params.set("q", q);
      return (await apiFetch<CmsArticle[]>(`/api/v1/cms/public/articles?${params.toString()}`)).data;
    },
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-teal-700 dark:text-teal-400">
              <BookOpen className="h-4 w-4" />
              مجله، اخبار و تحلیل بازار مسکن
            </div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">مجله تخصصی بنیان ملک</h1>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              گزارش‌های تحلیلی قیمت مسکن، نکات حقوقی تنظیم قراردادها و راهکارهای مدیریت آژانس
            </p>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-400" />
            <input
              placeholder="جستجو در مقالات و اخبار..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 pr-9 pl-3 text-xs text-slate-900 dark:text-slate-100"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setSelectedCat("")}
            className={`h-8 rounded-lg border px-3 text-xs font-semibold ${
              selectedCat === ""
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
            }`}
          >
            همه موضوعات
          </button>
          {(catsQ.data || []).map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setSelectedCat(c.slug)}
              className={`h-8 rounded-lg border px-3 text-xs font-semibold ${
                selectedCat === c.slug
                  ? "border-teal-700 bg-teal-700 text-white"
                  : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
              }`}
            >
              {c.name}
            </button>
          ))}
          <select
            value={articleType}
            onChange={(e) => setArticleType(e.target.value)}
            aria-label="نوع مطلب"
            className="h-8 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-2.5 text-xs text-slate-700 dark:text-slate-300"
          >
            <option value="">مقاله و خبر</option>
            <option value="ARTICLE">فقط مقالات آموزشی</option>
            <option value="NEWS">فقط اخبار و گزارش بازار</option>
          </select>
        </div>

        {articlesQ.isLoading ? (
          <LoadingState message="در حال بارگذاری مقالات و اخبار..." />
        ) : articlesQ.error ? (
          <ErrorState
            message={articlesQ.error instanceof Error ? articlesQ.error.message : "خطا در بارگذاری مجله"}
            onRetry={() => articlesQ.refetch()}
          />
        ) : (articlesQ.data || []).length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-10 text-center text-sm text-slate-500">
            مطلبی در این دسته‌بندی یافت نشد.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {(articlesQ.data || []).map((a) => (
              <article
                key={a.id}
                className="flex flex-col overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 transition-shadow hover:shadow-md"
              >
                <Link href={`/blog/${a.slug}`} className="block aspect-[16/9] bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <img
                    src={a.cover_image_url || "/images/prop-zafaranieh.jpg"}
                    alt={a.title}
                    className="h-full w-full object-cover"
                  />
                </Link>
                <div className="flex flex-1 flex-col justify-between p-5 space-y-3">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      {a.category ? (
                        <Link
                          href={`/blog/category/${a.category.slug}`}
                          className="font-semibold text-teal-700 dark:text-teal-400 hover:underline"
                        >
                          {a.category.name}
                        </Link>
                      ) : (
                        <span className="text-slate-500">تحریریه</span>
                      )}
                      <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                        <Clock className="h-3 w-3" />
                        {formatNumberFa(a.reading_time_minutes)} دقیقه مطالعه
                      </span>
                    </div>
                    <Link href={`/blog/${a.slug}`}>
                      <h2 className="text-base font-bold leading-snug text-slate-900 dark:text-slate-100 hover:text-teal-700 dark:hover:text-teal-400">
                        {a.title}
                      </h2>
                    </Link>
                    <p className="line-clamp-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">{a.summary}</p>
                  </div>
                  <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 pt-3 text-[11px] text-slate-500 dark:text-slate-400">
                    <span>{a.author?.display_name || "تحریریه بنیان ملک"}</span>
                    <DateDisplay value={a.published_at} />
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
