import React from "react";
import Link from "next/link";
import { ArrowRight, Compass } from "lucide-react";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { PublicPropertyVirtualTour } from "@/components/virtual-tour/PublicPropertyVirtualTour";

export default async function PublicVirtualTourPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto max-w-7xl space-y-5 px-4 py-8 sm:px-6 lg:px-8">
        <Link href="/properties" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-teal-700 dark:text-slate-300">
          <ArrowRight className="h-4 w-4" /> بازگشت به املاک
        </Link>
        <div className="flex items-center gap-2">
          <Compass className="h-5 w-5 text-teal-700" />
          <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">مشاهده تور مجازی ملک</h1>
        </div>
        <PublicPropertyVirtualTour publicSlug={slug} />
      </main>
      <PublicFooter />
    </div>
  );
}
