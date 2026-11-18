"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AppointmentItem, CustomerItem, PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function AppointmentsPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    property_id: "",
    customer_id: "",
    scheduled_start: "2026-12-06T10:00",
    scheduled_end: "2026-12-06T11:00",
  });

  const apptsQ = useQuery({
    queryKey: ["appointments", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<AppointmentItem[]>("/api/v1/appointments", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const propsQ = useQuery({
    queryKey: ["props-for-appt", activeAgencyId],
    enabled: !!accessToken && effectiveRole !== "CUSTOMER",
    queryFn: async () =>
      (await apiFetch<PropertyItem[]>("/api/v1/properties?page_size=50", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const custQ = useQuery({
    queryKey: ["custs-for-appt", activeAgencyId],
    enabled: !!accessToken && effectiveRole !== "CUSTOMER",
    queryFn: async () =>
      (await apiFetch<CustomerItem[]>("/api/v1/customers", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/appointments", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          property_id: form.property_id,
          customer_id: form.customer_id,
          scheduled_start: new Date(form.scheduled_start).toISOString(),
          scheduled_end: new Date(form.scheduled_end).toISOString(),
        }),
      }),
    onSuccess: () => {
      setModalOpen(false);
      setNotice("قرار بازدید با کنترل تداخل زمانی مشاور ثبت شد.");
      qc.invalidateQueries({ queryKey: ["appointments"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const statusMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/appointments/${id}/status`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setNotice("وضعیت بازدید به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["appointments"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="تقویم بازدیدها و هماهنگی"
        subtitle="زمان‌بندی بازدید املاک همراه با جلوگیری خودکار از تداخل زمانی مشاوران"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "بازدیدها" }]}
        actions={
          effectiveRole !== "CUSTOMER" ? (
            <button
              type="button"
              onClick={() => setModalOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Plus className="h-4 w-4" />
              ثبت بازدید جدید
            </button>
          ) : null
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={apptsQ.data || []}
        rowKey={(a) => a.id}
        isLoading={apptsQ.isLoading}
        error={apptsQ.error instanceof Error ? apptsQ.error.message : null}
        searchPlaceholder="جستجو در نام ملک، مشتری یا مشاور..."
        columns={[
          { key: "prop", header: "ملک", render: (a) => <span className="font-semibold">{a.property_title}</span> },
          { key: "cust", header: "مشتری", render: (a) => a.customer_name },
          { key: "agent", header: "مشاور", render: (a) => a.agent_name },
          { key: "start", header: "زمان شروع", render: (a) => <DateDisplay value={a.scheduled_start} withTime /> },
          { key: "status", header: "وضعیت", render: (a) => <StatusText status={a.status} /> },
          {
            key: "act",
            header: "عملیات",
            render: (a) =>
              effectiveRole === "CUSTOMER" ? (
                "—"
              ) : (
                <div className="flex gap-1.5">
                  {a.status === "REQUESTED" && (
                    <button
                      type="button"
                      onClick={() => statusMut.mutate({ id: a.id, status: "CONFIRMED" })}
                      className="rounded bg-teal-700 px-2 py-1 text-xs font-semibold text-white"
                    >
                      تأیید
                    </button>
                  )}
                  {a.status === "CONFIRMED" && (
                    <button
                      type="button"
                      onClick={() => statusMut.mutate({ id: a.id, status: "COMPLETED" })}
                      className="rounded bg-emerald-700 px-2 py-1 text-xs font-semibold text-white"
                    >
                      انجام شد
                    </button>
                  )}
                  {["REQUESTED", "CONFIRMED"].includes(a.status) && (
                    <button
                      type="button"
                      onClick={() => statusMut.mutate({ id: a.id, status: "CANCELLED" })}
                      className="rounded border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700"
                    >
                      لغو
                    </button>
                  )}
                </div>
              ),
          },
        ]}
      />

      <ModalDrawer open={modalOpen} onClose={() => setModalOpen(false)} title="زمان‌بندی بازدید جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={form.property_id}
            onChange={(e) => setForm({ ...form, property_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب ملک...</option>
            {(propsQ.data || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.property_code} — {p.title}
              </option>
            ))}
          </select>
          <select
            required
            value={form.customer_id}
            onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب مشتری...</option>
            {(custQ.data || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </select>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">شروع</label>
              <input
                type="datetime-local"
                value={form.scheduled_start}
                onChange={(e) => setForm({ ...form, scheduled_start: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-2 text-xs"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">پایان</label>
              <input
                type="datetime-local"
                value={form.scheduled_end}
                onChange={(e) => setForm({ ...form, scheduled_end: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-2 text-xs"
              />
            </div>
          </div>
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت بازدید
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
