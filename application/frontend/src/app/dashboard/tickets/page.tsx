// Path: frontend/src/app/dashboard/tickets/page.tsx

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookTemplate, Plus, Ticket } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { useToast } from "@/components/ui/ToastProvider";
import { formatNumberFa } from "@/lib/formatters";

interface TicketItem {
  id: string;
  ticket_number: string;
  scope: string;
  agency_name: string;
  created_by_name: string;
  assigned_to_name: string | null;
  category: string;
  priority: string;
  status: string;
  subject: string;
  sla_due_at: string | null;
  satisfaction_rating: number | null;
  created_at: string;
}

interface CannedReplyItem {
  id: string;
  title: string;
  category: string;
  body: string;
}

interface TicketReport {
  total: number;
  by_status: { status: string; count: number }[];
  avg_satisfaction: number | null;
}

export default function TicketsPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [cannedOpen, setCannedOpen] = useState(false);

  const [form, setForm] = useState({
    scope: activeAgencyId ? "AGENCY" : "PLATFORM",
    category: "AGENCY_OPS",
    priority: "NORMAL",
    subject: "",
    body: "",
  });

  const [cannedForm, setCannedForm] = useState({ title: "", category: "GENERAL", body: "" });

  const ticketsQ = useQuery({
    queryKey: ["tickets", activeAgencyId, statusFilter],
    enabled: !!accessToken,
    queryFn: async () => {
      const qs = new URLSearchParams();
      if (statusFilter) qs.set("status", statusFilter);
      return (
        await apiFetch<TicketItem[]>(`/api/v1/tickets?${qs.toString()}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const reportQ = useQuery({
    queryKey: ["tickets-report", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<TicketReport>("/api/v1/tickets/reports/summary", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const cannedQ = useQuery({
    queryKey: ["canned-replies", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<CannedReplyItem[]>("/api/v1/tickets/canned-replies", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/tickets", {
        method: "POST",
        token: accessToken,
        agencyId: form.scope === "AGENCY" ? activeAgencyId : null,
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      setCreateOpen(false);
      setForm({ scope: activeAgencyId ? "AGENCY" : "PLATFORM", category: "AGENCY_OPS", priority: "NORMAL", subject: "", body: "" });
      toast.success("تیکت پشتیبانی با موفقیت ثبت شد.");
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["tickets-report"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const cannedMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/tickets/canned-replies", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(cannedForm),
      }),
    onSuccess: () => {
      setCannedForm({ title: "", category: "GENERAL", body: "" });
      toast.success("پاسخ آماده ثبت شد.");
      qc.invalidateQueries({ queryKey: ["canned-replies"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const openCount = (reportQ.data?.by_status || [])
    .filter((s) => s.status === "OPEN" || s.status === "IN_PROGRESS")
    .reduce((acc, s) => acc + s.count, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="مرکز تیکت‌ها و پشتیبانی"
        subtitle="ثبت و پیگیری درخواست‌های پشتیبانی پلتفرم و داخلی آژانس همراه با SLA و پاسخ‌های آماده"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "تیکت‌های پشتیبانی" }]}
        actions={
          <div className="flex flex-wrap gap-2">
            {["SUPER_ADMIN", "AGENCY_MANAGER"].includes(effectiveRole) && (
              <button
                type="button"
                onClick={() => setCannedOpen(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <BookTemplate className="h-4 w-4" />
                پاسخ‌های آماده ({formatNumberFa((cannedQ.data || []).length)})
              </button>
            )}
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Plus className="h-4 w-4" />
              ثبت تیکت جدید
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard label="کل تیکت‌ها" value={formatNumberFa(reportQ.data?.total ?? 0)} icon={<Ticket className="h-4 w-4" />} />
        <KpiCard label="در دست بررسی / باز" value={formatNumberFa(openCount)} />
        <KpiCard
          label="میانگین رضایت (از ۵)"
          value={reportQ.data?.avg_satisfaction ? formatNumberFa(reportQ.data.avg_satisfaction) : "—"}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          { val: "", label: "همه" },
          { val: "OPEN", label: "باز" },
          { val: "IN_PROGRESS", label: "در حال بررسی" },
          { val: "WAITING_USER", label: "در انتظار کاربر" },
          { val: "RESOLVED", label: "حل‌شده" },
          { val: "CLOSED", label: "بسته‌شده" },
        ].map((f) => (
          <button
            key={f.val}
            type="button"
            onClick={() => setStatusFilter(f.val)}
            className={`h-8 rounded-lg border px-3 text-xs font-semibold transition-colors ${
              statusFilter === f.val
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <DataTable
        rows={ticketsQ.data || []}
        rowKey={(t) => t.id}
        isLoading={ticketsQ.isLoading}
        error={ticketsQ.error instanceof Error ? ticketsQ.error.message : null}
        onRetry={() => ticketsQ.refetch()}
        searchPlaceholder="جستجو در شماره تیکت یا موضوع..."
        exportFileName="tickets"
        columns={[
          {
            key: "num",
            header: "شماره تیکت",
            render: (t) => (
              <Link href={`/dashboard/tickets/${t.id}`} className="font-mono text-xs font-semibold text-teal-700 dark:text-teal-400 hover:underline">
                {t.ticket_number}
              </Link>
            ),
          },
          {
            key: "subject",
            header: "موضوع",
            render: (t) => (
              <Link href={`/dashboard/tickets/${t.id}`} className="font-semibold text-slate-900 dark:text-slate-100 hover:underline">
                {t.subject}
              </Link>
            ),
          },
          { key: "scope", header: "حوزه", render: (t) => t.agency_name },
          { key: "priority", header: "اولویت", render: (t) => <span className="font-mono text-xs">{t.priority}</span> },
          { key: "status", header: "وضعیت", render: (t) => <StatusText status={t.status} /> },
          { key: "sla", header: "مهلت SLA", render: (t) => <DateDisplay value={t.sla_due_at} withTime /> },
        ]}
      />

      <ModalDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="ثبت تیکت پشتیبانی جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <select
              value={form.scope}
              onChange={(e) => setForm({ ...form, scope: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm dark:text-slate-100"
            >
              {activeAgencyId && <option value="AGENCY">پشتیبانی داخلی آژانس</option>}
              <option value="PLATFORM">پشتیبانی کل پلتفرم</option>
            </select>
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm dark:text-slate-100"
            >
              <option value="LOW">اولویت کم</option>
              <option value="NORMAL">عادی</option>
              <option value="HIGH">بالا</option>
              <option value="URGENT">فوری</option>
            </select>
          </div>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm dark:text-slate-100"
          >
            <option value="AGENCY_OPS">عملیات آژانس و فایل‌ها</option>
            <option value="TECHNICAL">فنی و سیستمی</option>
            <option value="BILLING">مالی و اشتراک</option>
            <option value="ACCOUNT">حساب کاربری و دسترسی</option>
            <option value="GENERAL">عمومی</option>
          </select>
          <input
            required
            placeholder="موضوع تیکت..."
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm dark:text-slate-100"
          />
          <textarea
            required
            rows={4}
            placeholder="شرح کامل درخواست یا مشکل..."
            value={form.body}
            onChange={(e) => setForm({ ...form, body: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-sm dark:text-slate-100"
          />
          <button
            type="submit"
            disabled={createMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            ارسال تیکت
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={cannedOpen} onClose={() => setCannedOpen(false)} title="مدیریت پاسخ‌های آماده (Canned Replies)">
        <div className="space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              cannedMut.mutate();
            }}
            className="space-y-2.5 border-b border-slate-200 dark:border-slate-800 pb-4"
          >
            <input
              required
              placeholder="عنوان پاسخ آماده"
              value={cannedForm.title}
              onChange={(e) => setCannedForm({ ...cannedForm, title: e.target.value })}
              className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs dark:text-slate-100"
            />
            <textarea
              required
              rows={3}
              placeholder="متن قالب پاسخ..."
              value={cannedForm.body}
              onChange={(e) => setCannedForm({ ...cannedForm, body: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-xs dark:text-slate-100"
            />
            <button type="submit" className="h-9 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white">
              ذخیره پاسخ آماده
            </button>
          </form>
          <div className="space-y-2">
            {(cannedQ.data || []).map((c) => (
              <div key={c.id} className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 p-3 text-xs">
                <div className="font-bold text-slate-900 dark:text-slate-100">{c.title}</div>
                <p className="mt-1 text-slate-600 dark:text-slate-300">{c.body}</p>
              </div>
            ))}
          </div>
        </div>
      </ModalDrawer>
    </div>
  );
}
