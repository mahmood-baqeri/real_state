// Path: frontend/src/app/dashboard/agencies/[id]/page.tsx

"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Building2, ShieldCheck, Users } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AgencyAccessPolicy, AgencyItem, BranchItem, TeamMemberItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { formatNumberFa } from "@/lib/formatters";

export default function AgencyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { accessToken } = useAuth();

  const agencyQ = useQuery({
    queryKey: ["agency-detail", id],
    enabled: !!accessToken && !!id,
    queryFn: async () => (await apiFetch<AgencyItem>(`/api/v1/agencies/${id}`, { token: accessToken })).data,
  });

  const branchesQ = useQuery({
    queryKey: ["agency-branches-detail", id],
    enabled: !!accessToken && !!id,
    queryFn: async () => (await apiFetch<BranchItem[]>(`/api/v1/agencies/${id}/branches`, { token: accessToken })).data,
  });

  const membersQ = useQuery({
    queryKey: ["agency-members-detail", id],
    enabled: !!accessToken && !!id,
    queryFn: async () => (await apiFetch<TeamMemberItem[]>(`/api/v1/agencies/${id}/members`, { token: accessToken })).data,
  });

  const policyQ = useQuery({
    queryKey: ["agency-policy-detail", id],
    enabled: !!accessToken && !!id,
    queryFn: async () =>
      (await apiFetch<AgencyAccessPolicy>(`/api/v1/agencies/${id}/access-policy`, { token: accessToken })).data,
  });

  if (agencyQ.isLoading) return <LoadingState message="در حال بارگذاری پرونده آژانس..." />;
  if (agencyQ.error) return <ErrorState message={(agencyQ.error as Error).message} onRetry={() => agencyQ.refetch()} />;
  const agency = agencyQ.data;
  if (!agency) return <ErrorState message="آژانس یافت نشد." />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={agency.name}
        subtitle={`شناسه یکتا: ${agency.slug} — مدیر مسئول: ${agency.owner_name}`}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "آژانس‌ها و شعب", href: "/dashboard/agencies" },
          { label: agency.name },
        ]}
        actions={
          <Link
            href="/dashboard/agencies"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            <ArrowRight className="h-4 w-4" />
            بازگشت به فهرست
          </Link>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3 lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
              <Building2 className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              مشخصات حقوقی و بومی‌سازی آژانس
            </h2>
            <StatusText status={agency.status} />
          </div>
          <dl className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-3">
            <div>
              <dt className="text-slate-500 dark:text-slate-400">شماره ثبت</dt>
              <dd className="mt-1 font-mono font-semibold text-slate-900 dark:text-slate-100">{agency.registration_number || "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">شناسه مالیاتی</dt>
              <dd className="mt-1 font-mono font-semibold text-slate-900 dark:text-slate-100">{agency.tax_id || "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">شماره تماس</dt>
              <dd className="mt-1 font-mono font-semibold text-slate-900 dark:text-slate-100">{agency.phone || "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">کشور / ارز</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{agency.country} / {agency.default_currency}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">تقویم / واحد مساحت</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{agency.default_calendar} / {agency.area_unit}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">تاریخ ثبت</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100"><DateDisplay value={agency.created_at} /></dd>
            </div>
          </dl>
          {agency.description && (
            <p className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
              {agency.description}
            </p>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-3">
            <ShieldCheck className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            سیاست دسترسی و محرمانگی
          </h2>
          {policyQ.data ? (
            <dl className="space-y-2 text-xs">
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">مشاهده املاک:</dt>
                <dd className="font-mono font-semibold text-slate-900 dark:text-slate-100">{policyQ.data.property_view_scope}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">مشاهده مشتریان:</dt>
                <dd className="font-mono font-semibold text-slate-900 dark:text-slate-100">{policyQ.data.customer_view_scope}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">اطلاعات مالک (PII):</dt>
                <dd className="font-mono font-semibold text-slate-900 dark:text-slate-100">{policyQ.data.owner_pii_visibility}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">دسترسی مالی:</dt>
                <dd className="font-mono font-semibold text-slate-900 dark:text-slate-100">{policyQ.data.financial_visibility}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-xs text-slate-500 dark:text-slate-400">سیاست دسترسی فقط برای اعضای آژانس قابل مشاهده است.</p>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            شعب ثبت‌شده ({formatNumberFa((branchesQ.data || []).length)})
          </h3>
          {(branchesQ.data || []).length === 0 ? (
            <p className="text-xs text-slate-500 dark:text-slate-400">شعبه‌ای ثبت نشده است.</p>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
              {(branchesQ.data || []).map((b) => (
                <div key={b.id} className="py-2.5 flex items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100">{b.name}</div>
                    <div className="text-slate-500 dark:text-slate-400">{b.city} — {b.address || "بدون نشانی"}</div>
                  </div>
                  <span className="font-mono text-slate-600 dark:text-slate-400">{b.code}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
          <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            <Users className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            اعضای فعال ({formatNumberFa((membersQ.data || []).length)})
          </h3>
          {(membersQ.data || []).length === 0 ? (
            <p className="text-xs text-slate-500 dark:text-slate-400">اطلاعات اعضای تیم در دسترس نیست.</p>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
              {(membersQ.data || []).map((m) => (
                <div key={m.id} className="py-2.5 flex items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100">{m.full_name}</div>
                    <div className="text-slate-500 dark:text-slate-400">{m.role_name} {m.branch_name ? `— ${m.branch_name}` : ""}</div>
                  </div>
                  <StatusText status={m.status} />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
