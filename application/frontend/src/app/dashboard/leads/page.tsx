"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, Edit3, MessageSquarePlus, Plus, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { LeadItem, TeamMemberItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

const REQUEST_LABELS: Record<string, string> = {
  BUY: "خرید",
  RENT: "اجاره",
  SELL: "فروش ملک",
};

const SOURCE_LABELS: Record<string, string> = {
  PORTAL: "پورتال",
  INSTAGRAM: "اینستاگرام",
  CALL: "تماس ورودی",
  REFERRAL: "معرف",
};

export default function LeadsPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [agentFilter, setAgentFilter] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<LeadItem | null>(null);
  const [activityTarget, setActivityTarget] = useState<LeadItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    full_name: "",
    phone_number: "",
    request_type: "BUY",
    source: "PORTAL",
    assigned_membership_id: "",
    notes: "",
  });

  const [editForm, setEditForm] = useState({
    full_name: "",
    phone_number: "",
    request_type: "BUY",
    source: "PORTAL",
    status: "NEW",
    assigned_membership_id: "",
    notes: "",
  });

  const [actForm, setActForm] = useState({
    activity_type: "CALL",
    note: "",
  });

  const leadsQ = useQuery({
    queryKey: ["leads", activeAgencyId, statusFilter, agentFilter],
    enabled: !!accessToken,
    queryFn: async () => {
      const sp = new URLSearchParams({ page_size: "100" });
      if (statusFilter) sp.set("status", statusFilter);
      if (agentFilter) sp.set("assigned_membership_id", agentFilter);
      return (
        await apiFetch<LeadItem[]>(`/api/v1/leads?${sp.toString()}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const membersAgencyId = activeAgencyId || editTarget?.agency_id || null;

  const membersQ = useQuery({
    queryKey: ["leads-team-members", membersAgencyId],
    enabled: !!accessToken && !!membersAgencyId,
    queryFn: async () =>
      (
        await apiFetch<TeamMemberItem[]>("/api/v1/team/members", {
          token: accessToken,
          agencyId: membersAgencyId,
        })
      ).data,
  });

  const createMut = useMutation({
    mutationFn: async () => {
      if (!activeAgencyId) {
        throw new Error("برای ثبت سرنخ جدید، ابتدا آژانس مقصد را از منوی بالای صفحه انتخاب کنید.");
      }
      return apiFetch("/api/v1/leads", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          full_name: form.full_name,
          phone_number: form.phone_number,
          request_type: form.request_type,
          source: form.source,
          assigned_membership_id: form.assigned_membership_id || null,
          notes: form.notes,
        }),
      });
    },
    onSuccess: () => {
      setModalOpen(false);
      setForm({
        full_name: "",
        phone_number: "",
        request_type: "BUY",
        source: "PORTAL",
        assigned_membership_id: "",
        notes: "",
      });
      setErrMsg(null);
      setNotice("سرنخ جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const editMut = useMutation({
    mutationFn: async () => {
      if (!editTarget) return;
      return apiFetch(`/api/v1/leads/${editTarget.id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId || editTarget.agency_id || null,
        body: JSON.stringify({
          full_name: editForm.full_name.trim(),
          phone_number: editForm.phone_number.trim(),
          request_type: editForm.request_type,
          source: editForm.source,
          status: editForm.status,
          assigned_membership_id: editForm.assigned_membership_id || null,
          notes: editForm.notes,
        }),
      });
    },
    onSuccess: () => {
      setEditTarget(null);
      setErrMsg(null);
      setNotice("سرنخ با موفقیت ویرایش و به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const addActivityMut = useMutation({
    mutationFn: async () => {
      if (!activityTarget) return;
      return apiFetch(`/api/v1/leads/${activityTarget.id}/activities`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId || activityTarget.agency_id || null,
        body: JSON.stringify(actForm),
      });
    },
    onSuccess: () => {
      setActForm({ activity_type: "CALL", note: "" });
      setErrMsg(null);
      setNotice("گزارش پیگیری سرنخ ثبت شد.");
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: async (lead: LeadItem) =>
      apiFetch(`/api/v1/leads/${lead.id}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId || lead.agency_id || null,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("سرنخ با موفقیت حذف (بایگانی) شد.");
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const convertMut = useMutation({
    mutationFn: async (lead: LeadItem) =>
      apiFetch(`/api/v1/leads/${lead.id}/convert`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId || lead.agency_id || null,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("سرنخ با موفقیت به مشتری دائمی تبدیل و در بخش مشتریان ثبت شد.");
      qc.invalidateQueries({ queryKey: ["leads"] });
      qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const activeActivityLead = activityTarget
    ? (leadsQ.data || []).find((l) => l.id === activityTarget.id) || activityTarget
    : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="سرنخ‌های فروش و اجاره (Leads)"
        subtitle="دریافت تقاضاهای اولیه، تخصیص مشاور، ثبت پیگیری‌ها، تغییر مرحله قیف و تبدیل یک‌کلیکی به مشتری"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "سرنخ‌ها" }]}
        actions={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
          >
            <Plus className="h-4 w-4" />
            ثبت سرنخ جدید
          </button>
        }
      />

      {effectiveRole === "SUPER_ADMIN" && !activeAgencyId && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          شما در نمای سراسری همه آژانس‌ها هستید. برای ثبت سرنخ جدید، ابتدا آژانس مقصد را از منوی بالای صفحه انتخاب کنید.
        </div>
      )}

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {activeAgencyId && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">فیلتر مشاور مسئول:</span>
          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="h-9 min-w-[220px] rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="">همه مشاوران</option>
            {(membersQ.data || []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.full_name} ({m.role_name})
              </option>
            ))}
          </select>
        </div>
      )}

      <DataTable
        rows={leadsQ.data || []}
        rowKey={(l) => l.id}
        isLoading={leadsQ.isLoading}
        error={leadsQ.error instanceof Error ? leadsQ.error.message : null}
        onRetry={() => leadsQ.refetch()}
        searchPlaceholder="جستجو در نام یا شماره سرنخ..."
        activeFilter={statusFilter}
        onFilterChange={setStatusFilter}
        filterTabs={[
          { value: "", label: "همه" },
          { value: "NEW", label: "جدید" },
          { value: "CONTACTED", label: "تماس‌گرفته‌شده" },
          { value: "QUALIFIED", label: "واجد شرایط" },
          { value: "CONVERTED", label: "تبدیل‌شده" },
          { value: "DISQUALIFIED", label: "ردشده" },
        ]}
        columns={[
          {
            key: "name",
            header: "متقاضی",
            render: (l) => (
              <div>
                <div className="font-semibold">{l.full_name}</div>
                {!activeAgencyId && l.agency_name && (
                  <div className="text-[11px] text-slate-500">{l.agency_name}</div>
                )}
              </div>
            ),
          },
          {
            key: "phone",
            header: "شماره تماس",
            render: (l) => <span className="font-mono text-xs">{l.phone_number}</span>,
          },
          {
            key: "req",
            header: "تقاضا / منبع",
            render: (l) => (
              <div className="text-xs">
                <div className="font-medium">{REQUEST_LABELS[l.request_type] || l.request_type}</div>
                <div className="text-[11px] text-slate-500">{SOURCE_LABELS[l.source] || l.source}</div>
              </div>
            ),
          },
          {
            key: "agent",
            header: "مشاور مسئول",
            render: (l) => <span className="text-xs">{l.assigned_agent_name || "تخصیص‌نیافته"}</span>,
          },
          {
            key: "notes",
            header: "یادداشت",
            render: (l) => (
              <span className="line-clamp-2 max-w-[200px] text-xs text-slate-600 dark:text-slate-400">
                {l.notes || "—"}
              </span>
            ),
          },
          { key: "status", header: "وضعیت", render: (l) => <StatusText status={l.status} /> },
          { key: "dt", header: "تاریخ", render: (l) => <DateDisplay value={l.created_at} /> },
          {
            key: "act",
            header: "عملیات",
            render: (l) => (
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => {
                    setEditTarget(l);
                    setEditForm({
                      full_name: l.full_name,
                      phone_number: l.phone_number,
                      request_type: l.request_type,
                      source: l.source,
                      status: l.status,
                      assigned_membership_id: l.assigned_membership_id || "",
                      notes: l.notes || "",
                    });
                  }}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Edit3 className="h-3 w-3" />
                  ویرایش
                </button>
                <button
                  type="button"
                  onClick={() => setActivityTarget(l)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <MessageSquarePlus className="h-3 w-3 text-teal-700 dark:text-teal-400" />
                  پیگیری ({l.activities?.length || 0})
                </button>
                {l.status !== "CONVERTED" && (
                  <button
                    type="button"
                    disabled={convertMut.isPending}
                    onClick={() => convertMut.mutate(l)}
                    className="inline-flex h-7 items-center gap-1 rounded bg-teal-700 px-2 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
                  >
                    <ArrowLeftRight className="h-3 w-3" />
                    تبدیل به مشتری
                  </button>
                )}
                <button
                  type="button"
                  disabled={deleteMut.isPending}
                  onClick={() => {
                    if (window.confirm(`آیا از حذف سرنخ «${l.full_name}» مطمئن هستید؟`)) {
                      deleteMut.mutate(l);
                    }
                  }}
                  className="inline-flex h-7 items-center justify-center rounded border border-rose-200 bg-rose-50 px-2 text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300"
                  title="حذف سرنخ"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
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
          {!activeAgencyId && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
              ابتدا از منوی بالای صفحه آژانس مقصد را انتخاب کنید.
            </div>
          )}
          <input
            required
            placeholder="نام کامل *"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <input
            required
            dir="ltr"
            placeholder="0912..."
            value={form.phone_number}
            onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
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
          {activeAgencyId && (
            <select
              value={form.assigned_membership_id}
              onChange={(e) => setForm({ ...form, assigned_membership_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="">تخصیص خودکار به ثبت‌کننده</option>
              {(membersQ.data || []).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name} ({m.role_name})
                </option>
              ))}
            </select>
          )}
          <textarea
            rows={3}
            placeholder="توضیحات تقاضا..."
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-sm"
          />
          <button
            type="submit"
            disabled={createMut.isPending || !activeAgencyId}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white disabled:opacity-60"
          >
            {createMut.isPending ? "در حال ثبت..." : "ثبت سرنخ"}
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        title={`ویرایش سرنخ — ${editTarget?.full_name || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            editMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام کامل"
            value={editForm.full_name}
            onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <input
            required
            dir="ltr"
            placeholder="شماره تماس"
            value={editForm.phone_number}
            onChange={(e) => setEditForm({ ...editForm, phone_number: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <select
              value={editForm.request_type}
              onChange={(e) => setEditForm({ ...editForm, request_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="BUY">خرید</option>
              <option value="RENT">اجاره</option>
              <option value="SELL">فروش ملک</option>
            </select>
            <select
              value={editForm.source}
              onChange={(e) => setEditForm({ ...editForm, source: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="PORTAL">پورتال</option>
              <option value="INSTAGRAM">اینستاگرام</option>
              <option value="CALL">تماس ورودی</option>
              <option value="REFERRAL">معرف</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">مرحله سرنخ</label>
              <select
                value={editForm.status}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
              >
                <option value="NEW">جدید</option>
                <option value="CONTACTED">تماس گرفته‌شده</option>
                <option value="QUALIFIED">واجد شرایط</option>
                <option value="CONVERTED">تبدیل‌شده به مشتری</option>
                <option value="DISQUALIFIED">ردشده / نامعتبر</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">مشاور مسئول</label>
              <select
                value={editForm.assigned_membership_id}
                onChange={(e) => setEditForm({ ...editForm, assigned_membership_id: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
              >
                <option value="">تخصیص‌نیافته</option>
                {(membersQ.data || []).map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.full_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <textarea
            rows={3}
            placeholder="یادداشت..."
            value={editForm.notes}
            onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-sm"
          />
          <button
            type="submit"
            disabled={editMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            {editMut.isPending ? "در حال ذخیره..." : "ذخیره تغییرات سرنخ"}
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={Boolean(activeActivityLead)}
        onClose={() => setActivityTarget(null)}
        title={`تاریخچه و ثبت پیگیری — ${activeActivityLead?.full_name || ""}`}
        widthClass="max-w-xl"
      >
        {activeActivityLead && (
          <div className="space-y-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!actForm.note.trim()) return;
                addActivityMut.mutate();
              }}
              className="space-y-2.5 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/40"
            >
              <select
                value={actForm.activity_type}
                onChange={(e) => setActForm({ ...actForm, activity_type: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
              >
                <option value="CALL">تماس تلفنی</option>
                <option value="FOLLOW_UP">پیگیری بعدی</option>
                <option value="MEETING">جلسه حضوری</option>
                <option value="NOTE">یادداشت داخلی</option>
              </select>
              <textarea
                required
                rows={2}
                value={actForm.note}
                onChange={(e) => setActForm({ ...actForm, note: e.target.value })}
                placeholder="نتیجه تماس یا پیگیری سرنخ..."
                className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
              />
              <button
                type="submit"
                disabled={addActivityMut.isPending || !actForm.note.trim()}
                className="h-9 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                {addActivityMut.isPending ? "در حال ثبت..." : "ثبت گزارش پیگیری"}
              </button>
            </form>

            <div className="space-y-2 max-h-[45vh] overflow-y-auto">
              {activeActivityLead.activities && activeActivityLead.activities.length > 0 ? (
                activeActivityLead.activities.map((a) => (
                  <div
                    key={a.id}
                    className="rounded-lg border border-slate-200 bg-white p-3 text-xs dark:border-slate-800 dark:bg-slate-950"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-teal-800 dark:text-teal-300">
                        {a.activity_type} · {a.created_by_name}
                      </span>
                      <DateDisplay value={a.created_at} className="text-[11px] text-slate-500" />
                    </div>
                    <p className="mt-1 whitespace-pre-line text-slate-700 dark:text-slate-300">{a.note}</p>
                  </div>
                ))
              ) : (
                <p className="py-4 text-center text-xs text-slate-400">
                  هنوز فعالیتی برای این سرنخ ثبت نشده است.
                </p>
              )}
            </div>
          </div>
        )}
      </ModalDrawer>
    </div>
  );
}
