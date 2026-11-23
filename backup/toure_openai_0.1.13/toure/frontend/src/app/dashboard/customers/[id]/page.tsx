import { confirmDialog } from "@/lib/confirm-dialog";
"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Calendar,
  Edit3,
  FileText,
  Handshake,
  Mail,
  MessageSquarePlus,
  Phone,
  Share2,
  Target,
  Trash2,
  User,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CustomerItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { StatusText } from "@/components/ui/StatusText";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

const CHANNEL_LABELS: Record<string, string> = {
  NOTE: "یادداشت داخلی",
  CALL: "تماس تلفنی",
  MEETING: "جلسه حضوری",
  WHATSAPP: "واتساپ / پیام‌رسان",
  EMAIL: "ایمیل",
};

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { accessToken, activeAgencyId } = useAuth();

  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [channel, setChannel] = useState("NOTE");
  const [summary, setSummary] = useState("");
  const [isPrivate, setIsPrivate] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    full_name: "",
    primary_phone: "",
    email: "",
    customer_type: "BUYER",
    readiness_level: "MEDIUM",
  });

  const custQ = useQuery({
    queryKey: ["customer-detail", params.id, activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<CustomerItem>(`/api/v1/customers/${params.id}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const c = custQ.data;
  const targetAgencyId = activeAgencyId || c?.agency || null;

  const interactionMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/customers/${params.id}/interactions`, {
        method: "POST",
        token: accessToken,
        agencyId: targetAgencyId,
        body: JSON.stringify({
          channel,
          summary: summary.trim(),
          is_private: isPrivate,
        }),
      }),
    onSuccess: () => {
      setSummary("");
      setErrMsg(null);
      setNotice("تعامل جدید با موفقیت در تایم‌لاین پرونده ثبت شد.");
      qc.invalidateQueries({ queryKey: ["customer-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const editMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/customers/${params.id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: targetAgencyId,
        body: JSON.stringify(editForm),
      }),
    onSuccess: () => {
      setEditOpen(false);
      setErrMsg(null);
      setNotice("مشخصات مشتری با موفقیت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["customer-detail", params.id] });
      qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/customers/${params.id}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: targetAgencyId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["customers"] });
      router.push("/dashboard/customers");
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={c ? `پرونده مشتری: ${c.full_name}` : "پرونده ۳۶۰ درجه مشتری"}
        subtitle={
          c
            ? `نوع: ${c.customer_type} · امتیاز سرنخ: ${c.lead_score}${c.agency_name ? ` · آژانس: ${c.agency_name}` : ""}`
            : undefined
        }
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "مشتریان", href: "/dashboard/customers" },
          { label: c?.full_name || "پرونده" },
        ]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {c && (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setEditForm({
                      full_name: c.full_name,
                      primary_phone: c.primary_phone,
                      email: c.email || "",
                      customer_type: c.customer_type,
                      readiness_level: c.readiness_level || "MEDIUM",
                    });
                    setEditOpen(true);
                  }}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 whitespace-nowrap"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                  ویرایش مشخصات
                </button>
                <button
                  type="button"
                  disabled={deleteMut.isPending}
                  onClick={async () => {
                    if (await confirmDialog({ title: "تأیید بایگانی مشتری", message: `آیا از حذف (بایگانی) مشتری «${c.full_name}» مطمئن هستید؟`, danger: true })) {
                      deleteMut.mutate();
                    }
                  }}
                  className="inline-flex h-9 items-center gap-1 rounded-lg border border-rose-200 bg-rose-50 px-3 text-xs font-semibold text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300 whitespace-nowrap"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  بایگانی
                </button>
              </>
            )}
            <Link
              href="/dashboard/customers"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 whitespace-nowrap"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت به فهرست
            </Link>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {custQ.isLoading ? (
        <LoadingState />
      ) : custQ.error instanceof Error ? (
        <ErrorState message={custQ.error.message} onRetry={() => custQ.refetch()} />
      ) : c ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-5">
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <User className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                اطلاعات تماس و مسئولیت
              </h3>
              <dl className="space-y-3 text-xs">
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">شماره تماس:</dt>
                  <dd className="flex items-center gap-1 font-mono font-bold" dir="ltr">
                    <Phone className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                    {c.primary_phone}
                  </dd>
                </div>
                {c.email && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500 dark:text-slate-400">ایمیل:</dt>
                    <dd className="flex items-center gap-1 font-mono" dir="ltr">
                      <Mail className="h-3.5 w-3.5 text-slate-400" />
                      {c.email}
                    </dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">مشاور مسئول:</dt>
                  <dd className="font-semibold">{c.assigned_agent_name || "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">آمادگی خرید/اجاره:</dt>
                  <dd className="font-semibold">{c.readiness_level}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">تاریخ ثبت:</dt>
                  <dd>
                    <DateDisplay value={c.created_at} />
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Share2 className="h-4 w-4 text-amber-600" />
                دسترسی اشتراکی همکاران
              </h3>
              {c.shares.length === 0 ? (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  این پرونده فقط در اختیار مشاور مسئول (خصوصی) است.
                </p>
              ) : (
                <div className="space-y-2 text-xs">
                  {c.shares.map((s) => (
                    <div
                      key={s.id}
                      className="flex justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-800/60"
                    >
                      <span className="font-semibold">{s.agent_name}</span>
                      <span className="font-mono text-slate-500">{s.access_level}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Linked Entities Summary */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Handshake className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                قراردادها، مذاکرات و بازدیدهای مرتبط
              </h3>

              <div className="space-y-3 text-xs">
                <div>
                  <div className="mb-1.5 font-semibold text-slate-500">قراردادها ({c.contracts?.length || 0})</div>
                  {c.contracts && c.contracts.length > 0 ? (
                    <div className="space-y-1.5">
                      {c.contracts.map((ct) => (
                        <Link
                          key={ct.id}
                          href={`/dashboard/contracts/${ct.id}`}
                          className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 hover:border-teal-500 dark:border-slate-800 dark:bg-slate-800/50"
                        >
                          <span className="font-mono font-semibold">{ct.contract_number}</span>
                          <StatusText status={ct.status} />
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-400">قراردادی ثبت نشده است.</span>
                  )}
                </div>

                <div>
                  <div className="mb-1.5 font-semibold text-slate-500">مذاکرات ({c.negotiations?.length || 0})</div>
                  {c.negotiations && c.negotiations.length > 0 ? (
                    <div className="space-y-1.5">
                      {c.negotiations.map((neg) => (
                        <Link
                          key={neg.id}
                          href={`/dashboard/negotiations/${neg.id}`}
                          className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 hover:border-teal-500 dark:border-slate-800 dark:bg-slate-800/50"
                        >
                          <span className="line-clamp-1">{neg.property_title || "مذاکره"}</span>
                          <StatusText status={neg.status} />
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-400">مذاکره‌ای ثبت نشده است.</span>
                  )}
                </div>

                <div>
                  <div className="mb-1.5 flex items-center gap-1 font-semibold text-slate-500">
                    <Calendar className="h-3.5 w-3.5" />
                    بازدیدها ({c.appointments?.length || 0})
                  </div>
                  {c.appointments && c.appointments.length > 0 ? (
                    <div className="space-y-1.5">
                      {c.appointments.map((ap) => (
                        <div
                          key={ap.id}
                          className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-800/50"
                        >
                          <span className="line-clamp-1">{ap.property_title || "بازدید"}</span>
                          <DateDisplay value={ap.scheduled_start} />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-400">بازدیدی ثبت نشده است.</span>
                  )}
                </div>

                <div>
                  <div className="mb-1.5 flex items-center gap-1 font-semibold text-slate-500">
                    <FileText className="h-3.5 w-3.5" />
                    اسناد پیوست ({c.documents?.length || 0})
                  </div>
                  {c.documents && c.documents.length > 0 ? (
                    <div className="space-y-1">
                      {c.documents.map((doc) => (
                        <div key={doc.id} className="flex justify-between rounded border border-slate-200 px-2.5 py-1.5 dark:border-slate-800">
                          <span className="font-medium">{doc.title}</span>
                          <DateDisplay value={doc.created_at} />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-400">سندی ثبت نشده است.</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6 lg:col-span-7">
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Target className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                نیازها و تقاضاهای ملکی ثبت‌شده
              </h3>
              {c.requirements.length === 0 ? (
                <p className="py-4 text-center text-xs text-slate-500 dark:text-slate-400">
                  هنوز تقاضای ملکی برای این مشتری ثبت نشده است.
                </p>
              ) : (
                <div className="space-y-3">
                  {c.requirements.map((req) => (
                    <div
                      key={req.id}
                      className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-800/60"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 font-bold text-slate-900 dark:text-slate-100">
                        <span>
                          {req.deal_type} · {req.property_type} در {req.target_city}
                        </span>
                        <span>حداقل {req.min_bedrooms} خواب</span>
                      </div>
                      <div className="mt-2 text-slate-600 dark:text-slate-300">
                        مناطق: {req.target_districts?.join("، ") || "همه مناطق"} | متراژ:{" "}
                        {req.min_area_sqm} تا {req.max_area_sqm} متر
                      </div>
                      <div className="mt-2 flex gap-4 font-semibold text-teal-800 dark:text-teal-300">
                        <span>
                          حداقل بودجه: <MoneyDisplay amount={req.min_budget} />
                        </span>
                        <span>
                          حداکثر بودجه: <MoneyDisplay amount={req.max_budget} />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Customer Interactions Log & Timeline */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <MessageSquarePlus className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                گزارش تماس‌ها، جلسات و تعاملات (Timeline)
              </h3>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!summary.trim()) return;
                  interactionMut.mutate();
                }}
                className="space-y-2.5 rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 dark:border-slate-800 dark:bg-slate-800/40"
              >
                <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  <select
                    value={channel}
                    onChange={(e) => setChannel(e.target.value)}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="NOTE">یادداشت داخلی</option>
                    <option value="CALL">تماس تلفنی</option>
                    <option value="MEETING">جلسه حضوری</option>
                    <option value="WHATSAPP">واتساپ / پیام‌رسان</option>
                    <option value="EMAIL">ایمیل</option>
                  </select>
                  <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={isPrivate}
                      onChange={(e) => setIsPrivate(e.target.checked)}
                      className="h-4 w-4 accent-teal-700"
                    />
                    یادداشت محرمانه مشاور
                  </label>
                </div>
                <textarea
                  rows={2}
                  required
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  placeholder="خلاصه تماس، بازخورد بازدید یا تصمیم بعدی مشتری..."
                  className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                />
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={interactionMut.isPending || !summary.trim()}
                    className="h-8 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                  >
                    {interactionMut.isPending ? "در حال ثبت..." : "ثبت تعامل در پرونده"}
                  </button>
                </div>
              </form>

              <div className="space-y-2.5">
                {c.interactions && c.interactions.length > 0 ? (
                  c.interactions.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-lg border border-slate-200 bg-white p-3 text-xs dark:border-slate-800 dark:bg-slate-950/60"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-bold text-teal-800 dark:text-teal-300">
                          {CHANNEL_LABELS[item.channel] || item.channel} · {item.author_name}
                        </span>
                        <DateDisplay value={item.created_at} className="text-[11px] text-slate-500" />
                      </div>
                      <p className="mt-1.5 whitespace-pre-line leading-relaxed text-slate-700 dark:text-slate-300">
                        {item.summary}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="py-4 text-center text-xs text-slate-400">
                    هنوز تعاملی برای این مشتری ثبت نشده است.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <ModalDrawer open={editOpen} onClose={() => setEditOpen(false)} title="ویرایش اطلاعات مشتری">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            editMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام و نام خانوادگی"
            value={editForm.full_name}
            onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <input
            required
            dir="ltr"
            placeholder="شماره تماس"
            value={editForm.primary_phone}
            onChange={(e) => setEditForm({ ...editForm, primary_phone: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
          />
          <input
            type="email"
            dir="ltr"
            placeholder="ایمیل"
            value={editForm.email}
            onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <select
              value={editForm.customer_type}
              onChange={(e) => setEditForm({ ...editForm, customer_type: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="BUYER">خریدار</option>
              <option value="TENANT">مستأجر</option>
              <option value="SELLER">فروشنده</option>
              <option value="LANDLORD">موجر</option>
              <option value="INVESTOR">سرمایه‌گذار</option>
            </select>
            <select
              value={editForm.readiness_level}
              onChange={(e) => setEditForm({ ...editForm, readiness_level: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="HIGH">آمادگی بالا</option>
              <option value="MEDIUM">آمادگی متوسط</option>
              <option value="LOW">در حال بررسی</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={editMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            {editMut.isPending ? "در حال ذخیره..." : "ذخیره تغییرات"}
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
