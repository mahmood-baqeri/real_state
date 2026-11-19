"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { LeadItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function LeadsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    full_name: "",
    phone_number: "",
    request_type: "BUY",
    source: "PORTAL",
    notes: "",
  });

  const leadsQ = useQuery({
    queryKey: ["leads", activeAgencyId, statusFilter],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () => {
      const q = statusFilter ? `?status=${statusFilter}` : "";
      return (
        await apiFetch<LeadItem[]>(`/api/v1/leads${q}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/leads", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      setModalOpen(false);
      setForm({ full_name: "", phone_number: "", request_type: "BUY", source: "PORTAL", notes: "" });
      setNotice("سرنخ جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const convertMut = useMutation({
    mutationFn: async (leadId: string) =>
      apiFetch(`/api/v1/leads/${leadId}/convert`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setNotice("سرنخ با موفقیت به مشتری دائمی تبدیل و در بخش مشتریان ثبت شد.");
      qc.invalidateQueries({ queryKey: ["leads"] });
      qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="سرنخ‌های فروش و اجاره (Leads)"
        subtitle="دریافت تقاضاهای اولیه از پورتال یا شبکه‌های اجتماعی و تبدیل یک‌کلیکی به مشتری"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "سرنخ‌ها" }]}
        actions={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            ثبت سرنخ جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={leadsQ.data || []}
        rowKey={(l) => l.id}
        isLoading={leadsQ.isLoading}
        error={leadsQ.error instanceof Error ? leadsQ.error.message : null}
        searchPlaceholder="جستجو در نام یا شماره سرنخ..."
        activeFilter={statusFilter}
        onFilterChange={setStatusFilter}
        filterTabs={[
          { value: "", label: "همه" },
          { value: "NEW", label: "جدید" },
          { value: "QUALIFIED", label: "واجد شرایط" },
          { value: "CONVERTED", label: "تبدیل‌شده" },
        ]}
        columns={[
          { key: "name", header: "متقاضی", render: (l) => <span className="font-semibold">{l.full_name}</span> },
          { key: "phone", header: "شماره تماس", render: (l) => <span className="font-mono text-xs">{l.phone_number}</span> },
          { key: "req", header: "نوع تقاضا", render: (l) => l.request_type },
          { key: "src", header: "منبع", render: (l) => l.source },
          { key: "notes", header: "یادداشت", render: (l) => <span className="text-xs text-slate-600 dark:text-slate-400">{l.notes || "—"}</span> },
          { key: "status", header: "وضعیت", render: (l) => <StatusText status={l.status} /> },
          { key: "dt", header: "تاریخ", render: (l) => <DateDisplay value={l.created_at} /> },
          {
            key: "act",
            header: "تبدیل",
            render: (l) =>
              l.status !== "CONVERTED" ? (
                <button
                  type="button"
                  onClick={() => convertMut.mutate(l.id)}
                  className="inline-flex h-7 items-center gap-1 rounded bg-teal-700 px-2.5 text-xs font-semibold text-white hover:bg-teal-800"
                >
                  <ArrowLeftRight className="h-3 w-3" />
                  تبدیل به مشتری
                </button>
              ) : (
                <span className="text-xs text-emerald-700 font-medium">تبدیل‌شده</span>
              ),
          },
        ]}
      />

      <ModalDrawer open={modalOpen} onClose={() => setModalOpen(false)} title="ثبت سرنخ جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام کامل"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
          />
          <input
            required
            dir="ltr"
            placeholder="0912..."
            value={form.phone_number}
            onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-left font-mono text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <select
              value={form.request_type}
              onChange={(e) => setForm({ ...form, request_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="BUY">خرید</option>
              <option value="RENT">اجاره</option>
              <option value="SELL">فروش ملک</option>
            </select>
            <select
              value={form.source}
              onChange={(e) => setForm({ ...form, source: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="PORTAL">پورتال</option>
              <option value="INSTAGRAM">اینستاگرام</option>
              <option value="CALL">تماس ورودی</option>
              <option value="REFERRAL">معرف</option>
            </select>
          </div>
          <textarea
            rows={3}
            placeholder="توضیحات تقاضا..."
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 p-2.5 text-sm"
          />
          <button
            type="submit"
            disabled={createMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ثبت سرنخ
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
