"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

interface CmsArticle {
  id: string;
  title: string;
  slug: string;
  summary: string;
  cover_image_url: string;
  published_at: string | null;
  category: { name: string; slug: string } | null;
}

export default function BlogCategoryPage() {
  const params = useParams();
  const slug = String(params?.slug || "");

  const articlesQ = useQuery({
    queryKey: ["public-blog-cat", slug],
    enabled: !!slug,
    queryFn: async () => (await apiFetch<CmsArticle[]>(`/api/v1/cms/public/articles?category=${encodeURIComponent(slug)}`)).data,
  });

  const catTitle = articlesQ.data?.[0]?.category?.name || slug;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-8">
        <div className="space-y-2">
          <Link href="/blog" className="inline-flex items-center gap-1 text-xs font-semibold text-teal-700 dark:text-teal-400 hover:underline">
            <ArrowRight className="h-3.5 w-3.5" />
            بازگشت به مجله
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">دسته‌بندی: {catTitle}</h1>
        </div>

        {articlesQ.isLoading ? (
          <LoadingState message="در حال دریافت مطالب دسته‌بندی..." />
        ) : articlesQ.error ? (
          <ErrorState
            message={articlesQ.error instanceof Error ? articlesQ.error.message : "خطا در دریافت مطالب"}
            onRetry={() => articlesQ.refetch()}
          />
        ) : (articlesQ.data || []).length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-10 text-center text-sm text-slate-500">
            مطلبی در این دسته‌بندی منتشر نشده است.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {(articlesQ.data || []).map((a) => (
              <Link
                key={a.id}
                href={`/blog/${a.slug}`}
                className="flex flex-col overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:shadow-md"
              >
                <img
                  src={a.cover_image_url || "/images/prop-zafaranieh.jpg"}
                  alt={a.title}
                  className="aspect-[16/9] w-full object-cover"
                />
                <div className="p-5 space-y-2">
                  <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">{a.title}</h2>
                  <p className="line-clamp-2 text-xs text-slate-600 dark:text-slate-400">{a.summary}</p>
                  <div className="pt-2 text-[11px] text-slate-500">
                    <DateDisplay value={a.published_at} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
