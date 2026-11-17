"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, Send } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { NotificationItem, TeamMemberItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

export default function NotificationsPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [form, setForm] = useState({
    recipient_user_id: "",
    channel: "IN_APP",
    title: "",
    body: "",
  });

  const notifsQ = useQuery({
    queryKey: ["notifications-list", unreadOnly],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<NotificationItem[]>(`/api/v1/notifications?unread_only=${unreadOnly}`, {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const membersQ = useQuery({
    queryKey: ["team-for-notif", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<TeamMemberItem[]>("/api/v1/team/members", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const readMut = useMutation({
    mutationFn: async (id: string) =>
      apiFetch(`/api/v1/notifications/${id}/read`, {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications-list"] });
      qc.invalidateQueries({ queryKey: ["unread-notif-count"] });
    },
  });

  const readAllMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/notifications/read-all", {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: () => {
      setNotice("تمامی اعلان‌ها به عنوان خوانده‌شده علامت‌گذاری شدند.");
      qc.invalidateQueries({ queryKey: ["notifications-list"] });
      qc.invalidateQueries({ queryKey: ["unread-notif-count"] });
    },
  });

  const sendMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/notifications", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      setSendOpen(false);
      setForm({ recipient_user_id: "", channel: "IN_APP", title: "", body: "" });
      setErrMsg(null);
      setNotice("پیام با موفقیت از طریق آداپتر اعلان ارسال شد.");
      qc.invalidateQueries({ queryKey: ["notifications-list"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="مرکز اعلان‌ها و پیام‌رسانی"
        subtitle="دریافت اعلان‌های سیستمی، گزارش پیامک‌ها و ارسال پیام مستقیم به اعضای تیم"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "اعلان‌ها" }]}
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => readAllMut.mutate()}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
            >
              <CheckCheck className="h-4 w-4" />
              خواندن همه
            </button>
            <button
              type="button"
              onClick={() => setSendOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
            >
              <Send className="h-4 w-4" />
              ارسال اعلان جدید
            </button>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setUnreadOnly(false)}
          className={`h-9 rounded-lg border px-4 text-xs font-semibold ${
            !unreadOnly ? "border-teal-700 bg-teal-700 text-white" : "border-slate-200 bg-white text-slate-700"
          }`}
        >
          همه اعلان‌ها
        </button>
        <button
          type="button"
          onClick={() => setUnreadOnly(true)}
          className={`h-9 rounded-lg border px-4 text-xs font-semibold ${
            unreadOnly ? "border-teal-700 bg-teal-700 text-white" : "border-slate-200 bg-white text-slate-700"
          }`}
        >
          فقط خوانده‌نشده‌ها
        </button>
      </div>

      {notifsQ.isLoading ? (
        <LoadingState />
      ) : notifsQ.error instanceof Error ? (
        <ErrorState message={notifsQ.error.message} onRetry={() => notifsQ.refetch()} />
      ) : (notifsQ.data || []).length === 0 ? (
        <EmptyState title="اعلانی وجود ندارد" description="در حال حاضر پیام یا اعلان جدیدی ثبت نشده است." />
      ) : (
        <div className="space-y-3">
          {notifsQ.data?.map((n) => (
            <div
              key={n.id}
              className={`flex flex-col justify-between gap-3 rounded-xl border p-4 sm:flex-row sm:items-center ${
                n.is_read ? "border-slate-200 bg-white" : "border-teal-300 bg-teal-50/40"
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-teal-700">
                  <Bell className="h-4 w-4" />
                </div>
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold text-slate-900">{n.title}</span>
                    <StatusText status={n.delivery_status} label={n.channel} />
                  </div>
                  <p className="text-xs leading-relaxed text-slate-600">{n.body}</p>
                  <div className="text-[11px] text-slate-400">
                    <DateDisplay value={n.created_at} withTime />
                    {n.agency_name ? ` — ${n.agency_name}` : ""}
                  </div>
                </div>
              </div>
              {!n.is_read && (
                <button
                  type="button"
                  onClick={() => readMut.mutate(n.id)}
                  className="shrink-0 rounded-lg border border-teal-700 bg-white px-3 py-1.5 text-xs font-semibold text-teal-800 hover:bg-teal-50"
                >
                  تأیید مطالعه
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <ModalDrawer open={sendOpen} onClose={() => setSendOpen(false)} title="ارسال اعلان یا پیامک">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={form.recipient_user_id}
            onChange={(e) => setForm({ ...form, recipient_user_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="">انتخاب کاربر گیرنده...</option>
            {(membersQ.data || []).map((m) => (
              <option key={m.id} value={m.user_id}>
                {m.full_name} ({m.role_name})
              </option>
            ))}
          </select>
          <select
            value={form.channel}
            onChange={(e) => setForm({ ...form, channel: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="IN_APP">اعلان درون‌برنامه‌ای (In-App)</option>
            <option value="SMS">پیامک (SMS Adapter)</option>
          </select>
          <input
            required
            placeholder="عنوان پیام"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <textarea
            required
            rows={4}
            placeholder="متن پیام..."
            value={form.body}
            onChange={(e) => setForm({ ...form, body: e.target.value })}
            className="w-full rounded-lg border border-slate-300 p-3 text-sm"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ارسال اعلان
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
