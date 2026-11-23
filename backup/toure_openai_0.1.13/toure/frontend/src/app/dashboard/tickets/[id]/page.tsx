"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Lock, Send, Star } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { useToast } from "@/components/ui/ToastProvider";

interface TicketDetail {
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
  satisfaction_comment: string;
  can_manage: boolean;
  messages: {
    id: string;
    sender_name: string;
    body: string;
    is_internal_note: boolean;
    created_at: string;
  }[];
  status_history: {
    id: string;
    from_status: string;
    to_status: string;
    changed_by_name: string;
    created_at: string;
  }[];
}

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();

  const [replyBody, setReplyBody] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [rating, setRating] = useState(5);
  const [ratingComment, setRatingComment] = useState("");

  const detailQ = useQuery({
    queryKey: ["ticket-detail", id],
    enabled: !!accessToken && !!id,
    queryFn: async () =>
      (
        await apiFetch<TicketDetail>(`/api/v1/tickets/${id}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const cannedQ = useQuery({
    queryKey: ["canned-replies-detail", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<{ id: string; title: string; body: string }[]>("/api/v1/tickets/canned-replies", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const replyMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/tickets/${id}/messages`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ body: replyBody, is_internal_note: isInternal }),
      }),
    onSuccess: () => {
      setReplyBody("");
      setIsInternal(false);
      toast.success("پیام ثبت شد.");
      qc.invalidateQueries({ queryKey: ["ticket-detail", id] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const statusMut = useMutation({
    mutationFn: async (status: string) =>
      apiFetch(`/api/v1/tickets/${id}/status`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      toast.success("وضعیت تیکت تغییر یافت.");
      qc.invalidateQueries({ queryKey: ["ticket-detail", id] });
      qc.invalidateQueries({ queryKey: ["tickets"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rateMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/tickets/${id}/rating`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ rating, comment: ratingComment }),
      }),
    onSuccess: () => {
      toast.success("امتیاز رضایت شما ثبت شد.");
      qc.invalidateQueries({ queryKey: ["ticket-detail", id] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (detailQ.isLoading) return <LoadingState message="در حال بارگذاری تیکت..." />;
  if (detailQ.error) return <ErrorState message={(detailQ.error as Error).message} onRetry={() => detailQ.refetch()} />;
  const ticket = detailQ.data;
  if (!ticket) return <ErrorState message="تیکت یافت نشد." />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${ticket.ticket_number} — ${ticket.subject}`}
        subtitle={`ایجادکننده: ${ticket.created_by_name} — حوزه: ${ticket.agency_name}`}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "تیکت‌های پشتیبانی", href: "/dashboard/tickets" },
          { label: ticket.ticket_number },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            {ticket.can_manage && ticket.status !== "RESOLVED" && (
              <button
                type="button"
                onClick={() => statusMut.mutate("RESOLVED")}
                className="h-9 rounded-lg bg-emerald-700 px-3.5 text-xs font-semibold text-white hover:bg-emerald-800"
              >
                علامت‌گذاری به عنوان حل‌شده
              </button>
            )}
            {ticket.status !== "CLOSED" && (
              <button
                type="button"
                onClick={() => statusMut.mutate("CLOSED")}
                className="h-9 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200"
              >
                بستن تیکت
              </button>
            )}
            <Link
              href="/dashboard/tickets"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">روند گفتگو</h2>
            <div className="space-y-3">
              {ticket.messages.map((m) => (
                <div
                  key={m.id}
                  className={`rounded-xl border p-4 text-xs ${
                    m.is_internal_note
                      ? "border-amber-300/70 bg-amber-50/70 dark:border-amber-800 dark:bg-amber-950/30"
                      : "border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                      {m.sender_name}
                      {m.is_internal_note && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 dark:text-amber-300">
                          <Lock className="h-3 w-3" />
                          یادداشت داخلی
                        </span>
                      )}
                    </span>
                    <DateDisplay value={m.created_at} withTime />
                  </div>
                  <p className="leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{m.body}</p>
                </div>
              ))}
            </div>

            {ticket.status !== "CLOSED" && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  replyMut.mutate();
                }}
                className="border-t border-slate-200 dark:border-slate-800 pt-4 space-y-3"
              >
                {ticket.can_manage && (cannedQ.data || []).length > 0 && (
                  <select
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) setReplyBody(e.target.value);
                    }}
                    className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs dark:text-slate-100"
                  >
                    <option value="">درج پاسخ آماده...</option>
                    {(cannedQ.data || []).map((c) => (
                      <option key={c.id} value={c.body}>
                        {c.title}
                      </option>
                    ))}
                  </select>
                )}
                <textarea
                  required
                  rows={3}
                  placeholder="متن پاسخ یا یادداشت..."
                  value={replyBody}
                  onChange={(e) => setReplyBody(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-xs dark:text-slate-100"
                />
                <div className="flex flex-wrap items-center justify-between gap-2">
                  {ticket.can_manage ? (
                    <label className="inline-flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isInternal}
                        onChange={(e) => setIsInternal(e.target.checked)}
                        className="accent-amber-600"
                      />
                      ثبت به عنوان یادداشت داخلی (مخفی از کاربر)
                    </label>
                  ) : (
                    <span />
                  )}
                  <button
                    type="submit"
                    disabled={replyMut.isPending}
                    className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800"
                  >
                    <Send className="h-3.5 w-3.5" />
                    ارسال پیام
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3 text-xs">
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-2.5">
              اطلاعات تیکت
            </h2>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">وضعیت:</span>
              <StatusText status={ticket.status} />
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">اولویت:</span>
              <span className="font-mono font-semibold">{ticket.priority}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">دسته‌بندی:</span>
              <span className="font-mono">{ticket.category}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">مسئول پیگیری:</span>
              <span className="font-semibold">{ticket.assigned_to_name || "در انتظار ارجاع"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">مهلت SLA:</span>
              <DateDisplay value={ticket.sla_due_at} withTime />
            </div>
          </section>

          {(ticket.status === "RESOLVED" || ticket.status === "CLOSED") && (
            <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3 text-xs">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">ارزیابی رضایت پشتیبانی</h2>
              {ticket.satisfaction_rating ? (
                <div className="space-y-1">
                  <div className="flex items-center gap-1 text-amber-500 font-bold">
                    <Star className="h-4 w-4 fill-amber-500" />
                    امتیاز ثبت‌شده: {ticket.satisfaction_rating} از ۵
                  </div>
                  {ticket.satisfaction_comment && (
                    <p className="text-slate-600 dark:text-slate-300">{ticket.satisfaction_comment}</p>
                  )}
                </div>
              ) : (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    rateMut.mutate();
                  }}
                  className="space-y-2.5"
                >
                  <select
                    value={rating}
                    onChange={(e) => setRating(Number(e.target.value))}
                    className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs dark:text-slate-100"
                  >
                    {[5, 4, 3, 2, 1].map((v) => (
                      <option key={v} value={v}>
                        {v} ستاره
                      </option>
                    ))}
                  </select>
                  <input
                    placeholder="نظر شما درباره کیفیت پاسخ‌گویی..."
                    value={ratingComment}
                    onChange={(e) => setRatingComment(e.target.value)}
                    className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs dark:text-slate-100"
                  />
                  <button type="submit" className="h-9 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white">
                    ثبت امتیاز رضایت
                  </button>
                </form>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
