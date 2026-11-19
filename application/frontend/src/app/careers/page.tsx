// Path: frontend/src/app/careers/page.tsx

"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Briefcase, MapPin } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { PublicHeader } from "@/components/layout/PublicHeader";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

interface JobItem {
  id: string;
  title: string;
  department: string;
  location: string;
  employment_type: string;
  description: string;
}

export default function CareersPage() {
  const jobsQ = useQuery({
    queryKey: ["public-jobs"],
    queryFn: async () => (await apiFetch<JobItem[]>("/api/v1/cms/public/jobs")).data,
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <PublicHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12 sm:px-6 lg:px-8 space-y-8">
        <div className="space-y-2">
          <div className="text-xs font-bold text-teal-700 dark:text-teal-400">فرصت‌های شغلی بنیان ملک</div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">همکاری با تیم مهندسی و عملیات</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            موقعیت‌های شغلی فعال برای ساخت زیرساخت مدرن فناوری املاک
          </p>
        </div>

        {jobsQ.isLoading ? (
          <LoadingState message="در حال دریافت فرصت‌های شغلی..." />
        ) : jobsQ.error ? (
          <ErrorState
            message={jobsQ.error instanceof Error ? jobsQ.error.message : "خطا در دریافت فرصت‌های شغلی"}
            onRetry={() => jobsQ.refetch()}
          />
        ) : (
          <div className="space-y-4">
            {(jobsQ.data || []).map((job) => (
              <div
                key={job.id}
                className="flex flex-col justify-between gap-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:flex-row sm:items-center"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-3 text-xs text-teal-700 dark:text-teal-400 font-semibold">
                    <span className="flex items-center gap-1">
                      <Briefcase className="h-3.5 w-3.5" />
                      {job.department}
                    </span>
                    <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                      <MapPin className="h-3.5 w-3.5" />
                      {job.location} • {job.employment_type}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">{job.title}</h2>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{job.description}</p>
                </div>
                <Link
                  href="/contact"
                  className="inline-flex h-9 shrink-0 items-center justify-center rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800"
                >
                  ارسال رزومه و معرفی
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
