"use client";
import { confirmDialog } from "@/lib/confirm-dialog";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Bath,
  BedDouble,
  Check,
  Download,
  Edit3,
  ExternalLink,
  Eye,
  EyeOff,
  FileText,
  History,
  MapPin,
  Maximize2,
  ShieldCheck,
  Star,
  Trash2,
  Upload,
  UserCheck,
  XCircle,
} from "lucide-react";
import { apiDownloadBlob, apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatArea, formatNumberFa, translateStatus } from "@/lib/formatters";
import type { DocumentItem, PropertyItem, PropertyVerificationData } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { PropertyGalleryLightbox } from "@/components/ui/PropertyGalleryLightbox";
import { SecureFileUploader, type QueuedUploadFile } from "@/components/ui/SecureFileUploader";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";
import { PropertyVirtualTourCard } from "@/components/virtual-tour/PropertyVirtualTourCard";

export default function DashboardPropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { accessToken, activeAgencyId, effectiveRole, hasPermission } = useAuth();
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [uploadQueue, setUploadQueue] = useState<QueuedUploadFile[]>([]);
  const [verDraft, setVerDraft] = useState<{
    physical_verified?: boolean;
    physical_notes?: string;
    deed_verified?: boolean;
    deed_notes?: string;
    owner_consent_verified?: boolean;
    owner_consent_notes?: string;
    evidence_document_id?: string | null;
    exception_override?: boolean;
    override_reason?: string;
    notes?: string;
  }>({});

  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [docCategory, setDocCategory] = useState("DEED");
  const [docAccessLevel, setDocAccessLevel] = useState("AGENCY_INTERNAL");
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docUploading, setDocUploading] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<{ title: string; url: string; mime: string } | null>(null);

  const propQ = useQuery({
    queryKey: ["dashboard-property-detail", params.id, activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<PropertyItem>(`/api/v1/properties/${params.id}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const targetAgencyId = activeAgencyId || propQ.data?.agency_id || null;

  const verificationQ = useQuery({
    queryKey: ["property-verification", params.id, targetAgencyId],
    enabled: !!accessToken && !!propQ.data,
    queryFn: async () =>
      (
        await apiFetch<PropertyVerificationData>(`/api/v1/properties/${params.id}/verification`, {
          token: accessToken,
          agencyId: targetAgencyId,
        })
      ).data,
  });

  const docsQ = useQuery({
    queryKey: ["property-documents", params.id, targetAgencyId],
    enabled: !!accessToken && !!targetAgencyId,
    queryFn: async () =>
      (
        await apiFetch<DocumentItem[]>(`/api/v1/documents?property_id=${params.id}&page_size=50`, {
          token: accessToken,
          agencyId: targetAgencyId,
        })
      ).data,
  });

  const agencyDocsQ = useQuery({
    queryKey: ["agency-documents-brief", targetAgencyId],
    enabled: !!accessToken && !!targetAgencyId,
    queryFn: async () =>
      (
        await apiFetch<DocumentItem[]>("/api/v1/documents?page_size=50", {
          token: accessToken,
          agencyId: targetAgencyId,
        })
      ).data,
  });

  const saveVerificationMut = useMutation({
    mutationFn: async (overrideMode: boolean) => {
      const cur = verificationQ.data;
      return apiFetch<PropertyVerificationData>(`/api/v1/properties/${params.id}/verification`, {
        method: "PUT",
        token: accessToken,
        agencyId: targetAgencyId,
        body: JSON.stringify({
          physical_verified: verDraft.physical_verified ?? cur?.physical_verified ?? false,
          physical_notes: verDraft.physical_notes ?? cur?.physical_notes ?? "",
          deed_verified: verDraft.deed_verified ?? cur?.deed_verified ?? false,
          deed_notes: verDraft.deed_notes ?? cur?.deed_notes ?? "",
          owner_consent_verified:
            verDraft.owner_consent_verified ?? cur?.owner_consent_verified ?? false,
          owner_consent_notes: verDraft.owner_consent_notes ?? cur?.owner_consent_notes ?? "",
          evidence_document_id:
            verDraft.evidence_document_id !== undefined
              ? verDraft.evidence_document_id || null
              : cur?.evidence_document_id || null,
          exception_override: overrideMode,
          override_reason: overrideMode ? verDraft.override_reason || "" : "",
          notes: verDraft.notes || "به‌روزرسانی چک‌لیست اصالت ملک",
        }),
      });
    },
    onSuccess: () => {
      setVerDraft({});
      setErrMsg(null);
      setNotice("وضعیت احراز اصالت ملک با موفقیت ثبت شد.");
      qc.invalidateQueries({ queryKey: ["property-verification", params.id] });
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const actionMut = useMutation({
    mutationFn: async (payload: {
      action: "submit" | "publish" | "unpublish" | "reject" | "delete";
      reason?: string;
    }) => {
      if (payload.action === "delete") {
        return apiFetch(`/api/v1/properties/${params.id}`, {
          method: "DELETE",
          token: accessToken,
          agencyId: targetAgencyId,
        });
      }
      if (payload.action === "unpublish") {
        return apiFetch(`/api/v1/properties/${params.id}/status`, {
          method: "POST",
          token: accessToken,
          agencyId: targetAgencyId,
          body: JSON.stringify({
            status: "DRAFT",
            reason: payload.reason?.trim() || "لغو انتشار از پورتال عمومی",
          }),
        });
      }
      if (payload.action === "reject") {
        return apiFetch(`/api/v1/properties/${params.id}/status`, {
          method: "POST",
          token: accessToken,
          agencyId: targetAgencyId,
          body: JSON.stringify({
            status: "REJECTED",
            reason: (payload.reason || "").trim(),
          }),
        });
      }
      return apiFetch(`/api/v1/properties/${params.id}/${payload.action}`, {
        method: "POST",
        token: accessToken,
        agencyId: targetAgencyId,
      });
    },
    onSuccess: (_, vars) => {
      setErrMsg(null);
      if (vars.action === "delete") {
        qc.invalidateQueries({ queryKey: ["agency-properties"] });
        router.push("/dashboard/properties");
        return;
      }
      if (vars.action === "reject") {
        setRejectOpen(false);
        setRejectReason("");
        setNotice("ملک رد شد و دلیل رد در پرونده ثبت گردید.");
      } else if (vars.action === "unpublish") {
        setNotice("انتشار ملک در پورتال عمومی لغو شد.");
      } else {
        setNotice("وضعیت ملک با موفقیت به‌روزرسانی شد.");
      }
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
      qc.invalidateQueries({ queryKey: ["agency-properties"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteDocMut = useMutation({
    mutationFn: async (docId: string) =>
      apiFetch(`/api/v1/documents/${docId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: targetAgencyId,
      }),
    onSuccess: () => {
      setNotice("سند از پرونده ملک حذف (بایگانی) شد.");
      qc.invalidateQueries({ queryKey: ["property-documents", params.id] });
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
      qc.invalidateQueries({ queryKey: ["agency-documents-brief"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const handleUploadPropertyDoc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docFile || !targetAgencyId) {
      setErrMsg("لطفاً فایل سند را انتخاب کنید.");
      return;
    }
    setErrMsg(null);
    setDocUploading(true);
    try {
      const form = new FormData();
      form.append("file", docFile);
      form.append("title", docTitle.trim() || docFile.name);
      form.append("category", docCategory);
      form.append("access_level", docAccessLevel);
      form.append("property_id", params.id);
      await apiFetch("/api/v1/documents/upload", {
        method: "POST",
        token: accessToken,
        agencyId: targetAgencyId,
        body: form,
      });
      setDocFile(null);
      setDocTitle("");
      setNotice("سند پیوست ملک با موفقیت بارگذاری شد.");
      qc.invalidateQueries({ queryKey: ["property-documents", params.id] });
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
      qc.invalidateQueries({ queryKey: ["agency-documents-brief"] });
    } catch (err) {
      setErrMsg(err instanceof Error ? err.message : "خطا در آپلود سند");
    } finally {
      setDocUploading(false);
    }
  };

  const openInlinePreview = async (doc: { id: string; title: string; versions?: { mime_type: string }[] }) => {
    try {
      const headers: Record<string, string> = {};
      if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
      if (targetAgencyId) headers["X-Agency-ID"] = targetAgencyId;
      const res = await fetch(`/api/v1/documents/${doc.id}/content?inline=true`, { headers });
      if (!res.ok) throw new Error(`خطا در دریافت پیش‌نمایش (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setPreviewDoc({
        title: doc.title,
        url,
        mime: doc.versions?.[0]?.mime_type || blob.type || "application/pdf",
      });
    } catch (err) {
      setErrMsg(err instanceof Error ? err.message : "خطا در پیش‌نمایش سند");
    }
  };

  const uploadSingleMedia = async (item: QueuedUploadFile) => {
    setUploadQueue((prev) =>
      prev.map((q) => (q.id === item.id ? { ...q, status: "UPLOADING", progress: 45, error: undefined } : q))
    );
    try {
      const form = new FormData();
      form.append("file", item.file);
      form.append("title", item.title || item.file.name);
      form.append("is_cover", item.isCover ? "true" : "false");
      form.append("is_public", "true");
      await apiFetch(`/api/v1/properties/${params.id}/media/upload`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: form,
      });
      setUploadQueue((prev) =>
        prev.map((q) => (q.id === item.id ? { ...q, status: "DONE", progress: 100 } : q))
      );
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "خطا در آپلود";
      setUploadQueue((prev) =>
        prev.map((q) => (q.id === item.id ? { ...q, status: "ERROR", error: msg } : q))
      );
      setErrMsg(msg);
    }
  };

  const handleUploadAll = async () => {
    setErrMsg(null);
    const pending = uploadQueue.filter((q) => q.status === "READY" || q.status === "ERROR");
    for (const item of pending) {
      await uploadSingleMedia(item);
    }
    setNotice("تصاویر انتخاب‌شده با موفقیت در گالری ملک ذخیره شدند.");
  };

  const reorderMut = useMutation({
    mutationFn: async ({ orderedIds, coverId }: { orderedIds: string[]; coverId?: string }) =>
      apiFetch(`/api/v1/properties/${params.id}/media/reorder`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          ordered_media_ids: orderedIds,
          cover_media_id: coverId || null,
        }),
      }),
    onSuccess: () => {
      setNotice("ترتیب تصاویر و کاور اصلی ملک به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteMediaMut = useMutation({
    mutationFn: async (mediaId: string) =>
      apiFetch(`/api/v1/properties/${params.id}/media/${mediaId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setNotice("تصویر از گالری ملک حذف شد.");
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const property = propQ.data;
  const canPublish =
    effectiveRole === "SUPER_ADMIN" ||
    effectiveRole === "AGENCY_MANAGER" ||
    hasPermission("property.publish");

  const groupedAmenities = useMemo(() => {
    if (!property?.amenities?.length) return [];
    const map = new Map<string, typeof property.amenities>();
    for (const am of property.amenities) {
      const grp = am.category_name_fa || "سایر امکانات";
      const list = map.get(grp) || [];
      list.push(am);
      map.set(grp, list);
    }
    return Array.from(map.entries());
  }, [property?.amenities]);

  const moveMedia = (idx: number, dir: -1 | 1) => {
    if (!property?.media_items) return;
    const list = [...property.media_items];
    const target = idx + dir;
    if (target < 0 || target >= list.length) return;
    const [moved] = list.splice(idx, 1);
    list.splice(target, 0, moved);
    reorderMut.mutate({ orderedIds: list.map((m) => m.id) });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={property ? `${property.title}` : "جزئیات فایل ملکی"}
        subtitle={
          property ? `کد ملک: ${property.property_code} — ${property.agency_name}` : undefined
        }
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "فهرست املاک", href: "/dashboard/properties" },
          { label: property?.property_code || "جزئیات" },
        ]}
        actions={
          property ? (
            <div className="flex flex-wrap gap-2">
              <Link
                href={`/dashboard/properties/${property.id}/edit`}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 whitespace-nowrap"
              >
                <Edit3 className="h-3.5 w-3.5" />
                ویرایش مشخصات
              </Link>
              {property.status === "DRAFT" && (
                <button
                  type="button"
                  disabled={actionMut.isPending}
                  onClick={() => actionMut.mutate({ action: "submit" })}
                  className="h-9 rounded-lg bg-amber-600 px-3.5 text-xs font-semibold text-white hover:bg-amber-700 whitespace-nowrap"
                >
                  ارسال برای تأیید
                </button>
              )}
              {property.status !== "PUBLISHED" && canPublish && (
                <button
                  type="button"
                  disabled={actionMut.isPending}
                  onClick={() => actionMut.mutate({ action: "publish" })}
                  className="h-9 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 dark:bg-teal-600 whitespace-nowrap"
                >
                  تأیید و انتشار در پورتال
                </button>
              )}
              {property.status === "PUBLISHED" && canPublish && (
                <button
                  type="button"
                  disabled={actionMut.isPending}
                  onClick={() => actionMut.mutate({ action: "unpublish" })}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-3.5 text-xs font-semibold text-amber-900 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300 whitespace-nowrap"
                >
                  <EyeOff className="h-3.5 w-3.5" />
                  لغو انتشار
                </button>
              )}
              {canPublish && property.status !== "REJECTED" && (
                <button
                  type="button"
                  onClick={() => {
                    setRejectOpen(true);
                    setRejectReason("");
                  }}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-rose-300 bg-rose-50 px-3.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300 whitespace-nowrap"
                >
                  <XCircle className="h-3.5 w-3.5" />
                  رد فایل
                </button>
              )}
              <Link
                href={`/properties/${property.id}`}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 whitespace-nowrap"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                نمای عمومی
              </Link>
              <button
                type="button"
                disabled={actionMut.isPending}
                onClick={async () => {
                    if (await confirmDialog({ title: "تأیید حذف", message: `آیا از حذف (بایگانی) ملک «${property.title}» مطمئن هستید؟`, danger: true })) {
                      actionMut.mutate({ action: "delete" });
                    }
                  }}
                className="inline-flex h-9 items-center gap-1 rounded-lg border border-rose-200 bg-white px-3 text-xs font-semibold text-rose-600 hover:bg-rose-50 dark:border-rose-900/60 dark:bg-slate-900 dark:text-rose-400 whitespace-nowrap"
              >
                <Trash2 className="h-3.5 w-3.5" />
                حذف
              </button>
            </div>
          ) : null
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {property && (property.status === "REJECTED" || property.latest_rejection_reason) && (
        <div className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400" />
          <div>
            <div className="font-bold">این فایل ملک رد شده است</div>
            <p className="mt-1 leading-relaxed">
              دلیل ثبت‌شده: {property.latest_rejection_reason || "دلیل ثبت نشده است"}
            </p>
          </div>
        </div>
      )}

      {propQ.isLoading ? (
        <LoadingState />
      ) : propQ.error instanceof Error ? (
        <ErrorState message={propQ.error.message} onRetry={() => propQ.refetch()} />
      ) : property ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-8">
            <PropertyGalleryLightbox
              title={property.title}
              mediaItems={property.media_items || []}
            />

            {/* Existing Gallery Reorder & Cover Manager */}
            {property.media_items && property.media_items.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                  مدیریت ترتیب و تصویر کاور گالری
                </h3>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {property.media_items.map((m, idx) => (
                    <div
                      key={m.id}
                      className={`overflow-hidden rounded-lg border p-1.5 text-[11px] ${
                        m.is_cover
                          ? "border-amber-500 bg-amber-50/40 dark:border-amber-500 dark:bg-amber-950/20"
                          : "border-slate-200 dark:border-slate-800"
                      }`}
                    >
                      <img
                        src={m.url}
                        alt={m.title || property.title}
                        className="aspect-[16/10] w-full rounded object-cover"
                      />
                      <div className="mt-1.5 flex items-center justify-between gap-1">
                        <button
                          type="button"
                          onClick={() =>
                            reorderMut.mutate({
                              orderedIds: property.media_items.map((x) => x.id),
                              coverId: m.id,
                            })
                          }
                          className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-semibold ${
                            m.is_cover
                              ? "bg-amber-500 text-white"
                              : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                          }`}
                        >
                          <Star className="h-2.5 w-2.5" />
                          {m.is_cover ? "کاور" : "کاور کن"}
                        </button>
                        <div className="flex items-center gap-0.5">
                          <button
                            type="button"
                            disabled={idx === 0}
                            onClick={() => moveMedia(idx, -1)}
                            className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:hover:bg-slate-800"
                          >
                            <ArrowRight className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            disabled={idx === property.media_items.length - 1}
                            onClick={() => moveMedia(idx, 1)}
                            className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:hover:bg-slate-800"
                          >
                            <ArrowLeft className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteMediaMut.mutate(m.id)}
                            className="rounded p-1 text-rose-600 hover:bg-rose-50 dark:text-rose-400"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Secure Multi-File Uploader with Live Pre-Upload Preview */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                آپلود تصاویر جدید با پیش‌نمایش و بزرگنمایی قبل از ارسال
              </h3>
              <SecureFileUploader
                accept="image/jpeg,image/png,image/webp"
                allowedExtensions={["jpg", "jpeg", "png", "webp"]}
                multiple
                allowCoverSelect
                queue={uploadQueue}
                onQueueChange={setUploadQueue}
                onUploadSingle={uploadSingleMedia}
                onUploadAll={handleUploadAll}
              />
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4 dark:border-slate-800">
                <div className="flex items-center gap-2 text-xs">
                  <StatusText status={property.status} />
                  <span className="font-semibold text-teal-700 dark:text-teal-400">
                    {property.deal_type.name_fa} · {property.property_type.name_fa}
                  </span>
                </div>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  ثبت‌شده در <DateDisplay value={property.created_at} />
                </span>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/60 sm:grid-cols-4">
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">زیربنا</div>
                  <div className="mt-1 flex items-center gap-1.5 text-sm font-bold tabular-nums">
                    <Maximize2 className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    {formatArea(property.built_area_sqm)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">خواب</div>
                  <div className="mt-1 flex items-center gap-1.5 text-sm font-bold tabular-nums">
                    <BedDouble className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    {formatNumberFa(property.bedrooms)} خواب
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">سرویس</div>
                  <div className="mt-1 flex items-center gap-1.5 text-sm font-bold tabular-nums">
                    <Bath className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    {formatNumberFa(property.bathrooms)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">سند</div>
                  <div className="mt-1 text-sm font-bold">{property.deed_type}</div>
                </div>
              </div>

              {property.location && (
                <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-800/60">
                  <div className="flex items-center gap-1.5 font-bold text-slate-900 dark:text-slate-100">
                    <MapPin className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    موقعیت مکانی و آدرس داخلی
                  </div>
                  <p className="mt-1.5 text-slate-600 dark:text-slate-300">
                    {property.location.province}، {property.location.city}
                    {property.location.district ? ` — منطقه ${property.location.district}` : ""}
                    {property.location.neighborhood ? ` (${property.location.neighborhood})` : ""}
                  </p>
                  {property.location.full_address && (
                    <p className="mt-1 font-medium text-slate-800 dark:text-slate-200">
                      نشانی دقیق: {property.location.full_address}
                    </p>
                  )}
                </div>
              )}

              {property.description && (
                <div className="mt-5">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">توضیحات</h3>
                  <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                    {property.description}
                  </p>
                </div>
              )}

              {groupedAmenities.length > 0 && (
                <div className="mt-5 border-t border-slate-100 pt-4 dark:border-slate-800 space-y-3">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    امکانات و تجهیزات دسته‌بندی‌شده
                  </h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {groupedAmenities.map(([catName, list]) => (
                      <div
                        key={catName}
                        className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-slate-800/40"
                      >
                        <div className="mb-2 text-xs font-bold text-teal-700 dark:text-teal-400">
                          {catName}
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {list.map((am) => {
                            const extraVal = am.value_number
                              ? `${formatNumberFa(am.value_number)} ${am.unit_label || ""}`.trim()
                              : am.value_text;
                            return (
                              <span
                                key={am.code}
                                className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium dark:border-slate-700 dark:bg-slate-900"
                              >
                                <Check className="h-3 w-3 text-teal-700 dark:text-teal-400" />
                                <span>{am.name_fa}</span>
                                {extraVal && (
                                  <span className="font-mono text-[11px] font-bold text-teal-700 dark:text-teal-300">
                                    ({extraVal})
                                  </span>
                                )}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Linked Property Documents Manager */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
                <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <FileText className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  اسناد و مدارک پیوست ملک
                </h3>
                <span className="tabular-nums text-xs text-slate-500">
                  {(docsQ.data || property.documents || []).length} سند
                </span>
              </div>

              <form onSubmit={handleUploadPropertyDoc} className="grid grid-cols-1 gap-2.5 rounded-lg border border-slate-200 bg-slate-50/80 p-3.5 dark:border-slate-800 dark:bg-slate-800/40 sm:grid-cols-12">
                <input
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  placeholder="عنوان سند (مثلاً تصویر سند تک‌برگ)..."
                  className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950 sm:col-span-4"
                />
                <select
                  value={docCategory}
                  onChange={(e) => setDocCategory(e.target.value)}
                  className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950 sm:col-span-3"
                >
                  <option value="DEED">سند مالکیت</option>
                  <option value="IDENTITY">احراز هویت مالک</option>
                  <option value="CONTRACT">قرارداد / مبایعه‌نامه</option>
                  <option value="INSPECTION">گزارش بازدید</option>
                  <option value="GENERAL">عمومی</option>
                </select>
                <select
                  value={docAccessLevel}
                  onChange={(e) => setDocAccessLevel(e.target.value)}
                  className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950 sm:col-span-2"
                >
                  <option value="AGENCY_INTERNAL">داخلی آژانس</option>
                  <option value="CONFIDENTIAL">محرمانه</option>
                  <option value="SHARED_COOP">همکاری</option>
                </select>
                <div className="flex items-center gap-2 sm:col-span-3">
                  <input
                    type="file"
                    onChange={(e) => setDocFile(e.target.files?.[0] || null)}
                    className="w-full text-[11px] file:ml-2 file:rounded file:border-0 file:bg-slate-200 file:px-2 file:py-1 file:text-[11px] file:font-semibold dark:file:bg-slate-700"
                  />
                  <button
                    type="submit"
                    disabled={docUploading || !docFile}
                    className="inline-flex h-9 shrink-0 items-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50 whitespace-nowrap"
                  >
                    <Upload className="h-3.5 w-3.5" />
                    {docUploading ? "آپلود..." : "پیوست"}
                  </button>
                </div>
              </form>

              {(docsQ.data || property.documents || []).length > 0 ? (
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  {(docsQ.data || property.documents || []).map((d) => (
                    <div key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-xs">
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{d.title}</div>
                        <div className="text-[11px] text-slate-500">
                          {translateStatus(d.category)} · {translateStatus(d.access_level)} ·{" "}
                          <DateDisplay value={d.created_at} />
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => openInlinePreview(d)}
                          className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 bg-white px-2 text-[11px] font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                        >
                          <Eye className="h-3 w-3" />
                          پیش‌نمایش
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            apiDownloadBlob(`/api/v1/documents/${d.id}/content`, {
                              token: accessToken,
                              agencyId: targetAgencyId,
                              filenameFallback: `${d.title}.pdf`,
                            }).catch((e) => setErrMsg(e instanceof Error ? e.message : "خطای دانلود"))
                          }
                          className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 bg-white px-2 text-[11px] font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                        >
                          <Download className="h-3 w-3" />
                          دانلود
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            if (await confirmDialog({ title: "تأیید حذف", message: `حذف سند «${d.title}»؟`, danger: true })) {
                              deleteDocMut.mutate(d.id);
                            }
                          }}
                          className="inline-flex h-7 items-center rounded border border-rose-200 bg-rose-50 px-2 text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400">هنوز سندی به این ملک پیوست نشده است.</p>
              )}
            </div>
          </div>

          <div className="space-y-6 lg:col-span-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                ارزش‌گذاری و شرایط مالی
              </h3>
              <div className="mt-3">
                {property.deal_type.is_rental ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>ودیعه:</span>
                      <MoneyDisplay
                        amount={property.deposit_amount}
                        sourceCurrency={property.currency}
                        className="font-bold"
                      />
                    </div>
                    <div className="flex justify-between">
                      <span>اجاره ماهانه:</span>
                      <MoneyDisplay
                        amount={property.rent_amount}
                        sourceCurrency={property.currency}
                        className="font-bold text-teal-700 dark:text-teal-300"
                      />
                    </div>
                  </div>
                ) : (
                  <MoneyDisplay
                    amount={property.total_price}
                    sourceCurrency={property.currency}
                    className="text-xl font-bold text-teal-800 dark:text-teal-300"
                  />
                )}
              </div>
            </div>

            <PropertyVirtualTourCard
              property={property}
              onCreated={() => propQ.refetch()}
            />

            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <UserCheck className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                مشاوران و مالکین مرتبط
              </h3>
              <div className="space-y-3 text-xs">
                <div>
                  <div className="mb-1 text-slate-500 dark:text-slate-400">مشاوران مسئول:</div>
                  {property.assigned_agents && property.assigned_agents.length > 0 ? (
                    property.assigned_agents.map((a) => (
                      <div key={a.membership_id} className="font-semibold">
                        {a.full_name} ({a.role})
                      </div>
                    ))
                  ) : (
                    <span className="text-slate-400">تخصیص نیافته</span>
                  )}
                </div>
                <div className="border-t border-slate-100 pt-2 dark:border-slate-800">
                  <div className="mb-1 text-slate-500 dark:text-slate-400">مالکین (مطابق سیاست دسترسی):</div>
                  {property.owners && property.owners.length > 0 ? (
                    property.owners.map((o) => (
                      <div key={o.id} className="flex justify-between py-1">
                        <span className="font-semibold">{o.full_name}</span>
                        <span className="font-mono text-slate-500">{o.phone_number || "محفوظ"}</span>
                      </div>
                    ))
                  ) : (
                    <span className="text-slate-400">مخفی یا ثبت‌نشده</span>
                  )}
                </div>
              </div>
            </div>

            {/* Authenticity Verification Checklist */}
            {verificationQ.data && (() => {
              const ver = verificationQ.data;
              const phys = verDraft.physical_verified ?? ver.physical_verified;
              const deed = verDraft.deed_verified ?? ver.deed_verified;
              const consent = verDraft.owner_consent_verified ?? ver.owner_consent_verified;
              const evDoc =
                verDraft.evidence_document_id !== undefined
                  ? verDraft.evidence_document_id || ""
                  : ver.evidence_document_id || "";
              const canOverride =
                effectiveRole === "SUPER_ADMIN" || effectiveRole === "AGENCY_MANAGER";
              return (
                <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                  <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2.5 dark:border-slate-800">
                    <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-900 dark:text-slate-100">
                      <ShieldCheck className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      احراز اصالت پیش از انتشار
                    </h3>
                    <StatusText status={ver.verification_status} />
                  </div>

                  {ver.anomaly_flags && ver.anomaly_flags.length > 0 && (
                    <div className="space-y-1.5 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                      {ver.anomaly_flags.map((flag, i) => (
                        <div key={`${flag.code}-${i}`} className="flex items-start gap-1.5">
                          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700 dark:text-amber-400" />
                          <span>{flag.message}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="space-y-2.5 text-xs">
                    <label className="flex items-center gap-2 font-semibold">
                      <input
                        type="checkbox"
                        checked={phys}
                        onChange={(e) =>
                          setVerDraft((d) => ({ ...d, physical_verified: e.target.checked }))
                        }
                        className="h-4 w-4 accent-teal-700"
                      />
                      تأیید وجود فیزیکی ملک
                    </label>
                    <input
                      placeholder="توضیح بازدید فیزیکی..."
                      value={verDraft.physical_notes ?? ver.physical_notes ?? ""}
                      onChange={(e) =>
                        setVerDraft((d) => ({ ...d, physical_notes: e.target.value }))
                      }
                      className="h-8 w-full rounded border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                    />

                    <label className="flex items-center gap-2 font-semibold">
                      <input
                        type="checkbox"
                        checked={deed}
                        onChange={(e) =>
                          setVerDraft((d) => ({ ...d, deed_verified: e.target.checked }))
                        }
                        className="h-4 w-4 accent-teal-700"
                      />
                      تأیید بررسی اصالت سند
                    </label>
                    <input
                      placeholder="توضیح وضعیت سند..."
                      value={verDraft.deed_notes ?? ver.deed_notes ?? ""}
                      onChange={(e) =>
                        setVerDraft((d) => ({ ...d, deed_notes: e.target.value }))
                      }
                      className="h-8 w-full rounded border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                    />

                    <label className="flex items-center gap-2 font-semibold">
                      <input
                        type="checkbox"
                        checked={consent}
                        onChange={(e) =>
                          setVerDraft((d) => ({ ...d, owner_consent_verified: e.target.checked }))
                        }
                        className="h-4 w-4 accent-teal-700"
                      />
                      تأیید رضایت مالک برای انتشار
                    </label>
                    <input
                      placeholder="توضیح رضایت مالک..."
                      value={verDraft.owner_consent_notes ?? ver.owner_consent_notes ?? ""}
                      onChange={(e) =>
                        setVerDraft((d) => ({ ...d, owner_consent_notes: e.target.value }))
                      }
                      className="h-8 w-full rounded border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                    />

                    <div>
                      <label className="mb-1 block text-[11px] text-slate-500">
                        سند/مدرک پیوست احراز
                      </label>
                      <select
                        value={evDoc}
                        onChange={(e) =>
                          setVerDraft((d) => ({ ...d, evidence_document_id: e.target.value || null }))
                        }
                        className="h-8 w-full rounded border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                      >
                        <option value="">بدون سند پیوست</option>
                        {(agencyDocsQ.data || []).map((doc) => (
                          <option key={doc.id} value={doc.id}>
                            {doc.title} ({doc.category})
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      type="button"
                      disabled={saveVerificationMut.isPending}
                      onClick={() => saveVerificationMut.mutate(false)}
                      className="h-9 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                    >
                      ذخیره وضعیت احراز اصالت
                    </button>

                    {canOverride &&
                      ver.verification_status !== "VERIFIED" &&
                      ver.verification_status !== "EXCEPTION_APPROVED" && (
                        <div className="border-t border-slate-100 pt-2.5 dark:border-slate-800 space-y-2">
                          <input
                            placeholder="دلیل ثبت استثنای مجاز (حداقل ۵ کاراکتر)..."
                            value={verDraft.override_reason ?? ver.override_reason ?? ""}
                            onChange={(e) =>
                              setVerDraft((d) => ({ ...d, override_reason: e.target.value }))
                            }
                            className="h-8 w-full rounded border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                          />
                          <button
                            type="button"
                            disabled={saveVerificationMut.isPending}
                            onClick={() => saveVerificationMut.mutate(true)}
                            className="h-8 w-full rounded-lg border border-amber-400 bg-amber-50 text-[11px] font-semibold text-amber-900 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                          >
                            ثبت استثنای مجاز با Audit
                          </button>
                        </div>
                      )}

                    {ver.history && ver.history.length > 0 && (
                      <div className="border-t border-slate-100 pt-2 dark:border-slate-800 space-y-1">
                        <div className="text-[11px] font-semibold text-slate-500">
                          تاریخچه تغییر وضعیت احراز
                        </div>
                        {ver.history.slice(0, 4).map((h) => (
                          <div key={h.id} className="flex justify-between text-[10px] text-slate-500">
                            <span>
                              {h.from_status} ➔ {h.to_status} ({h.changed_by_name})
                            </span>
                            <DateDisplay value={h.created_at} />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}

            {property.status_history && property.status_history.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-2.5">
                <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <History className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  تاریخچه وضعیت انتشار ملک
                </h3>
                <div className="space-y-2 text-xs">
                  {property.status_history.map((sh) => (
                    <div
                      key={sh.id}
                      className="rounded-lg border border-slate-100 bg-slate-50/70 p-2.5 dark:border-slate-800 dark:bg-slate-800/40"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold">
                          {translateStatus(sh.from_status)} ➔ {translateStatus(sh.to_status)}
                        </span>
                        <DateDisplay value={sh.changed_at} className="text-[11px] text-slate-500" />
                      </div>
                      {sh.reason && (
                        <p className="mt-1 text-[11px] text-slate-600 dark:text-slate-300">
                          توضیح: {sh.reason}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              type="button"
              onClick={() => router.push("/dashboard/properties")}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              بازگشت به فهرست املاک
            </button>
          </div>
        </div>
      ) : null}

      <ModalDrawer
        open={rejectOpen}
        onClose={() => {
          setRejectOpen(false);
          setRejectReason("");
        }}
        title={`رد فایل ملک ${property?.property_code || ""}`}
        subtitle="درج دلیل رد الزامی است و برای مشاور نمایش داده می‌شود."
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-700 dark:text-slate-300">
              دلیل رد ملک *
            </label>
            <textarea
              rows={4}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="مثال: متراژ اعلام‌شده با سند هم‌خوانی ندارد..."
              className="w-full rounded-lg border border-slate-300 bg-white p-3 text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
          </div>
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setRejectOpen(false)}
              className="h-9 rounded-lg border border-slate-300 px-4 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
            >
              انصراف
            </button>
            <button
              type="button"
              disabled={!rejectReason.trim() || actionMut.isPending}
              onClick={() =>
                actionMut.mutate({ action: "reject", reason: rejectReason.trim() })
              }
              className="h-9 rounded-lg bg-rose-600 px-4 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
            >
              {actionMut.isPending ? "در حال ثبت..." : "ثبت رد فایل"}
            </button>
          </div>
        </div>
      </ModalDrawer>

      <ModalDrawer
        open={Boolean(previewDoc)}
        onClose={() => {
          if (previewDoc?.url) URL.revokeObjectURL(previewDoc.url);
          setPreviewDoc(null);
        }}
        title={previewDoc?.title || "پیش‌نمایش سند"}
        widthClass="max-w-3xl"
      >
        {previewDoc &&
          (previewDoc.mime.startsWith("image/") ? (
            <img
              src={previewDoc.url}
              alt={previewDoc.title}
              className="max-h-[75vh] w-full rounded-lg object-contain"
            />
          ) : (
            <iframe
              src={previewDoc.url}
              title={previewDoc.title}
              className="h-[75vh] w-full rounded-lg border border-slate-200 dark:border-slate-800"
            />
          ))}
      </ModalDrawer>
    </div>
  );
}
