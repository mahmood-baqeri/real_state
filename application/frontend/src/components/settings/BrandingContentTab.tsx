"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileEdit, Image as ImageIcon, Plus, Save, Trash2, Upload } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { BrandMediaSlotItem, SiteContentBlockItem } from "@/lib/types";
import { LoadingState } from "@/components/ui/StateNotice";

interface Props {
  onNotice: (msg: string) => void;
  onError: (msg: string) => void;
}

export function BrandingContentTab({ onNotice, onError }: Props) {
  const { accessToken } = useAuth();
  const qc = useQueryClient();

  const [selectedSlug, setSelectedSlug] = useState<string>("home_hero");
  const [blockForm, setBlockForm] = useState({
    slug_key: "home_hero",
    page_key: "HOME",
    section_key: "HERO",
    title_fa: "",
    subtitle_fa: "",
    body_html: "",
    cta_label: "",
    cta_href: "",
    status: "PUBLISHED",
    is_active: true,
  });

  const [slotEdits, setSlotEdits] = useState<Record<string, { alt_text?: string; image_url?: string; dark_image_url?: string }>>({});
  const [newSlot, setNewSlot] = useState({ slot_key: "", title_fa: "", category: "LOGO" });
  const [uploadingSlotKey, setUploadingSlotKey] = useState<string | null>(null);

  const brandingQ = useQuery({
    queryKey: ["admin-branding-slots"],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<BrandMediaSlotItem[]>("/api/v1/settings/branding?include_inactive=true")).data,
  });

  const blocksQ = useQuery({
    queryKey: ["admin-content-blocks"],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<SiteContentBlockItem[]>("/api/v1/settings/content-blocks?published_only=false")).data,
  });

  const selectBlock = (blk: SiteContentBlockItem) => {
    setSelectedSlug(blk.slug_key);
    setBlockForm({
      slug_key: blk.slug_key,
      page_key: blk.page_key || "HOME",
      section_key: blk.section_key || "GENERAL",
      title_fa: blk.title_fa || "",
      subtitle_fa: blk.subtitle_fa || "",
      body_html: blk.body_html || "",
      cta_label: blk.cta_label || "",
      cta_href: blk.cta_href || "",
      status: blk.status || "PUBLISHED",
      is_active: blk.is_active !== false,
    });
  };

  const uploadSlotMut = useMutation({
    mutationFn: async ({
      slotKey,
      file,
      darkVariant,
    }: {
      slotKey: string;
      file: File;
      darkVariant: boolean;
    }) => {
      setUploadingSlotKey(`${slotKey}:${darkVariant ? "dark" : "light"}`);
      const form = new FormData();
      form.append("file", file);
      form.append("dark_variant", darkVariant ? "true" : "false");
      return apiFetch(`/api/v1/settings/branding/${encodeURIComponent(slotKey)}/upload`, {
        method: "POST",
        token: accessToken,
        body: form,
      });
    },
    onSuccess: () => {
      setUploadingSlotKey(null);
      onNotice("تصویر برند با موفقیت آپلود و در جایگاه مربوطه ذخیره شد.");
      qc.invalidateQueries({ queryKey: ["admin-branding-slots"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => {
      setUploadingSlotKey(null);
      onError(e.message);
    },
  });

  const clearSlotImageMut = useMutation({
    mutationFn: async ({ slotKey, darkVariant }: { slotKey: string; darkVariant: boolean }) =>
      apiFetch(`/api/v1/settings/branding/${encodeURIComponent(slotKey)}/image?dark_variant=${darkVariant}`, {
        method: "DELETE",
        token: accessToken,
      }),
    onSuccess: () => {
      onNotice("تصویر جایگاه بصری با موفقیت حذف شد.");
      qc.invalidateQueries({ queryKey: ["admin-branding-slots"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const createSlotMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/settings/branding/${encodeURIComponent(newSlot.slot_key.trim().toLowerCase())}`, {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify({
          title_fa: newSlot.title_fa.trim(),
          category: newSlot.category,
          is_active: true,
        }),
      }),
    onSuccess: () => {
      setNewSlot({ slot_key: "", title_fa: "", category: "LOGO" });
      onNotice("جایگاه رسانه جدید اضافه شد.");
      qc.invalidateQueries({ queryKey: ["admin-branding-slots"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const updateSlotMut = useMutation({
    mutationFn: async (slotKey: string) => {
      const patch = slotEdits[slotKey] || {};
      return apiFetch(`/api/v1/settings/branding/${encodeURIComponent(slotKey)}`, {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify(patch),
      });
    },
    onSuccess: () => {
      onNotice("مشخصات جایگاه بصری به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["admin-branding-slots"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const saveBlockMut = useMutation({
    mutationFn: async () =>
      apiFetch<SiteContentBlockItem>(
        `/api/v1/settings/content-blocks/${encodeURIComponent(blockForm.slug_key.trim())}`,
        {
          method: "PUT",
          token: accessToken,
          body: JSON.stringify({
            page_key: blockForm.page_key,
            section_key: blockForm.section_key,
            title_fa: blockForm.title_fa,
            subtitle_fa: blockForm.subtitle_fa,
            body_html: blockForm.body_html,
            cta_label: blockForm.cta_label,
            cta_href: blockForm.cta_href,
            status: blockForm.status,
            is_active: blockForm.is_active,
          }),
        }
      ),
    onSuccess: () => {
      onNotice("بلوک محتوای صفحه اصلی و پورتال در دیتابیس ذخیره شد.");
      qc.invalidateQueries({ queryKey: ["admin-content-blocks"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  return (
    <div className="space-y-6">
      {/* Section 1: Brand Media Slots */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <ImageIcon className="h-5 w-5 text-teal-700 dark:text-teal-400" />
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              جایگاه‌های لوگو، بنر و تصاویر برندینگ پلتفرم
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              آپلود فایل برای حالت روشن و تاریک و تنظیم متن جایگزین (Alt)
            </p>
          </div>
        </div>

        {brandingQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {(brandingQ.data || []).map((slot) => {
              const edit = slotEdits[slot.slot_key] || {};
              return (
                <div
                  key={slot.slot_key}
                  className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-3 dark:border-slate-800 dark:bg-slate-800/40"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                        {slot.title_fa}
                      </div>
                      <div className="font-mono text-[11px] text-slate-500">{slot.slot_key}</div>
                    </div>
                    <span className="rounded border border-slate-200 bg-white px-2 py-0.5 font-mono text-[10px] dark:border-slate-700 dark:bg-slate-900">
                      {slot.category}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                        نسخه روشن (Light)
                      </div>
                      <div className="flex h-20 items-center justify-center overflow-hidden rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-700">
                        {slot.image_url ? (
                          <img
                            src={slot.image_url}
                            alt={slot.alt_text || slot.title_fa}
                            className="max-h-full max-w-full object-contain"
                          />
                        ) : (
                          <span className="text-[10px] text-slate-400">بدون تصویر</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <label className="inline-flex h-8 flex-1 cursor-pointer items-center justify-center gap-1 rounded-lg border border-slate-300 bg-white px-2 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                          <Upload className="h-3 w-3" />
                          {uploadingSlotKey === `${slot.slot_key}:light` ? "در حال آپلود..." : "آپلود نسخه روشن"}
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp,image/x-icon,.ico"
                            className="hidden"
                            onChange={(e) => {
                              const f = e.target.files?.[0];
                              e.target.value = "";
                              if (f) uploadSlotMut.mutate({ slotKey: slot.slot_key, file: f, darkVariant: false });
                            }}
                          />
                        </label>
                        {slot.image_url && (
                          <button
                            type="button"
                            disabled={clearSlotImageMut.isPending}
                            onClick={() => clearSlotImageMut.mutate({ slotKey: slot.slot_key, darkVariant: false })}
                            className="inline-flex h-8 shrink-0 items-center justify-center rounded-lg border border-rose-200 bg-rose-50 px-2 text-rose-700 hover:bg-rose-100"
                            title="حذف تصویر روشن"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                        نسخه تاریک (Dark)
                      </div>
                      <div className="flex h-20 items-center justify-center overflow-hidden rounded-lg border border-slate-700 bg-slate-900 p-2">
                        {slot.dark_image_url ? (
                          <img
                            src={slot.dark_image_url}
                            alt={slot.alt_text || slot.title_fa}
                            className="max-h-full max-w-full object-contain"
                          />
                        ) : (
                          <span className="text-[10px] text-slate-400">بدون تصویر</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <label className="inline-flex h-8 flex-1 cursor-pointer items-center justify-center gap-1 rounded-lg border border-slate-300 bg-white px-2 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                          <Upload className="h-3 w-3" />
                          {uploadingSlotKey === `${slot.slot_key}:dark` ? "در حال آپلود..." : "آپلود نسخه تاریک"}
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp,image/x-icon,.ico"
                            className="hidden"
                            onChange={(e) => {
                              const f = e.target.files?.[0];
                              e.target.value = "";
                              if (f) uploadSlotMut.mutate({ slotKey: slot.slot_key, file: f, darkVariant: true });
                            }}
                          />
                        </label>
                        {slot.dark_image_url && (
                          <button
                            type="button"
                            disabled={clearSlotImageMut.isPending}
                            onClick={() => clearSlotImageMut.mutate({ slotKey: slot.slot_key, darkVariant: true })}
                            className="inline-flex h-8 shrink-0 items-center justify-center rounded-lg border border-rose-200 bg-rose-50 px-2 text-rose-700 hover:bg-rose-100"
                            title="حذف تصویر تاریک"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      value={edit.alt_text ?? slot.alt_text ?? ""}
                      onChange={(e) =>
                        setSlotEdits((p) => ({
                          ...p,
                          [slot.slot_key]: { ...p[slot.slot_key], alt_text: e.target.value },
                        }))
                      }
                      placeholder="متن جایگزین (Alt Text)"
                      className="h-8 flex-1 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                    />
                    <button
                      type="button"
                      onClick={() => updateSlotMut.mutate(slot.slot_key)}
                      className="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
                    >
                      <Save className="h-3 w-3" />
                      ذخیره
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            createSlotMut.mutate();
          }}
          className="flex flex-wrap items-center gap-2 rounded-xl border border-dashed border-slate-300 p-3 dark:border-slate-700"
        >
          <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">افزودن جایگاه رسانه جدید:</span>
          <input
            required
            dir="ltr"
            placeholder="slot_key (مثلاً promo_banner)"
            value={newSlot.slot_key}
            onChange={(e) => setNewSlot({ ...newSlot, slot_key: e.target.value })}
            className="h-8 w-44 rounded-lg border border-slate-300 bg-white px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            required
            placeholder="عنوان فارسی جایگاه"
            value={newSlot.title_fa}
            onChange={(e) => setNewSlot({ ...newSlot, title_fa: e.target.value })}
            className="h-8 flex-1 min-w-[160px] rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <select
            value={newSlot.category}
            onChange={(e) => setNewSlot({ ...newSlot, category: e.target.value })}
            className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
          >
            <option value="LOGO">لوگو (LOGO)</option>
            <option value="FAVICON">آیکون (FAVICON)</option>
            <option value="BANNER">بنر (BANNER)</option>
          </select>
          <button
            type="submit"
            disabled={createSlotMut.isPending}
            className="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg bg-slate-800 px-3 text-xs font-semibold text-white hover:bg-slate-900 dark:bg-slate-700"
          >
            <Plus className="h-3.5 w-3.5" />
            ایجاد جایگاه
          </button>
        </form>
      </div>

      {/* Section 2: Editable Portal Site Content Blocks */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <FileEdit className="h-5 w-5 text-teal-700 dark:text-teal-400" />
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              بلوک‌های متنی و معرفی صفحات پورتال
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              متون صفحه اصلی، بنر معرفی، فرم ثبت‌نام و صفحه درباره ما مستقیماً از دیتابیس خوانده می‌شوند.
            </p>
          </div>
        </div>

        {blocksQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <div className="lg:col-span-4 space-y-1.5">
              {(blocksQ.data || []).map((blk) => (
                <button
                  key={blk.slug_key}
                  type="button"
                  onClick={() => selectBlock(blk)}
                  className={`flex w-full items-center justify-between rounded-lg border px-3 py-2.5 text-right text-xs transition-colors ${
                    selectedSlug === blk.slug_key
                      ? "border-teal-700 bg-teal-50/70 font-bold text-teal-900 dark:border-teal-500 dark:bg-teal-950/40 dark:text-teal-200"
                      : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
                  }`}
                >
                  <div>
                    <div>{blk.title_fa || blk.slug_key}</div>
                    <div className="font-mono text-[10px] text-slate-400">
                      {blk.slug_key} ({blk.page_key})
                    </div>
                  </div>
                  <span className="font-mono text-[10px] text-teal-700 dark:text-teal-400">
                    {blk.status || "PUBLISHED"}
                  </span>
                </button>
              ))}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                saveBlockMut.mutate();
              }}
              className="lg:col-span-8 space-y-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-800/40"
            >
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-[11px] font-semibold">کلید بلوک (Slug)</label>
                  <input
                    required
                    dir="ltr"
                    value={blockForm.slug_key}
                    onChange={(e) => setBlockForm({ ...blockForm, slug_key: e.target.value })}
                    className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[11px] font-semibold">صفحه (Page Key)</label>
                  <input
                    value={blockForm.page_key}
                    onChange={(e) => setBlockForm({ ...blockForm, page_key: e.target.value })}
                    className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[11px] font-semibold">وضعیت انتشار</label>
                  <select
                    value={blockForm.status}
                    onChange={(e) => setBlockForm({ ...blockForm, status: e.target.value })}
                    className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="PUBLISHED">منتشرشده (PUBLISHED)</option>
                    <option value="DRAFT">پیش‌نویس (DRAFT)</option>
                    <option value="ARCHIVED">بایگانی (ARCHIVED)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-semibold">عنوان اصلی (Title)</label>
                <input
                  value={blockForm.title_fa}
                  onChange={(e) => setBlockForm({ ...blockForm, title_fa: e.target.value })}
                  className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-semibold">زیرعنوان / توضیح کوتاه</label>
                <textarea
                  rows={2}
                  value={blockForm.subtitle_fa}
                  onChange={(e) => setBlockForm({ ...blockForm, subtitle_fa: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-semibold">محتوای HTML پاکسازی‌شده</label>
                <textarea
                  rows={4}
                  value={blockForm.body_html}
                  onChange={(e) => setBlockForm({ ...blockForm, body_html: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 bg-white p-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-[11px] font-semibold">متن دکمه فراخوان (CTA)</label>
                  <input
                    value={blockForm.cta_label}
                    onChange={(e) => setBlockForm({ ...blockForm, cta_label: e.target.value })}
                    className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[11px] font-semibold">مسیر دکمه (Href)</label>
                  <input
                    dir="ltr"
                    value={blockForm.cta_href}
                    onChange={(e) => setBlockForm({ ...blockForm, cta_href: e.target.value })}
                    className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={saveBlockMut.isPending}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                >
                  <Save className="h-3.5 w-3.5" />
                  ذخیره بلوک محتوا
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
