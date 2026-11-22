"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ArrowRight,
  CheckCircle2,
  Download,
  Edit3,
  Eye,
  FilePlus2,
  FileText,
  Lock,
  Paperclip,
  Printer,
  Trash2,
  Upload,
} from "lucide-react";
import { apiDownloadBlob, apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { ContractAmendmentItem, ContractItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";
import { useToast } from "@/components/ui/ToastProvider";
import { formatNumberFa } from "@/lib/formatters";

interface ContractAttachedDoc {
  id: string;
  title: string;
  category: string;
  access_level: string;
  created_at: string;
}

interface ContractDetail extends ContractItem {
  template_title?: string | null;
  terms_snapshot?: string;
  obligations_json?: Record<string, unknown>;
  documents?: ContractAttachedDoc[];
  amendments?: ContractAmendmentItem[];
  history?: {
    id: string;
    from_status: string;
    to_status: string;
    reason: string;
    changed_by_name: string;
    created_at: string;
  }[];
}

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();

  const [editOpen, setEditOpen] = useState(false);
  const [amendOpen, setAmendOpen] = useState(false);
  const [terminateOpen, setTerminateOpen] = useState(false);
  const [terminateReason, setTerminateReason] = useState("");

  const [previewDoc, setPreviewDoc] = useState<{ title: string; url: string; mime: string } | null>(null);

  const [editForm, setEditForm] = useState({
    contract_type: "SALE",
    amount: "0",
    deposit_amount: "0",
    rent_amount: "0",
    advance_payment: "0",
    remaining_amount: "0",
    payment_method: "",
    terms_snapshot: "",
  });

  const [amendForm, setAmendForm] = useState({
    title: "",
    reason: "",
    summary: "",
    adjusted_amount: "",
    approve_immediately: true,
  });

  const [docTitle, setDocTitle] = useState("");
  const [docCategory, setDocCategory] = useState("CONTRACT_ATTACHMENT");
  const [docFile, setDocFile] = useState<File | null>(null);

  const detailQ = useQuery({
    queryKey: ["contract-detail", id, activeAgencyId],
    enabled: !!accessToken && !!id,
    queryFn: async () =>
      (
        await apiFetch<ContractDetail>(`/api/v1/contracts/${id}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const contract = detailQ.data;
  const effAgencyId = activeAgencyId || contract?.agency_id;

  const statusMut = useMutation({
    mutationFn: async ({ status, reason = "" }: { status: string; reason?: string }) =>
      apiFetch(`/api/v1/contracts/${id}/status`, {
        method: "POST",
        token: accessToken,
        agencyId: effAgencyId,
        body: JSON.stringify({ status, reason }),
      }),
    onSuccess: () => {
      setTerminateOpen(false);
      setTerminateReason("");
      toast.success("وضعیت قرارداد به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["contract-detail", id] });
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const editMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/contracts/${id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: effAgencyId,
        body: JSON.stringify(editForm),
      }),
    onSuccess: () => {
      setEditOpen(false);
      toast.success("مفاد و مبالغ پیش‌نویس قرارداد ویرایش شد.");
      qc.invalidateQueries({ queryKey: ["contract-detail", id] });
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const archiveMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/contracts/${id}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: effAgencyId,
      }),
    onSuccess: () => {
      toast.success("قرارداد پیش‌نویس بایگانی شد.");
      qc.invalidateQueries({ queryKey: ["contracts"] });
      router.push("/dashboard/contracts");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const amendMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/contracts/${id}/amendments`, {
        method: "POST",
        token: accessToken,
        agencyId: effAgencyId,
        body: JSON.stringify({
          title: amendForm.title,
          reason: amendForm.reason,
          changes_json: {
            summary: amendForm.summary,
            ...(amendForm.adjusted_amount ? { adjusted_amount: amendForm.adjusted_amount } : {}),
          },
          approve_immediately: amendForm.approve_immediately,
        }),
      }),
    onSuccess: () => {
      setAmendOpen(false);
      setAmendForm({ title: "", reason: "", summary: "", adjusted_amount: "", approve_immediately: true });
      toast.success("الحاقیه رسمی قرارداد با موفقیت ثبت شد.");
      qc.invalidateQueries({ queryKey: ["contract-detail", id] });
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const uploadDocMut = useMutation({
    mutationFn: async () => {
      if (!docFile || !contract) throw new Error("فایل مدرک را انتخاب کنید.");
      const fd = new FormData();
      fd.append("file", docFile);
      fd.append("title", docTitle.trim() || docFile.name);
      fd.append("category", docCategory);
      fd.append("access_level", "AGENCY_INTERNAL");
      fd.append("contract_id", contract.id);
      if (contract.property_id) fd.append("property_id", contract.property_id);
      return apiFetch("/api/v1/documents/upload", {
        method: "POST",
        token: accessToken,
        agencyId: effAgencyId,
        body: fd,
      });
    },
    onSuccess: () => {
      setDocTitle("");
      setDocFile(null);
      toast.success("سند با موفقیت به قرارداد پیوست شد.");
      qc.invalidateQueries({ queryKey: ["contract-detail", id] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteDocMut = useMutation({
    mutationFn: async (docId: string) =>
      apiFetch(`/api/v1/documents/${docId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: effAgencyId,
      }),
    onSuccess: () => {
      toast.success("سند پیوست حذف شد.");
      qc.invalidateQueries({ queryKey: ["contract-detail", id] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const openInlinePreview = async (doc: ContractAttachedDoc) => {
    try {
      const headers: Record<string, string> = {};
      if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
      if (effAgencyId) headers["X-Agency-ID"] = effAgencyId;
      const res = await fetch(`/api/v1/documents/${doc.id}/content?inline=true`, { headers });
      if (!res.ok) throw new Error(`خطا در دریافت فایل (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setPreviewDoc({ title: doc.title, url, mime: blob.type || "application/octet-stream" });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "خطا در پیش‌نمایش فایل");
    }
  };

  if (detailQ.isLoading) return <LoadingState message="در حال بارگذاری پرونده قرارداد..." />;
  if (detailQ.error) {
    return <ErrorState message={(detailQ.error as Error).message} onRetry={() => detailQ.refetch()} />;
  }
  if (!contract) return <ErrorState message="قرارداد یافت نشد." />;

  const isEditable =
    contract.is_editable ??
    ["DRAFT", "PENDING_REVIEW", "PENDING_PARTIES_APPROVAL"].includes(contract.status);
  const isLocked = ["SIGNED", "ACTIVE", "COMPLETED"].includes(contract.status);

  const openEditModal = () => {
    setEditForm({
      contract_type: contract.contract_type,
      amount: contract.amount,
      deposit_amount: contract.deposit_amount,
      rent_amount: contract.rent_amount,
      advance_payment: contract.advance_payment,
      remaining_amount: contract.remaining_amount,
      payment_method: contract.payment_method || "",
      terms_snapshot: contract.terms_snapshot || "",
    });
    setEditOpen(true);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={`قرارداد ${contract.contract_number}`}
        subtitle={`کد رهگیری داخلی: ${contract.internal_tracking_code} — ملک: ${contract.property_title}`}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "قراردادها", href: "/dashboard/contracts" },
          { label: contract.contract_number },
        ]}
        actions={
          <div className="flex flex-wrap gap-2 print:hidden">
            {isEditable && (
              <>
                <button
                  type="button"
                  onClick={openEditModal}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                  ویرایش مفاد
                </button>
                {contract.status === "DRAFT" && (
                  <button
                    type="button"
                    onClick={() => statusMut.mutate({ status: "PENDING_REVIEW" })}
                    className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-amber-600 px-3 text-xs font-semibold text-white hover:bg-amber-700 whitespace-nowrap"
                  >
                    ارسال به بازبینی حقوقی
                  </button>
                )}
                {contract.status === "PENDING_REVIEW" && (
                  <button
                    type="button"
                    onClick={() => statusMut.mutate({ status: "PENDING_PARTIES_APPROVAL" })}
                    className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 text-xs font-semibold text-white hover:bg-indigo-700 whitespace-nowrap"
                  >
                    ارسال برای تأیید طرفین
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => statusMut.mutate({ status: "SIGNED" })}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  امضای نهایی
                </button>
                <button
                  type="button"
                  onClick={() => archiveMut.mutate()}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/30 px-3 text-xs font-semibold text-rose-700 dark:text-rose-300 whitespace-nowrap"
                >
                  <Archive className="h-3.5 w-3.5" />
                  بایگانی پیش‌نویس
                </button>
              </>
            )}

            {contract.status === "SIGNED" && (
              <button
                type="button"
                onClick={() => statusMut.mutate({ status: "ACTIVE" })}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-emerald-700 px-3.5 text-xs font-semibold text-white whitespace-nowrap"
              >
                فعال‌سازی و اجرای قرارداد
              </button>
            )}

            {contract.status === "ACTIVE" && (
              <button
                type="button"
                onClick={() => statusMut.mutate({ status: "COMPLETED" })}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-emerald-700 px-3.5 text-xs font-semibold text-white whitespace-nowrap"
              >
                تکمیل قرارداد
              </button>
            )}

            {isLocked && (
              <button
                type="button"
                onClick={() => setAmendOpen(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 text-xs font-semibold text-white hover:bg-amber-700 whitespace-nowrap"
              >
                <FilePlus2 className="h-4 w-4" />
                ثبت الحاقیه رسمی
              </button>
            )}

            {["SIGNED", "ACTIVE"].includes(contract.status) && (
              <button
                type="button"
                onClick={() => setTerminateOpen(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-rose-300 dark:border-rose-800 px-3 text-xs font-semibold text-rose-700 dark:text-rose-300 whitespace-nowrap"
              >
                فسخ قرارداد
              </button>
            )}

            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
            >
              <Printer className="h-4 w-4" />
              چاپ قرارداد
            </button>
            <Link
              href="/dashboard/contracts"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت
            </Link>
          </div>
        }
      />

      {isLocked && (
        <div className="flex items-center gap-2.5 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          <Lock className="h-4 w-4 shrink-0 text-amber-600" />
          <span>
            قرارداد پس از امضا قفل است و هرگونه تغییر یا اصلاح مستقیم در مفاد آن غیرمجاز می‌باشد؛ ثبت تغییر فقط از طریق «الحاقیه رسمی قرارداد» امکان‌پذیر است.
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
              <FileText className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              ارکان مالی و شرایط قرارداد
            </h2>
            <StatusText status={contract.status} />
          </div>

          <dl className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-3">
            <div>
              <dt className="text-slate-500 dark:text-slate-400">نوع قرارداد / معامله</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{contract.deal_type_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">مبلغ کل قرارداد</dt>
              <dd className="mt-1 font-bold text-teal-800 dark:text-teal-300">
                <MoneyDisplay amount={contract.amount} sourceCurrency={contract.currency} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">پیش‌پرداخت</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
                <MoneyDisplay amount={contract.advance_payment} sourceCurrency={contract.currency} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">مبلغ باقیمانده</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
                <MoneyDisplay amount={contract.remaining_amount} sourceCurrency={contract.currency} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">روش پرداخت</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
                {contract.payment_method || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">تاریخ شروع</dt>
              <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
                <DateDisplay value={contract.start_date} />
              </dd>
            </div>
            <div className="sm:col-span-3">
              <dt className="text-slate-500 dark:text-slate-400">ملک مرتبط</dt>
              <dd className="mt-1">
                <Link
                  href={`/dashboard/properties/${contract.property_id}`}
                  className="font-semibold text-teal-700 dark:text-teal-400 hover:underline"
                >
                  {contract.property_code} — {contract.property_title}
                </Link>
              </dd>
            </div>
          </dl>

          <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
            <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 mb-2">طرفین قرارداد</h3>
            {contract.parties.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">طرف قراردادی ثبت نشده است.</p>
            ) : (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {contract.parties.map((p) => (
                  <div
                    key={p.id}
                    className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 p-3 text-xs flex justify-between"
                  >
                    <span className="font-semibold text-slate-900 dark:text-slate-100">{p.full_name}</span>
                    <span className="font-mono text-slate-500 dark:text-slate-400">{p.party_role}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {contract.terms_snapshot && (
            <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
              <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 mb-2">متن و شروط قرارداد</h3>
              <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 dark:bg-slate-800/60 p-4 text-xs leading-relaxed text-slate-800 dark:text-slate-200">
                {contract.terms_snapshot}
              </pre>
            </div>
          )}

          {/* Amendments List */}
          <div className="border-t border-slate-200 dark:border-slate-800 pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                الحاقیه‌های رسمی قرارداد ({formatNumberFa((contract.amendments || []).length)})
              </h3>
              {isLocked && (
                <button
                  type="button"
                  onClick={() => setAmendOpen(true)}
                  className="text-xs font-semibold text-teal-700 dark:text-teal-400 hover:underline print:hidden"
                >
                  + ثبت الحاقیه جدید
                </button>
              )}
            </div>
            {(contract.amendments || []).length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">الحاقیه‌ای برای این قرارداد ثبت نشده است.</p>
            ) : (
              <div className="space-y-2.5">
                {(contract.amendments || []).map((am) => (
                  <div
                    key={am.id}
                    className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3.5 text-xs space-y-1.5"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-bold text-slate-900 dark:text-slate-100">
                        الحاقیه شماره {formatNumberFa(am.amendment_number)}: {am.title}
                      </span>
                      <div className="flex items-center gap-2">
                        <StatusText status={am.status} />
                        <DateDisplay value={am.created_at} className="text-[11px] text-slate-400" />
                      </div>
                    </div>
                    <div className="text-slate-600 dark:text-slate-300">علت الحاقیه: {am.reason}</div>
                    {am.changes_json && Object.keys(am.changes_json).length > 0 && (
                      <div className="rounded bg-white dark:bg-slate-900 px-2.5 py-1.5 text-[11px] text-slate-700 dark:text-slate-300">
                        {String(am.changes_json.summary || JSON.stringify(am.changes_json))}
                      </div>
                    )}
                    {am.approved_by_name && (
                      <div className="text-[11px] text-slate-400">تأییدکننده: {am.approved_by_name}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Right Column: Status History + Attached Documents */}
        <div className="space-y-4">
          <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-3">
              تاریخچه تغییرات وضعیت
            </h2>
            {(contract.history || []).length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">تغییر وضعیتی ثبت نشده است.</p>
            ) : (
              <div className="space-y-2.5 text-xs">
                {(contract.history || []).map((h) => (
                  <div
                    key={h.id}
                    className="rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3"
                  >
                    <div className="flex items-center justify-between font-semibold text-slate-900 dark:text-slate-100">
                      <span>
                        {h.from_status || "—"} ← {h.to_status}
                      </span>
                      <DateDisplay value={h.created_at} />
                    </div>
                    <div className="mt-1 text-slate-500 dark:text-slate-400">توسط: {h.changed_by_name}</div>
                    {h.reason && <div className="mt-1 text-slate-700 dark:text-slate-300">{h.reason}</div>}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4 print:hidden">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-800 pb-3">
              <Paperclip className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              اسناد و مدارک پیوست قرارداد ({formatNumberFa((contract.documents || []).length)})
            </h2>

            {(contract.documents || []).length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">مدرکی به این قرارداد پیوست نشده است.</p>
            ) : (
              <div className="space-y-2">
                {(contract.documents || []).map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-2.5 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-semibold text-slate-900 dark:text-slate-100">{doc.title}</div>
                      <div className="font-mono text-[10px] text-slate-400">{doc.category}</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      <button
                        type="button"
                        onClick={() => openInlinePreview(doc)}
                        title="پیش‌نمایش"
                        className="inline-flex h-7 w-7 items-center justify-center rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          apiDownloadBlob(`/api/v1/documents/${doc.id}/content`, {
                            token: accessToken,
                            agencyId: effAgencyId,
                            filenameFallback: doc.title,
                          })
                        }
                        title="دانلود"
                        className="inline-flex h-7 w-7 items-center justify-center rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-teal-700 dark:text-teal-400"
                      >
                        <Download className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteDocMut.mutate(doc.id)}
                        title="حذف سند"
                        className="inline-flex h-7 w-7 items-center justify-center rounded border border-rose-200 dark:border-rose-900 bg-white dark:bg-slate-900 text-rose-600"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                uploadDocMut.mutate();
              }}
              className="space-y-2 border-t border-slate-100 dark:border-slate-800 pt-3"
            >
              <input
                placeholder="عنوان مدرک پیوست (مثلاً نسخه اسکن‌شده مبایعه‌نامه)"
                value={docTitle}
                onChange={(e) => setDocTitle(e.target.value)}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs"
              />
              <select
                value={docCategory}
                onChange={(e) => setDocCategory(e.target.value)}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs"
              >
                <option value="CONTRACT_ATTACHMENT">مدرک پیوست قرارداد</option>
                <option value="DEED">سند مالکیت</option>
                <option value="IDENTITY">مدرک هویتی طرفین</option>
                <option value="CHEQUE_RECEIPT">تصویر چک / رسید مالی</option>
              </select>
              <input
                required
                type="file"
                onChange={(e) => setDocFile(e.target.files?.[0] || null)}
                className="block w-full text-xs text-slate-600 dark:text-slate-300"
              />
              <button
                type="submit"
                disabled={uploadDocMut.isPending || !docFile}
                className="inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                <Upload className="h-3.5 w-3.5" />
                {uploadDocMut.isPending ? "در حال آپلود..." : "آپلود و پیوست مدرک"}
              </button>
            </form>
          </section>
        </div>
      </div>

      {/* Edit Draft Contract Modal */}
      <ModalDrawer open={editOpen} onClose={() => setEditOpen(false)} title="ویرایش مفاد و مبالغ پیش‌نویس قرارداد">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            editMut.mutate();
          }}
          className="space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold">مبلغ کل</label>
              <input
                type="number"
                value={editForm.amount}
                onChange={(e) => setEditForm({ ...editForm, amount: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs tabular-nums"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold">پیش‌پرداخت</label>
              <input
                type="number"
                value={editForm.advance_payment}
                onChange={(e) => setEditForm({ ...editForm, advance_payment: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs tabular-nums"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold">باقیمانده</label>
              <input
                type="number"
                value={editForm.remaining_amount}
                onChange={(e) => setEditForm({ ...editForm, remaining_amount: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs tabular-nums"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold">روش پرداخت</label>
              <input
                value={editForm.payment_method}
                onChange={(e) => setEditForm({ ...editForm, payment_method: e.target.value })}
                className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 text-xs"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold">متن و شروط قرارداد</label>
            <textarea
              rows={4}
              value={editForm.terms_snapshot}
              onChange={(e) => setEditForm({ ...editForm, terms_snapshot: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-xs"
            />
          </div>
          <button
            type="submit"
            disabled={editMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white"
          >
            {editMut.isPending ? "در حال ذخیره..." : "ذخیره تغییرات قرارداد"}
          </button>
        </form>
      </ModalDrawer>

      {/* Contract Amendment Modal */}
      <ModalDrawer
        open={amendOpen}
        onClose={() => setAmendOpen(false)}
        title="ثبت الحاقیه رسمی قرارداد"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            amendMut.mutate();
          }}
          className="space-y-3"
        >
          <div>
            <label className="mb-1 block text-xs font-semibold">عنوان الحاقیه</label>
            <input
              required
              placeholder="مثلاً: اصلاح زمان تحویل ملک یا تمدید مهلت چک"
              value={amendForm.title}
              onChange={(e) => setAmendForm({ ...amendForm, title: e.target.value })}
              className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold">دلیل و مستندات الحاقیه</label>
            <input
              required
              placeholder="توافق طرفین طی صورتجلسه مورخ..."
              value={amendForm.reason}
              onChange={(e) => setAmendForm({ ...amendForm, reason: e.target.value })}
              className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold">شرح دقیق تغییرات توافق‌شده</label>
            <textarea
              required
              rows={3}
              placeholder="مفاد اصلاحی الحاقیه..."
              value={amendForm.summary}
              onChange={(e) => setAmendForm({ ...amendForm, summary: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold">مبلغ اصلاحی جدید (اختیاری)</label>
            <input
              type="number"
              value={amendForm.adjusted_amount}
              onChange={(e) => setAmendForm({ ...amendForm, adjusted_amount: e.target.value })}
              className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-xs tabular-nums"
            />
          </div>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={amendForm.approve_immediately}
              onChange={(e) => setAmendForm({ ...amendForm, approve_immediately: e.target.checked })}
              className="accent-teal-700"
            />
            تصویب و نهایی‌سازی همزمان الحاقیه
          </label>
          <button
            type="submit"
            disabled={amendMut.isPending}
            className="h-10 w-full rounded-lg bg-amber-600 text-xs font-semibold text-white hover:bg-amber-700"
          >
            {amendMut.isPending ? "در حال ثبت..." : "ثبت الحاقیه رسمی"}
          </button>
        </form>
      </ModalDrawer>

      {/* Terminate Contract Modal */}
      <ModalDrawer
        open={terminateOpen}
        onClose={() => setTerminateOpen(false)}
        title="ثبت فسخ قرارداد"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            statusMut.mutate({ status: "TERMINATED", reason: terminateReason });
          }}
          className="space-y-3"
        >
          <textarea
            required
            rows={3}
            placeholder="دلیل قانونی یا توافقی فسخ قرارداد را درج کنید (الزامی)..."
            value={terminateReason}
            onChange={(e) => setTerminateReason(e.target.value)}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3 text-xs"
          />
          <button
            type="submit"
            disabled={statusMut.isPending || !terminateReason.trim()}
            className="h-10 w-full rounded-lg bg-rose-700 text-xs font-semibold text-white"
          >
            تأیید و ثبت فسخ
          </button>
        </form>
      </ModalDrawer>

      {/* Document Inline Preview Modal */}
      <ModalDrawer
        open={!!previewDoc}
        onClose={() => {
          if (previewDoc) URL.revokeObjectURL(previewDoc.url);
          setPreviewDoc(null);
        }}
        title={previewDoc?.title || "پیش‌نمایش مدرک"}
        widthClass="max-w-3xl"
      >
        {previewDoc && (
          <div className="space-y-3">
            {previewDoc.mime.startsWith("image/") ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={previewDoc.url} alt={previewDoc.title} className="max-h-[70vh] w-full rounded-lg object-contain" />
            ) : previewDoc.mime === "application/pdf" ? (
              <iframe src={previewDoc.url} title={previewDoc.title} className="h-[70vh] w-full rounded-lg border" />
            ) : (
              <div className="rounded-lg border border-slate-200 p-6 text-center text-xs">
                پیش‌نمایش مرورگر برای این فرمت در دسترس نیست؛ لطفاً فایل را دانلود کنید.
              </div>
            )}
          </div>
        )}
      </ModalDrawer>
    </div>
  );
}
