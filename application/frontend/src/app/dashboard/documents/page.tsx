"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Plus } from "lucide-react";
import { apiDownloadBlob, apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { DocumentItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { SecureFileUploader, type QueuedUploadFile } from "@/components/ui/SecureFileUploader";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function DocumentsVaultPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [catFilter, setCatFilter] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [uploadQueue, setUploadQueue] = useState<QueuedUploadFile[]>([]);

  const [form, setForm] = useState({
    title: "",
    category: "TITLE_DEED",
    access_level: "AGENCY_INTERNAL",
    file_key: "",
  });

  const docsQ = useQuery({
    queryKey: ["documents", activeAgencyId, catFilter],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () => {
      const q = catFilter ? `?category=${catFilter}` : "";
      return (
        await apiFetch<DocumentItem[]>(`/api/v1/documents${q}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const uploadFile = uploadQueue[0]?.file || null;

  const createMut = useMutation({
    mutationFn: async () => {
      if (uploadFile) {
        setUploadQueue((prev) =>
          prev.map((q) => ({ ...q, status: "UPLOADING", progress: 65 }))
        );
        const fd = new FormData();
        fd.append("file", uploadFile);
        fd.append("title", form.title || uploadQueue[0]?.title || uploadFile.name);
        fd.append("category", form.category);
        fd.append("access_level", form.access_level);
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
          file_key: form.file_key || undefined,
        }),
      });
    },
    onSuccess: () => {
      setModalOpen(false);
      setUploadQueue([]);
      setForm({ title: "", category: "TITLE_DEED", access_level: "AGENCY_INTERNAL", file_key: "" });
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

  const downloadMut = useMutation({
    mutationFn: async (doc: DocumentItem) => {
      try {
        await apiDownloadBlob(`/api/v1/documents/${doc.id}/content`, {
          token: accessToken,
          agencyId: activeAgencyId,
          filenameFallback: `${doc.title || "document"}.pdf`,
        });
        return { downloaded: true };
      } catch {
        const env = await apiFetch<{ file_key: string }>(`/api/v1/documents/${doc.id}/download`, {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="خزانه اسناد و مدارک"
        subtitle="پیش‌نمایش ایمن PDF و تصاویر پیش از آپلود، مدیریت اسناد ملکی و کنترل سطح محرمانگی"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "اسناد و فایل‌ها" }]}
        actions={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            آپلود / ثبت سند جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={docsQ.data || []}
        rowKey={(d) => d.id}
        isLoading={docsQ.isLoading}
        error={docsQ.error instanceof Error ? docsQ.error.message : null}
        searchPlaceholder="جستجو در عنوان سند..."
        activeFilter={catFilter}
        onFilterChange={setCatFilter}
        filterTabs={[
          { value: "", label: "همه دسته‌ها" },
          { value: "TITLE_DEED", label: "سند مالکیت" },
          { value: "CONTRACT", label: "قرارداد" },
          { value: "IDENTITY", label: "هویتی" },
          { value: "GENERAL", label: "عمومی" },
        ]}
        columns={[
          {
            key: "title",
            header: "عنوان سند",
            render: (d) => (
              <div className="flex items-center gap-2 font-semibold">
                <FileText className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                {d.title}
              </div>
            ),
          },
          { key: "cat", header: "دسته‌بندی", render: (d) => d.category },
          {
            key: "lvl",
            header: "سطح دسترسی",
            render: (d) =>
              d.access_level === "CONFIDENTIAL" ? "محرمانه (مدیر/مالی)" : "داخلی آژانس",
          },
          { key: "ver", header: "آخرین نسخه", render: (d) => `v${d.versions[0]?.version_number || 1}` },
          { key: "dt", header: "تاریخ ثبت", render: (d) => <DateDisplay value={d.created_at} /> },
          {
            key: "dl",
            header: "دانلود",
            render: (d) => (
              <button
                type="button"
                disabled={downloadMut.isPending}
                onClick={() => downloadMut.mutate(d)}
                className="inline-flex items-center gap-1 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <Download className="h-3.5 w-3.5" />
                دریافت فایل
              </button>
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
              <option value="GENERAL">عمومی</option>
            </select>
            <select
              value={form.access_level}
              onChange={(e) => setForm({ ...form, access_level: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="AGENCY_INTERNAL">داخلی آژانس</option>
              <option value="CONFIDENTIAL">محرمانه (فقط مدیر و حسابدار)</option>
            </select>
          </div>

          <SecureFileUploader
            accept=".pdf,.jpg,.jpeg,.png,.webp,.docx"
            allowedExtensions={["pdf", "jpg", "jpeg", "png", "webp", "docx"]}
            multiple={false}
            queue={uploadQueue}
            onQueueChange={setUploadQueue}
            hint="PDF، تصویر (JPG/PNG/WebP) یا DOCX تا سقف ۱۰ مگابایت — برای مشاهده پیش‌نمایش قبل از آپلود روی تصویر بندانگشتی کلیک کنید"
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
            disabled={createMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            {createMut.isPending ? "در حال آپلود و ثبت..." : uploadFile ? "تأیید، آپلود و ثبت سند" : "ثبت سند"}
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}
