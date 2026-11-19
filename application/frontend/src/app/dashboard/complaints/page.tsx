// Path: frontend/src/app/dashboard/complaints/page.tsx

"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock, MessageSquarePlus, Plus, ShieldAlert } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { useToast } from "@/components/ui/ToastProvider";

interface ComplaintItem {
  id: string;
  tracking_code: string;
  complainant_name: string;
  complainant_phone: string;
  agency_name: string;
  target_type: string;
  target_title: string;
  subject: string;
  description: string;
  is_confidential: boolean;
  status: string;
  resolution_summary: string;
  notes: { id: string; author_name: string; note: string; is_confidential: boolean; created_at: string }[];
  created_at: string;
}

export default function ComplaintsDashboardPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<ComplaintItem | null>(null);
  const [noteText, setNoteText] = useState("");
  const [resolutionText, setResolutionText] = useState("");

  const [form, setForm] = useState({
    target_type: "AGENCY",
    target_title: "",
    subject: "",
    description: "",
    is_confidential: true,
  });

  const canManage = ["SUPER_ADMIN", "AGENCY_MANAGER"].includes(effectiveRole);

  const complaintsQ = useQuery({
    queryKey: ["complaints-list", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<ComplaintItem[]>("/api/v1/complaints", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch<ComplaintItem>("/api/v1/complaints", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(form),
      }),
    onSuccess: (res) => {
      setCreateOpen(false);
      setForm({ target_type: "AGENCY", target_title: "", subject: "", description: "", is_confidential: true });
      toast.success(`شکایت ثبت شد. کد رهگیری: ${res.data.tracking_code}`);
      qc.invalidateQueries({ queryKey: ["complaints-list"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const noteMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/complaints/${selected?.id}/notes`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ note: noteText, is_confidential: true }),
      }),
    onSuccess: () => {
      setNoteText("");
      toast.success("یادداشت محرمانه رسیدگی ثبت شد.");
      qc.invalidateQueries({ queryKey: ["complaints-list"] });
      setSelected(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const statusMut = useMutation({
    mutationFn: async (status: string) =>
      apiFetch(`/api/v1/complaints/${selected?.id}/status`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status, resolution_summary: resolutionText }),
      }),
    onSuccess: () => {
      toast.success("وضعیت شکایت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["complaints-list"] });
      setSelected(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="رسیدگی به شکایات و گزارش تخلفات"
        subtitle="ثبت شکایات با کد رهگیری یکتا و مدیریت محرمانه پرونده‌های بازرسی"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "شکایات" }]}
        actions={
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            ثبت شکایت جدید
          </button>
        }
      />

      <DataTable
        rows={complaintsQ.data || []}
        rowKey={(c) => c.id}
        isLoading={complaintsQ.isLoading}
        error={complaintsQ.error instanceof Error ? complaintsQ.error.message : null}
        onRetry={() => complaintsQ.refetch()}
        searchPlaceholder="جستجو در کد رهگیری یا موضوع شکایت..."
        exportFileName="complaints"
        columns={[
          { key: "code", header: "کد رهگیری", render: (c) => <span className="font-mono text-xs font-bold">{c.tracking_code}</span> },
          {
            key: "subject",
            header: "موضوع",
            render: (c) => (
              <div className="flex items-center gap-1.5">
                {c.is_confidential && <Lock className="h-3.5 w-3.5 text-amber-600 shrink-0" />}
                <span className="font-semibold">{c.subject}</span>
              </div>
            ),
          },
          { key: "target", header: "موضوع / آژانس", render: (c) => `${c.target_type} (${c.target_title || c.agency_name})` },
          { key: "status", header: "وضعیت", render: (c) => <StatusText status={c.status} /> },
          { key: "dt", header: "تاریخ ثبت", render: (c) => <DateDisplay value={c.created_at} /> },
          {
            key: "act",
            header: "پرونده",
            render: (c) => (
              <button
                type="button"
                onClick={() => {
                  setSelected(c);
                  setResolutionText(c.resolution_summary || "");
                }}
                className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                جزئیات و رسیدگی
              </button>
            ),
          },
        ]}
      />

      <ModalDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="ثبت شکایت جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            value={form.target_type}
            onChange={(e) => setForm({ ...form, target_type: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm dark:text-slate-100"
          >
            <option value="AGENCY">آژانس املاک</option>
            <option value="AGENT">مشاور املاک</option>
            <option value="PROPERTY">آگهی ملکی</option>
            <option value="PLATFORM">پلتفرم</option>
            <option value="OTHER">سایر</option>
          </select>
          <input
            placeholder="نام شعبه / مشاور / کد ملک مرتبط"
            value={form.target_title}
            onChange={(e) => setForm({ ...form, target_title: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm dark:text-slate-100"
          />
          <input
            required
            placeholder="موضوع شکایت"
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm dark:text-slate-100"
          />
          <textarea
            required
            rows={4}
            placeholder="شرح کامل شکایت..."
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-sm dark:text-slate-100"
          />
          <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_confidential}
              onChange={(e) => setForm({ ...form, is_confidential: e.target.checked })}
              className="accent-teal-700"
            />
            ثبت به صورت محرمانه (فقط بازرسی مرکزی پلتفرم دسترسی داشته باشد)
          </label>
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت شکایت و دریافت کد رهگیری
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected ? `پرونده ${selected.tracking_code}` : ""}
        widthClass="max-w-2xl"
      >
        {selected && (
          <div className="space-y-4 text-xs">
            <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-slate-900 dark:text-slate-100">{selected.subject}</span>
                <StatusText status={selected.status} />
              </div>
              <p className="leading-relaxed text-slate-700 dark:text-slate-300">{selected.description}</p>
              <div className="text-slate-500 dark:text-slate-400">
                شاکی: {selected.complainant_name} ({selected.complainant_phone})
              </div>
            </div>

            {selected.notes.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <ShieldAlert className="h-4 w-4 text-amber-600" />
                  یادداشت‌های رسیدگی محرمانه
                </h3>
                {selected.notes.map((n) => (
                  <div key={n.id} className="rounded-lg border border-amber-200 dark:border-amber-900/50 bg-amber-50/50 dark:bg-amber-950/20 p-3">
                    <div className="font-semibold">{n.author_name}</div>
                    <p className="mt-1 text-slate-700 dark:text-slate-300">{n.note}</p>
                  </div>
                ))}
              </div>
            )}

            {canManage && (
              <div className="border-t border-slate-200 dark:border-slate-800 pt-4 space-y-3">
                <div className="space-y-2">
                  <textarea
                    rows={2}
                    placeholder="افزودن یادداشت بازرسی محرمانه..."
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-xs dark:text-slate-100"
                  />
                  <button
                    type="button"
                    onClick={() => noteMut.mutate()}
                    disabled={!noteText.trim() || noteMut.isPending}
                    className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 px-3 font-semibold"
                  >
                    <MessageSquarePlus className="h-3.5 w-3.5" />
                    ثبت یادداشت
                  </button>
                </div>

                <div className="space-y-2 border-t border-slate-200 dark:border-slate-800 pt-3">
                  <input
                    placeholder="نتیجه نهایی رسیدگی (قابل مشاهده در رهگیری عمومی)..."
                    value={resolutionText}
                    onChange={(e) => setResolutionText(e.target.value)}
                    className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs dark:text-slate-100"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => statusMut.mutate("IN_PROGRESS")}
                      className="h-8 rounded-lg bg-amber-600 px-3 font-semibold text-white"
                    >
                      در حال بررسی
                    </button>
                    <button
                      type="button"
                      onClick={() => statusMut.mutate("ESCALATED")}
                      className="h-8 rounded-lg bg-rose-700 px-3 font-semibold text-white"
                    >
                      ارجاع به سطح بالاتر
                    </button>
                    <button
                      type="button"
                      onClick={() => statusMut.mutate("RESOLVED")}
                      className="h-8 rounded-lg bg-emerald-700 px-3 font-semibold text-white"
                    >
                      مختومه و حل‌شده
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </ModalDrawer>
    </div>
  );
}
