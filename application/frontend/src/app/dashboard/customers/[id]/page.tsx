"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Mail, Phone, Share2, Target, User } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CustomerItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const { accessToken, activeAgencyId } = useAuth();

  const custQ = useQuery({
    queryKey: ["customer-detail", params.id, activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<CustomerItem>(`/api/v1/customers/${params.id}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const c = custQ.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title={c ? `پرونده مشتری: ${c.full_name}` : "پرونده ۳۶۰ درجه مشتری"}
        subtitle={c ? `کد نوع: ${c.customer_type} — امتیاز سرنخ: ${c.lead_score}` : undefined}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "مشتریان", href: "/dashboard/customers" },
          { label: c?.full_name || "پرونده" },
        ]}
        actions={
          <Link
            href="/dashboard/customers"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          >
            <ArrowRight className="h-4 w-4" />
            بازگشت به فهرست مشتریان
          </Link>
        }
      />

      {custQ.isLoading ? (
        <LoadingState />
      ) : custQ.error instanceof Error ? (
        <ErrorState message={custQ.error.message} onRetry={() => custQ.refetch()} />
      ) : c ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-5">
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <User className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                اطلاعات تماس و مسئولیت
              </h3>
              <dl className="space-y-3 text-xs">
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">شماره تماس:</dt>
                  <dd className="flex items-center gap-1 font-mono font-bold" dir="ltr">
                    <Phone className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                    {c.primary_phone}
                  </dd>
                </div>
                {c.email && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500 dark:text-slate-400">ایمیل:</dt>
                    <dd className="flex items-center gap-1 font-mono" dir="ltr">
                      <Mail className="h-3.5 w-3.5 text-slate-400" />
                      {c.email}
                    </dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">مشاور مسئول:</dt>
                  <dd className="font-semibold">{c.assigned_agent_name || "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">آمادگی خرید/اجاره:</dt>
                  <dd className="font-semibold">{c.readiness_level}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">تاریخ ثبت:</dt>
                  <dd>
                    <DateDisplay value={c.created_at} />
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Share2 className="h-4 w-4 text-amber-600" />
                دسترسی اشتراکی همکاران
              </h3>
              {c.shares.length === 0 ? (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  این پرونده فقط در اختیار مشاور مسئول (خصوصی) است.
                </p>
              ) : (
                <div className="space-y-2 text-xs">
                  {c.shares.map((s) => (
                    <div
                      key={s.id}
                      className="flex justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-800/60"
                    >
                      <span className="font-semibold">{s.agent_name}</span>
                      <span className="font-mono text-slate-500">{s.access_level}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6 lg:col-span-7">
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Target className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                نیازها و تقاضاهای ملکی ثبت‌شده
              </h3>
              {c.requirements.length === 0 ? (
                <p className="py-6 text-center text-xs text-slate-500 dark:text-slate-400">
                  هنوز تقاضای ملکی برای این مشتری ثبت نشده است.
                </p>
              ) : (
                <div className="space-y-3">
                  {c.requirements.map((req) => (
                    <div
                      key={req.id}
                      className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-800/60"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 font-bold text-slate-900 dark:text-slate-100">
                        <span>
                          {req.deal_type} · {req.property_type} در {req.target_city}
                        </span>
                        <span>حداقل {req.min_bedrooms} خواب</span>
                      </div>
                      <div className="mt-2 text-slate-600 dark:text-slate-300">
                        مناطق: {req.target_districts?.join("، ") || "همه مناطق"} | متراژ:{" "}
                        {req.min_area_sqm} تا {req.max_area_sqm} متر
                      </div>
                      <div className="mt-2 flex gap-4 font-semibold text-teal-800 dark:text-teal-300">
                        <span>
                          حداقل بودجه: <MoneyDisplay amount={req.min_budget} />
                        </span>
                        <span>
                          حداکثر بودجه: <MoneyDisplay amount={req.max_budget} />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
