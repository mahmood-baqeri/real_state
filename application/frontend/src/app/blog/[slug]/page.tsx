import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, Clock, Eye, User } from "lucide-react";
import { buildArticleJsonLd, getApiOrigin } from "@/lib/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { formatLocalizedDate, formatNumberFa } from "@/lib/formatters";

export const dynamic = "force-dynamic";

interface ArticleDetail {
  id: string;
  title: string;
  slug: string;
  article_type: string;
  category: { id: string; name: string; slug: string } | null;
  author: { display_name: string; role_title: string } | null;
  summary: string;
  content_body: string;
  cover_image_url: string;
  published_at: string | null;
  meta_title: string;
  meta_description: string;
  canonical_url: string;
  reading_time_minutes: number;
  view_count: number;
  tags: { name: string; slug: string }[];
}

async function fetchArticle(slug: string): Promise<ArticleDetail | null> {
  try {
    const res = await fetch(`${getApiOrigin()}/api/v1/cms/public/articles/${encodeURIComponent(slug)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json?.data || null;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const art = await fetchArticle(slug);
  if (!art) return { title: "مقاله یافت نشد" };
  return {
    title: art.meta_title || art.title,
    description: art.meta_description || art.summary,
    alternates: art.canonical_url ? { canonical: art.canonical_url } : undefined,
    openGraph: {
      title: art.meta_title || art.title,
      description: art.meta_description || art.summary,
      type: "article",
    },
  };
}

export default async function BlogArticleDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = await fetchArticle(slug);
  if (!article) {
    notFound();
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <JsonLd data={buildArticleJsonLd(article)} />
      <PublicHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-10 sm:px-6 space-y-6">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <Link href="/blog" className="inline-flex items-center gap-1 font-semibold text-teal-700 dark:text-teal-400 hover:underline">
            <ArrowRight className="h-3.5 w-3.5" />
            مجله بنیان ملک
          </Link>
          {article.category && (
            <>
              <span>/</span>
              <Link href={`/blog/category/${article.category.slug}`} className="hover:underline">
                {article.category.name}
              </Link>
            </>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
          {article.cover_image_url && (
            <div className="aspect-[16/9] w-full bg-slate-100 dark:bg-slate-800">
              <img src={article.cover_image_url} alt={article.title} className="h-full w-full object-cover" />
            </div>
          )}
          <div className="p-6 sm:p-10 space-y-6">
            <div className="space-y-3 border-b border-slate-100 dark:border-slate-800 pb-6">
              <h1 className="text-2xl sm:text-3xl font-bold leading-snug text-slate-900 dark:text-slate-100">
                {article.title}
              </h1>
              {article.summary && (
                <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">{article.summary}</p>
              )}
              <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                  {article.author?.display_name || "تحریریه بنیان ملک"}
                </span>
                <span className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  {formatNumberFa(article.reading_time_minutes)} دقیقه مطالعه
                </span>
                <span className="flex items-center gap-1.5">
                  <Eye className="h-3.5 w-3.5" />
                  {formatNumberFa(article.view_count)} بازدید
                </span>
                {article.published_at && <span>{formatLocalizedDate(article.published_at, "jalali")}</span>}
              </div>
            </div>

            <div className="space-y-4 text-sm leading-8 text-slate-800 dark:text-slate-200 whitespace-pre-line">
              {article.content_body}
            </div>

            {article.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 border-t border-slate-100 dark:border-slate-800 pt-5">
                {article.tags.map((t) => (
                  <span
                    key={t.slug}
                    className="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2.5 py-1 text-xs text-slate-700 dark:text-slate-300"
                  >
                    #{t.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        </article>
      </main>
      <PublicFooter />
    </div>
  );
}
