"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Eye } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AuditLogItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";

export default function AuditLogsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const [resourceFilter, setResourceFilter] = useState("");
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  const logsQ = useQuery({
    queryKey: ["audit-logs", activeAgencyId, resourceFilter],
    enabled: !!accessToken,
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "60" });
      if (resourceFilter.trim()) params.set("resource_type", resourceFilter.trim());
      return (
        await apiFetch<AuditLogItem[]>(`/api/v1/audit/logs?${params.toString()}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="گزارش ممیزی و تغییرات سیستم (Audit Logs)"
        subtitle="ثبت تغییرناپذیر تمام رویدادهای حساس امنیتی، مالی، تغییر وضعیت و دسترسی‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "گزارش ممیزی" }]}
      />

      <DataTable
        rows={logsQ.data || []}
        rowKey={(l) => l.id}
        isLoading={logsQ.isLoading}
        error={logsQ.error instanceof Error ? logsQ.error.message : null}
        onRetry={() => logsQ.refetch()}
        searchPlaceholder="جستجو در اقدام یا کاربر..."
        toolbarExtra={
          <select
            value={resourceFilter}
            onChange={(e) => setResourceFilter(e.target.value)}
            className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700"
          >
            <option value="">همه موجودیت‌ها</option>
            <option value="Property">ملک (Property)</option>
            <option value="Contract">قرارداد (Contract)</option>
            <option value="Deal">معامله (Deal)</option>
            <option value="Commission">کمیسیون (Commission)</option>
            <option value="JournalEntry">سند حسابداری (JournalEntry)</option>
            <option value="AgencyAccessPolicy">سیاست دسترسی</option>
            <option value="AgencyMembership">عضویت تیم</option>
          </select>
        }
        columns={[
          {
            key: "date",
            header: "زمان",
            render: (l) => <DateDisplay value={l.created_at} withTime className="text-xs text-slate-600" />,
          },
          {
            key: "actor",
            header: "انجام‌دهنده",
            render: (l) => (
              <div>
                <div className="font-semibold text-slate-900">{l.actor_name}</div>
                {l.actor_phone && <div className="font-mono text-[11px] text-slate-500">{l.actor_phone}</div>}
              </div>
            ),
          },
          { key: "action", header: "رویداد", render: (l) => <span className="font-mono text-xs font-bold text-teal-800">{l.action}</span> },
          {
            key: "res",
            header: "موجودیت",
            render: (l) => (
              <div>
                <div className="text-xs font-medium text-slate-800">{l.resource_type}</div>
                <div className="font-mono text-[11px] text-slate-400">{l.resource_id.slice(0, 12)}</div>
              </div>
            ),
          },
          { key: "ip", header: "نشانی IP", render: (l) => <span className="font-mono text-xs text-slate-500">{l.ip_address || "—"}</span> },
          {
            key: "inspect",
            header: "جزئیات",
            render: (l) => (
              <button
                type="button"
                onClick={() => setSelectedLog(l)}
                className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-800 hover:bg-slate-50"
              >
                <Eye className="h-3.5 w-3.5" />
                مشاهده
              </button>
            ),
          },
        ]}
      />

      <ModalDrawer
        open={!!selectedLog}
        onClose={() => setSelectedLog(null)}
        title={selectedLog ? `جزئیات لاگ: ${selectedLog.action}` : ""}
        widthClass="max-w-2xl"
      >
        {selectedLog && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div>کاربر: <span className="font-bold">{selectedLog.actor_name}</span></div>
              <div>موجودیت: <span className="font-mono font-bold">{selectedLog.resource_type}</span></div>
              <div>شناسه رکورد: <span className="font-mono">{selectedLog.resource_id}</span></div>
              <div>زمان: <DateDisplay value={selectedLog.created_at} withTime /></div>
            </div>

            {selectedLog.before_state && (
              <div>
                <div className="mb-1 font-bold text-slate-700">وضعیت قبلی (Before State)</div>
                <pre dir="ltr" className="overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-[11px] text-slate-100">
                  {JSON.stringify(selectedLog.before_state, null, 2)}
                </pre>
              </div>
            )}

            {selectedLog.after_state && (
              <div>
                <div className="mb-1 font-bold text-slate-700">وضعیت جدید (After State)</div>
                <pre dir="ltr" className="overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-[11px] text-emerald-300">
                  {JSON.stringify(selectedLog.after_state, null, 2)}
                </pre>
              </div>
            )}

            <div>
              <div className="mb-1 font-bold text-slate-700">فراداده (Metadata)</div>
              <pre dir="ltr" className="overflow-x-auto rounded-lg bg-slate-100 p-3 font-mono text-[11px] text-slate-800">
                {JSON.stringify(selectedLog.metadata || {}, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </ModalDrawer>
    </div>
  );
}
