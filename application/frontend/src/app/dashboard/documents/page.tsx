"use client";
import { confirmDialog } from "@/lib/confirm-dialog";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Edit3, Eye, FileText, Plus, Trash2 } from "lucide-react";
import { apiDownloadBlob, apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { ContractItem, CustomerItem, DocumentItem, PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { SecureFileUploader, type QueuedUploadFile } from "@/components/ui/SecureFileUploader";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

const CATEGORY_LABELS: Record<string, string> = {
  DEED: "سند مالکیت",
  TITLE_DEED: "سند مالکیت",
  CONTRACT: "قرارداد",
  IDENTITY: "مدرک هویتی",
  INSPECTION: "گزارش کارشناسی / بازدید",
  GENERAL: "عمومی",
};

const ACCESS_LABELS: Record<string, string> = {
  PUBLIC: "عمومی",
  AGENCY_INTERNAL: "داخلی آژانس",
  CONFIDENTIAL: "محرمانه (مدیر/مالی)",
};

export default function DocumentsVaultPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<DocumentItem | null>(null);
  const [previewDoc, setPreviewDoc] = useState<{ title: string; url: string; mime: string } | null>(null);
  const [catFilter, setCatFilter] = useState("");
  const [propertyFilter, setPropertyFilter] = useState("");
  const [customerFilter, setCustomerFilter] = useState("");
  const [contractFilter, setContractFilter] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [uploadQueue, setUploadQueue] = useState<QueuedUploadFile[]>([]);

  const [form, setForm] = useState({
    title: "",
    category: "TITLE_DEED",
    access_level: "AGENCY_INTERNAL",
    property_id: "",
    customer_id: "",
    contract_id: "",
    file_key: "",
  });

  const [editForm, setEditForm] = useState({
    title: "",
    category: "GENERAL",
    access_level: "AGENCY_INTERNAL",
    property_id: "",
    customer_id: "",
    contract_id: "",
  });

  const docsQ = useQuery({
    queryKey: ["documents", activeAgencyId, catFilter, propertyFilter, customerFilter, contractFilter],
    enabled: !!accessToken,
    queryFn: async () => {
      const sp = new URLSearchParams({ page_size: "100" });
      if (catFilter) sp.set("category", catFilter);
      if (propertyFilter) sp.set("property_id", propertyFilter);
      if (customerFilter) sp.set("customer_id", customerFilter);
      if (contractFilter) sp.set("contract_id", contractFilter);
      return (
        await apiFetch<DocumentItem[]>(`/api/v1/documents?${sp.toString()}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const refAgencyId = activeAgencyId || editTarget?.agency_id || null;

  const propsQ = useQuery({
    queryKey: ["docs-ref-properties", refAgencyId],
    enabled: !!accessToken && !!refAgencyId,
    queryFn: async () =>
      (
        await apiFetch<PropertyItem[]>("/api/v1/properties?page_size=100", {
          token: accessToken,
          agencyId: refAgencyId,
        })
      ).data,
  });

  const custsQ = useQuery({
    queryKey: ["docs-ref-customers", refAgencyId],
    enabled: !!accessToken && !!refAgencyId,
    queryFn: async () =>
      (
        await apiFetch<CustomerItem[]>("/api/v1/customers?page_size=100", {
          token: accessToken,
          agencyId: refAgencyId,
        })
      ).data,
  });

  const contractsQ = useQuery({
    queryKey: ["docs-ref-contracts", refAgencyId],
    enabled: !!accessToken && !!refAgencyId,
    queryFn: async () =>
      (
        await apiFetch<ContractItem[]>("/api/v1/contracts?page_size=100", {
          token: accessToken,
          agencyId: refAgencyId,
        })
      ).data,
  });

  const uploadFile = uploadQueue[0]?.file || null;

  const createMut = useMutation({
    mutationFn: async () => {
      if (!activeAgencyId) {
        throw new Error("برای آپلود یا ثبت سند جدید، ابتدا از منوی بالای صفحه آژانس مقصد را انتخاب کنید.");
      }
      if (uploadFile) {
        setUploadQueue((prev) =>
          prev.map((q) => ({ ...q, status: "UPLOADING", progress: 65 }))
        );
        const fd = new FormData();
        fd.append("file", uploadFile);
        fd.append("title", form.title || uploadQueue[0]?.title || uploadFile.name);
        fd.append("category", form.category);
        fd.append("access_level", form.access_level);
        if (form.property_id) fd.append("property_id", form.property_id);
        if (form.customer_id) fd.append("customer_id", form.customer_id);
        if (form.contract_id) fd.append("contract_id", form.contract_id);
        return apiFetch("/api/v1/documents/upload", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: fd,
        });
      }
      return apiFetch("/api/v1/documents", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          title: form.title,
          category: form.category,
          access_level: form.access_level,
          property_id: form.property_id || null,
          customer_id: form.customer_id || null,
          contract_id: form.contract_id || null,
          file_key: form.file_key || undefined,
        }),
      });
    },
    onSuccess: () => {
      setModalOpen(false);
      setUploadQueue([]);
      setForm({
        title: "",
        category: "TITLE_DEED",
        access_level: "AGENCY_INTERNAL",
        property_id: "",
        customer_id: "",
        contract_id: "",
        file_key: "",
      });
      setErrMsg(null);
      setNotice("سند جدید با موفقیت در خزانه ثبت و نسخه‌بندی شد.");
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e: Error) => {
      setUploadQueue((prev) =>
        prev.map((q) => ({ ...q, status: "ERROR", error: e.message }))
      );
      setErrMsg(e.message);
    },
  });

  const editMut = useMutation({
    mutationFn: async () => {
      if (!editTarget) return;
      return apiFetch(`/api/v1/documents/${editTarget.id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId || editTarget.agency_id || null,
        body: JSON.stringify({
          title: editForm.title.trim(),
          category: editForm.category,
          access_level: editForm.access_level,
          property_id: editForm.property_id || null,
          customer_id: editForm.customer_id || null,
          contract_id: editForm.contract_id || null,
        }),
      });
    },
    onSuccess: () => {
      setEditTarget(null);
      setErrMsg(null);
      setNotice("مشخصات سند با موفقیت ویرایش شد.");
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: async (doc: DocumentItem) =>
      apiFetch(`/api/v1/documents/${doc.id}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId || doc.agency_id || null,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("سند با موفقیت حذف (بایگانی) شد.");
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const downloadMut = useMutation({
    mutationFn: async (doc: DocumentItem) => {
      const targetAg = activeAgencyId || doc.agency_id || null;
      try {
        await apiDownloadBlob(`/api/v1/documents/${doc.id}/content`, {
          token: accessToken,
          agencyId: targetAg,
          filenameFallback: `${doc.title || "document"}.pdf`,
        });
        return { downloaded: true };
      } catch {
        const env = await apiFetch<{ file_key: string }>(`/api/v1/documents/${doc.id}/download`, {
          method: "POST",
          token: accessToken,
          agencyId: targetAg,
        });
        return { downloaded: false, file_key: env.data.file_key };
      }
    },
    onSuccess: (res) => {
      setErrMsg(null);
      setNotice(
        res.downloaded
          ? "فایل سند با موفقیت دانلود و رویداد دسترسی ممیزی ثبت شد."
          : `فایل فیزیکی موجود نبود؛ دسترسی و لاگ دانلود سند ثبت شد (${res.file_key || "v1"}).`
      );
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const openInlinePreview = async (doc: DocumentItem) => {
    try {
      setErrMsg(null);
      const headers: Record<string, string> = {};
      if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
      const targetAg = activeAgencyId || doc.agency_id;
      if (targetAg) headers["X-Agency-ID"] = targetAg;
      const res = await fetch(`/api/v1/documents/${doc.id}/content?inline=true`, { headers });
      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || `فایل فیزیکی برای پیش‌نمایش یافت نشد (${res.status})`);
      }
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="خزانه اسناد و مدارک"
        subtitle="پیش‌نمایش ایمن، اتصال به پرونده ملک/مشتری/قرارداد، مدیریت نسخه‌ها و کنترل سطح محرمانگی"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "اسناد و فایل‌ها" }]}
        actions={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
          >
            <Plus className="h-4 w-4" />
            آپلود / ثبت سند جدید
          </button>
        }
      />

      {effectiveRole === "SUPER_ADMIN" && !activeAgencyId && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          شما در نمای سراسری همه آژانس‌ها هستید. برای آپلود یا ثبت سند جدید، ابتدا آژانس مقصد را از منوی بالای صفحه انتخاب کنید.
        </div>
      )}

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {activeAgencyId && (
        <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900 sm:grid-cols-3">
          <select
            value={propertyFilter}
            onChange={(e) => setPropertyFilter(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="">فیلتر بر اساس ملک (همه)</option>
            {(propsQ.data || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.property_code} — {p.title}
              </option>
            ))}
          </select>
          <select
            value={customerFilter}
            onChange={(e) => setCustomerFilter(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="">فیلتر بر اساس مشتری (همه)</option>
            {(custsQ.data || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name} ({c.primary_phone})
              </option>
            ))}
          </select>
          <select
            value={contractFilter}
            onChange={(e) => setContractFilter(e.target.value)}
            className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="">فیلتر بر اساس قرارداد (همه)</option>
            {(contractsQ.data || []).map((ct) => (
              <option key={ct.id} value={ct.id}>
                {ct.contract_number} — {ct.property_title}
              </option>
            ))}
          </select>
        </div>
      )}

      <DataTable
        rows={docsQ.data || []}
        rowKey={(d) => d.id}
        isLoading={docsQ.isLoading}
        error={docsQ.error instanceof Error ? docsQ.error.message : null}
        onRetry={() => docsQ.refetch()}
        searchPlaceholder="جستجو در عنوان سند..."
        activeFilter={catFilter}
        onFilterChange={setCatFilter}
        filterTabs={[
          { value: "", label: "همه دسته‌ها" },
          { value: "TITLE_DEED", label: "سند مالکیت" },
          { value: "CONTRACT", label: "قرارداد" },
          { value: "IDENTITY", label: "هویتی" },
          { value: "INSPECTION", label: "گزارش بازدید" },
          { value: "GENERAL", label: "عمومی" },
        ]}
        columns={[
          {
            key: "title",
            header: "عنوان سند",
            render: (d) => (
              <div>
                <div className="flex items-center gap-2 font-semibold">
                  <FileText className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  <span>{d.title}</span>
                </div>
                {(d.property_title || d.customer_name || d.contract_number || (!activeAgencyId && d.agency_name)) && (
                  <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                    {[
                      !activeAgencyId && d.agency_name ? d.agency_name : null,
                      d.property_title ? `ملک: ${d.property_title}` : null,
                      d.customer_name ? `مشتری: ${d.customer_name}` : null,
                      d.contract_number ? `قرارداد: ${d.contract_number}` : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                )}
              </div>
            ),
          },
          {
            key: "cat",
            header: "دسته‌بندی",
            render: (d) => <span className="text-xs">{CATEGORY_LABELS[d.category] || d.category}</span>,
          },
          {
            key: "lvl",
            header: "سطح دسترسی",
            render: (d) => (
              <span className="text-xs">{ACCESS_LABELS[d.access_level] || d.access_level}</span>
            ),
          },
          {
            key: "ver",
            header: "آخرین نسخه",
            render: (d) => <span className="font-mono text-xs">v{d.versions[0]?.version_number || 1}</span>,
          },
          { key: "dt", header: "تاریخ ثبت", render: (d) => <DateDisplay value={d.created_at} /> },
          {
            key: "act",
            header: "عملیات",
            render: (d) => (
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => openInlinePreview(d)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Eye className="h-3.5 w-3.5" />
                  پیش‌نمایش
                </button>
                <button
                  type="button"
                  disabled={downloadMut.isPending}
                  onClick={() => downloadMut.mutate(d)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Download className="h-3.5 w-3.5" />
                  دانلود
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditTarget(d);
                    setEditForm({
                      title: d.title,
                      category: d.category,
                      access_level: d.access_level,
                      property_id: d.property_id || "",
                      customer_id: d.customer_id || "",
                      contract_id: d.contract_id || "",
                    });
                  }}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                  ویرایش
                </button>
                <button
                  type="button"
                  disabled={deleteMut.isPending}
                  onClick={async () => {
                    if (await confirmDialog({ title: "تأیید حذف", message: `آیا از حذف (بایگانی) سند «${d.title}» مطمئن هستید؟`, danger: true })) {
                      deleteMut.mutate(d);
                    }
                  }}
                  className="inline-flex h-7 items-center justify-center rounded border border-rose-200 bg-rose-50 px-2 text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300"
                  title="حذف سند"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ),
          },
        ]}
      />

      <ModalDrawer
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="آپلود و پیش‌نمایش سند جدید در خزانه"
        widthClass="max-w-2xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-4"
        >
          {!activeAgencyId && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
              ابتدا آژانس فعال را از منوی بالای صفحه انتخاب کنید تا سند در خزانه همان آژانس ذخیره شود.
            </div>
          )}
          <input
            required={!uploadFile}
            placeholder="عنوان سند (مثال: تصویر سند تک‌برگ پنت‌هاوس زعفرانیه)"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="TITLE_DEED">سند مالکیت</option>
              <option value="CONTRACT">قرارداد</option>
              <option value="IDENTITY">مدرک هویتی</option>
              <option value="INSPECTION">گزارش بازدید</option>
              <option value="GENERAL">عمومی</option>
            </select>
            <select
              value={form.access_level}
              onChange={(e) => setForm({ ...form, access_level: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="AGENCY_INTERNAL">داخلی آژانس</option>
              <option value="CONFIDENTIAL">محرمانه (فقط مدیر و حسابدار)</option>
              <option value="PUBLIC">عمومی</option>
            </select>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <select
              value={form.property_id}
              onChange={(e) => setForm({ ...form, property_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 text-xs"
            >
              <option value="">اتصال به ملک (اختیاری)</option>
              {(propsQ.data || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.property_code} — {p.title}
                </option>
              ))}
            </select>
            <select
              value={form.customer_id}
              onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 text-xs"
            >
              <option value="">اتصال به مشتری (اختیاری)</option>
              {(custsQ.data || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name}
                </option>
              ))}
            </select>
            <select
              value={form.contract_id}
              onChange={(e) => setForm({ ...form, contract_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 text-xs"
            >
              <option value="">اتصال به قرارداد (اختیاری)</option>
              {(contractsQ.data || []).map((ct) => (
                <option key={ct.id} value={ct.id}>
                  {ct.contract_number}
                </option>
              ))}
            </select>
          </div>

          <SecureFileUploader
            accept=".pdf,.jpg,.jpeg,.png,.webp,.docx"
            allowedExtensions={["pdf", "jpg", "jpeg", "png", "webp", "docx"]}
            multiple={false}
            queue={uploadQueue}
            onQueueChange={setUploadQueue}
            hint="PDF، تصویر (JPG/PNG/WebP) یا DOCX تا سقف ۱۰ مگابایت"
          />

          {!uploadFile && (
            <input
              placeholder="یا کلید فایل مخزن (اختیاری)"
              dir="ltr"
              value={form.file_key}
              onChange={(e) => setForm({ ...form, file_key: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
            />
          )}

          <button
            type="submit"
            disabled={createMut.isPending || !activeAgencyId}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            {createMut.isPending ? "در حال آپلود و ثبت..." : uploadFile ? "تأیید، آپلود و ثبت سند" : "ثبت سند"}
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        title={`ویرایش مشخصات سند ${editTarget?.title || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            editMut.mutate();
          }}
          className="space-y-3"
        >
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">عنوان سند *</label>
            <input
              required
              value={editForm.title}
              onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">دسته‌بندی</label>
              <select
                value={editForm.category}
                onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
              >
                <option value="TITLE_DEED">سند مالکیت</option>
                <option value="DEED">سند ملکی (DEED)</option>
                <option value="CONTRACT">قرارداد</option>
                <option value="IDENTITY">مدرک هویتی</option>
                <option value="INSPECTION">گزارش بازدید</option>
                <option value="GENERAL">عمومی</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">سطح دسترسی</label>
              <select
                value={editForm.access_level}
                onChange={(e) => setEditForm({ ...editForm, access_level: e.target.value })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
              >
                <option value="AGENCY_INTERNAL">داخلی آژانس</option>
                <option value="CONFIDENTIAL">محرمانه</option>
                <option value="PUBLIC">عمومی</option>
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">ملک مرتبط</label>
            <select
              value={editForm.property_id}
              onChange={(e) => setEditForm({ ...editForm, property_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="">بدون ارتباط با ملک</option>
              {(propsQ.data || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.property_code} — {p.title}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">مشتری مرتبط</label>
            <select
              value={editForm.customer_id}
              onChange={(e) => setEditForm({ ...editForm, customer_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="">بدون ارتباط با مشتری</option>
              {(custsQ.data || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">قرارداد مرتبط</label>
            <select
              value={editForm.contract_id}
              onChange={(e) => setEditForm({ ...editForm, contract_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="">بدون ارتباط با قرارداد</option>
              {(contractsQ.data || []).map((ct) => (
                <option key={ct.id} value={ct.id}>
                  {ct.contract_number}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={editMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            {editMut.isPending ? "در حال ذخیره..." : "ذخیره تغییرات سند"}
          </button>
        </form>
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
