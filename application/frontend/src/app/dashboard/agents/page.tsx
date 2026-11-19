"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Award } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa } from "@/lib/formatters";
import type { TeamMemberItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { HorizontalBarChart } from "@/components/ui/AnalyticsCharts";
import { StatusText } from "@/components/ui/StatusText";

interface AnalyticsResp {
  agent_leaderboard: {
    membership_id: string;
    agent_name: string;
    total_commission: string;
    deals_count: number;
  }[];
}

export default function AgentsDirectoryPage() {
  const { accessToken, activeAgencyId } = useAuth();

  const membersQ = useQuery({
    queryKey: ["team-members", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<TeamMemberItem[]>("/api/v1/team/members", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const analyticsQ = useQuery({
    queryKey: ["agent-analytics", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<AnalyticsResp>("/api/v1/reports/analytics", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const agents = (membersQ.data || []).filter(
    (m) => m.role_code === "REAL_ESTATE_AGENT" || m.role_code === "AGENCY_MANAGER"
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="مشاوران املاک و عملکرد فروش"
        subtitle="فهرست مشاوران فعال آژانس و جدول رتبه‌بندی پورسانت"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "مشاوران املاک" }]}
        actions={
          <Link
            href="/dashboard/team"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            <Award className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            مدیریت تیم و نقش‌ها
          </Link>
        }
      />

      <HorizontalBarChart
        title="رتبه‌بندی عملکرد مالی مشاوران"
        subtitle="مجموع سهم کمیسیون ثبت‌شده به تفکیک مشاور (تومان)"
        items={(analyticsQ.data?.agent_leaderboard || []).map((a) => ({
          label: a.agent_name,
          value: Number(a.total_commission || 0),
          secondary: `${formatNumberFa(a.deals_count)} معامله`,
        }))}
        unitLabel="تومان"
      />

      <DataTable
        rows={agents}
        rowKey={(a) => a.id}
        isLoading={membersQ.isLoading}
        error={membersQ.error instanceof Error ? membersQ.error.message : null}
        searchPlaceholder="جستجو در نام یا شعبه مشاور..."
        columns={[
          { key: "name", header: "نام مشاور", render: (a) => <span className="font-semibold">{a.full_name}</span> },
          { key: "phone", header: "تلفن", render: (a) => <span className="font-mono text-xs">{a.phone_number}</span> },
          { key: "role", header: "سمت", render: (a) => a.role_name },
          { key: "branch", header: "شعبه", render: (a) => a.branch_name || "—" },
          { key: "status", header: "وضعیت", render: (a) => <StatusText status={a.status} /> },
        ]}
      />
    </div>
  );
}
