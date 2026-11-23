"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, List, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AppointmentItem, CustomerItem, PropertyItem, UnifiedCalendarEvent } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

const EVENT_TYPE_LABEL: Record<string, string> = {
  VIEWING: "بازدید ملک",
  TASK: "پیگیری CRM",
  CONTRACT: "سررسید قرارداد",
  CHEQUE: "سررسید چک",
};

export default function AppointmentsPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"appointments" | "calendar">("appointments");
  const [calFilter, setCalFilter] = useState<string>("");
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

  const calendarQ = useQuery({
    queryKey: ["unified-calendar", activeAgencyId],
    enabled: !!accessToken && tab === "calendar",
    queryFn: async () =>
      (
        await apiFetch<UnifiedCalendarEvent[]>("/api/v1/appointments/calendar?days_ahead=30", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
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
      qc.invalidateQueries({ queryKey: ["unified-calendar"] });
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
      qc.invalidateQueries({ queryKey: ["unified-calendar"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const filteredCalendar = (calendarQ.data || []).filter((ev) =>
    calFilter ? ev.event_type === calFilter : true
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="تقویم بازدیدها و رویدادهای یکپارچه"
        subtitle="زمان‌بندی بازدید املاک با کنترل تداخل و مشاهده تقویم ۳۰ روزه بازدید، پیگیری‌ها، قراردادها و چک‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "بازدیدها و تقویم" }]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 dark:border-slate-700 dark:bg-slate-900">
              <button
                type="button"
                onClick={() => setTab("appointments")}
                className={`inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors ${
                  tab === "appointments"
                    ? "bg-teal-700 text-white"
                    : "text-slate-600 dark:text-slate-300"
                }`}
              >
                <List className="h-3.5 w-3.5" />
                فهرست بازدیدها
              </button>
              <button
                type="button"
                onClick={() => setTab("calendar")}
                className={`inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors ${
                  tab === "calendar"
                    ? "bg-teal-700 text-white"
                    : "text-slate-600 dark:text-slate-300"
                }`}
              >
                <CalendarDays className="h-3.5 w-3.5" />
                تقویم یکپارچه
              </button>
            </div>
            {effectiveRole !== "CUSTOMER" && (
              <button
                type="button"
                onClick={() => setModalOpen(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <Plus className="h-4 w-4" />
                ثبت بازدید جدید
              </button>
            )}
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {tab === "appointments" ? (
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
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {[
              { code: "", label: "همه رویدادها" },
              { code: "VIEWING", label: "بازدیدها" },
              { code: "TASK", label: "پیگیری‌های CRM" },
              { code: "CONTRACT", label: "قراردادها" },
              { code: "CHEQUE", label: "چک‌ها" },
            ].map((item) => (
              <button
                key={item.code || "ALL"}
                type="button"
                onClick={() => setCalFilter(item.code)}
                className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors ${
                  calFilter === item.code
                    ? "border-teal-700 bg-teal-700 text-white"
                    : "border-slate-200 bg-white text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {calendarQ.isLoading ? (
            <LoadingState message="در حال بارگذاری رویدادهای تقویم..." />
          ) : calendarQ.error instanceof Error ? (
            <ErrorState message={calendarQ.error.message} onRetry={() => calendarQ.refetch()} />
          ) : filteredCalendar.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
              رویدادی در ۳۰ روز پیش‌رو یافت نشد.
            </div>
          ) : (
            <div className="space-y-2.5">
              {filteredCalendar.map((ev) => (
                <Link
                  key={`${ev.event_type}-${ev.id}`}
                  href={ev.href}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 text-xs transition-colors hover:border-teal-600 dark:border-slate-800 dark:bg-slate-900"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] font-bold text-teal-700 dark:text-teal-400">
                        {EVENT_TYPE_LABEL[ev.event_type] || ev.event_type}
                      </span>
                      <span className="font-bold text-slate-900 dark:text-slate-100">
                        {ev.title}
                      </span>
                    </div>
                    <div className="text-slate-500 dark:text-slate-400">{ev.subtitle}</div>
                  </div>
                  <div className="flex items-center gap-4">
                    <DateDisplay
                      value={ev.start_at}
                      withTime
                      className="text-slate-600 dark:text-slate-300"
                    />
                    <StatusText status={ev.status} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

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
