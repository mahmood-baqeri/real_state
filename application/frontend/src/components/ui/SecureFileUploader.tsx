"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Eye,
  File as FileIcon,
  FileText,
  Image as ImageIcon,
  RefreshCw,
  Star,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";

export interface QueuedUploadFile {
  id: string;
  file: File;
  previewUrl: string | null;
  kind: "IMAGE" | "PDF" | "OTHER";
  title: string;
  isCover: boolean;
  progress: number;
  status: "READY" | "UPLOADING" | "DONE" | "ERROR";
  error?: string;
}

const DEFAULT_MAX_BYTES = 10 * 1024 * 1024; // 10MB

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function classifyFile(file: File): "IMAGE" | "PDF" | "OTHER" {
  const mime = (file.type || "").toLowerCase();
  const name = file.name.toLowerCase();
  if (mime.startsWith("image/") || /\.(jpg|jpeg|png|webp)$/.test(name)) return "IMAGE";
  if (mime === "application/pdf" || name.endsWith(".pdf")) return "PDF";
  return "OTHER";
}

/** فایل‌ها را از انتخاب، کشیدن و در صورت فعال بودن، کلیپ‌بورد به صف می‌افزاید. */
export function SecureFileUploader({
  accept = "image/jpeg,image/png,image/webp",
  allowedExtensions = ["jpg", "jpeg", "png", "webp"],
  maxSizeBytes = DEFAULT_MAX_BYTES,
  multiple = true,
  allowCoverSelect = false,
  allowImagePaste = false,
  queue,
  onQueueChange,
  onUploadSingle,
  onUploadAll,
  hint = "تصاویر JPG، PNG یا WebP تا سقف ۱۰ مگابایت",
}: {
  accept?: string;
  allowedExtensions?: string[];
  maxSizeBytes?: number;
  multiple?: boolean;
  allowCoverSelect?: boolean;
  allowImagePaste?: boolean;
  queue: QueuedUploadFile[];
  onQueueChange: React.Dispatch<React.SetStateAction<QueuedUploadFile[]>>;
  onUploadSingle?: (item: QueuedUploadFile) => Promise<void>;
  onUploadAll?: () => Promise<void>;
  hint?: string;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [validationErr, setValidationErr] = useState<string | null>(null);
  const [previewTarget, setPreviewTarget] = useState<QueuedUploadFile | null>(null);
  const [uploadingAll, setUploadingAll] = useState(false);

  // Revoke object URLs on unmount to avoid memory leaks
  const urlsRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    const urls = urlsRef.current;
    return () => {
      urls.forEach((u) => URL.revokeObjectURL(u));
      urls.clear();
    };
  }, []);

  const addFiles = (fileList: ArrayLike<File> | null) => {
    if (!fileList || fileList.length === 0) return;
    setValidationErr(null);

    const incoming = Array.from(fileList);
    const created: QueuedUploadFile[] = [];
    const errors: string[] = [];

    for (const f of incoming) {
      const ext = f.name.split(".").pop()?.toLowerCase() || "";
      if (!allowedExtensions.includes(ext)) {
        errors.push(`فرمت فایل «${f.name}» مجاز نیست (مجاز: ${allowedExtensions.join(", ")}).`);
        continue;
      }
      if (f.size > maxSizeBytes) {
        errors.push(
          `حجم فایل «${f.name}» (${formatBytes(f.size)}) از سقف ${formatBytes(maxSizeBytes)} بیشتر است.`
        );
        continue;
      }
      const kind = classifyFile(f);
      let previewUrl: string | null = null;
      if (kind === "IMAGE" || kind === "PDF") {
        previewUrl = URL.createObjectURL(f);
        urlsRef.current.add(previewUrl);
      }
      created.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        file: f,
        previewUrl,
        kind,
        title: f.name.replace(/\.[^/.]+$/, ""),
        isCover: false,
        progress: 0,
        status: "READY",
      });
    }

    if (errors.length > 0) {
      setValidationErr(errors.join(" "));
    }
    if (created.length > 0) {
      onQueueChange((prev) => {
        const next = multiple ? [...prev, ...created] : [created[0]];
        if (allowCoverSelect && !next.some((i) => i.isCover)) {
          next[0].isCover = true;
        }
        return next;
      });
    }
  };

  const removeItem = (id: string) => {
    onQueueChange((prev) => {
      const target = prev.find((i) => i.id === id);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
        urlsRef.current.delete(target.previewUrl);
      }
      return prev.filter((i) => i.id !== id);
    });
  };

  const moveItem = (idx: number, dir: -1 | 1) => {
    onQueueChange((prev) => {
      const targetIdx = idx + dir;
      if (targetIdx < 0 || targetIdx >= prev.length) return prev;
      const copy = [...prev];
      const [item] = copy.splice(idx, 1);
      copy.splice(targetIdx, 0, item);
      return copy;
    });
  };

  const setCover = (id: string) => {
    onQueueChange((prev) =>
      prev.map((item) => ({ ...item, isCover: item.id === id }))
    );
  };

  const readyCount = queue.filter((q) => q.status === "READY" || q.status === "ERROR").length;

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onPaste={allowImagePaste ? (event) => {
          const images = Array.from(event.clipboardData.files).filter((file) => file.type.startsWith("image/"));
          if (!images.length) return;
          event.preventDefault();
          const extensions = new Map([
            ["image/jpeg", "jpg"], ["image/png", "png"], ["image/webp", "webp"],
          ]);
          addFiles(images.map((file, index) => {
            const extension = extensions.get(file.type);
            return extension && !/\.[^./]+$/.test(file.name)
              ? new File([file], `clipboard-${index + 1}.${extension}`, { type: file.type })
              : file;
          }));
        } : undefined}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-5 text-center transition-colors ${
          dragging
            ? "border-teal-600 bg-teal-50/70 dark:border-teal-400 dark:bg-teal-950/30"
            : "border-slate-300 bg-slate-50/80 hover:border-teal-600 dark:border-slate-700 dark:bg-slate-900/50 dark:hover:border-teal-500"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
          className="hidden"
        />
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-400">
          <UploadCloud className="h-5 w-5" />
        </div>
        <div className="text-xs font-bold text-slate-800 dark:text-slate-200">
          فایل‌ها را اینجا بکشید و رها کنید یا کلیک کنید
        </div>
        <div className="text-[11px] text-slate-500 dark:text-slate-400">{hint}</div>
        {allowImagePaste && (
          <div className="text-[11px] text-slate-500 dark:text-slate-400">
            برای چسباندن تصویر، این بخش را انتخاب کنید و Ctrl+V یا ⌘+V بزنید.
          </div>
        )}
      </div>

      {validationErr && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-900/70 dark:bg-rose-950/40 dark:text-rose-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{validationErr}</span>
        </div>
      )}

      {queue.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-slate-700 dark:text-slate-300 tabular-nums">
              پیش‌نمایش فایل‌های آماده آپلود ({queue.length} فایل)
            </span>
            {onUploadAll && readyCount > 0 && (
              <button
                type="button"
                disabled={uploadingAll}
                onClick={async () => {
                  setUploadingAll(true);
                  try {
                    await onUploadAll();
                  } finally {
                    setUploadingAll(false);
                  }
                }}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                <UploadCloud className="h-3.5 w-3.5" />
                {uploadingAll ? "در حال آپلود..." : `آپلود ${readyCount} فایل`}
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {queue.map((item, idx) => (
              <div
                key={item.id}
                className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3 text-xs dark:border-slate-800 dark:bg-slate-900"
              >
                <button
                  type="button"
                  onClick={() => setPreviewTarget(item)}
                  className="group relative flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800"
                  title="پیش‌نمایش کامل قبل از آپلود"
                >
                  {item.kind === "IMAGE" && item.previewUrl ? (
                    <img
                      src={item.previewUrl}
                      alt={item.title}
                      className="h-full w-full object-cover transition-transform group-hover:scale-105"
                    />
                  ) : item.kind === "PDF" ? (
                    <div className="flex flex-col items-center gap-0.5 text-rose-700 dark:text-rose-400">
                      <FileText className="h-6 w-6" />
                      <span className="font-mono text-[9px] font-bold">PDF</span>
                    </div>
                  ) : (
                    <FileIcon className="h-6 w-6 text-slate-500" />
                  )}
                  {(item.kind === "IMAGE" || item.kind === "PDF") && (
                    <span className="absolute inset-0 flex items-center justify-center bg-slate-950/40 text-white opacity-0 transition-opacity group-hover:opacity-100">
                      <Eye className="h-4 w-4" />
                    </span>
                  )}
                </button>

                <div className="min-w-0 flex-1 space-y-1.5">
                  <input
                    type="text"
                    value={item.title}
                    disabled={item.status === "DONE"}
                    onChange={(e) => {
                      const nextTitle = e.target.value;
                      onQueueChange((prev) =>
                        prev.map((q) => (q.id === item.id ? { ...q, title: nextTitle } : q))
                      );
                    }}
                    className="h-7 w-full rounded border border-slate-200 bg-slate-50 px-2 text-xs font-medium text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                  />

                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 tabular-nums">
                    <span>{formatBytes(item.file.size)}</span>
                    {item.status === "DONE" && (
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 dark:text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" /> آپلود شد
                      </span>
                    )}
                    {item.status === "UPLOADING" && (
                      <span className="font-semibold text-teal-700 dark:text-teal-400">
                        در حال ارسال ({item.progress}%)
                      </span>
                    )}
                    {item.status === "ERROR" && (
                      <span className="font-semibold text-rose-600 dark:text-rose-400">
                        {item.error || "خطا در آپلود"}
                      </span>
                    )}
                  </div>

                  {item.status === "UPLOADING" && (
                    <div className="h-1.5 w-full overflow-hidden rounded bg-slate-200 dark:bg-slate-800">
                      <div
                        className="h-full bg-teal-600 transition-all"
                        style={{ width: `${Math.max(12, item.progress)}%` }}
                      />
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-1 pt-0.5">
                    {allowCoverSelect && (
                      <button
                        type="button"
                        onClick={() => setCover(item.id)}
                        className={`inline-flex h-6 items-center gap-1 rounded border px-1.5 text-[10px] font-semibold ${
                          item.isCover
                            ? "border-amber-500 bg-amber-50 text-amber-800 dark:border-amber-600 dark:bg-amber-950/50 dark:text-amber-300"
                            : "border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300"
                        }`}
                      >
                        <Star className="h-2.5 w-2.5" />
                        {item.isCover ? "کاور اصلی" : "انتخاب کاور"}
                      </button>
                    )}

                    {multiple && queue.length > 1 && (
                      <>
                        <button
                          type="button"
                          disabled={idx === 0}
                          onClick={() => moveItem(idx, -1)}
                          title="جابه‌جایی به بالا"
                          className="inline-flex h-6 w-6 items-center justify-center rounded border border-slate-200 text-slate-600 disabled:opacity-30 dark:border-slate-700 dark:text-slate-300"
                        >
                          <ArrowUp className="h-3 w-3" />
                        </button>
                        <button
                          type="button"
                          disabled={idx === queue.length - 1}
                          onClick={() => moveItem(idx, 1)}
                          title="جابه‌جایی به پایین"
                          className="inline-flex h-6 w-6 items-center justify-center rounded border border-slate-200 text-slate-600 disabled:opacity-30 dark:border-slate-700 dark:text-slate-300"
                        >
                          <ArrowDown className="h-3 w-3" />
                        </button>
                      </>
                    )}

                    {item.status === "ERROR" && onUploadSingle && (
                      <button
                        type="button"
                        onClick={() => onUploadSingle(item)}
                        className="inline-flex h-6 items-center gap-1 rounded border border-rose-300 bg-rose-50 px-2 text-[10px] font-semibold text-rose-700"
                      >
                        <RefreshCw className="h-2.5 w-2.5" />
                        تلاش مجدد
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => removeItem(item.id)}
                      title="حذف / لغو"
                      className="inline-flex h-6 w-6 items-center justify-center rounded border border-slate-200 text-rose-600 hover:bg-rose-50 dark:border-slate-700 dark:text-rose-400"
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

      {/* Safe Sandboxed Preview Modal */}
      {previewTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-xs"
          onClick={() => setPreviewTarget(null)}
        >
          <div
            className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-slate-700 bg-white dark:bg-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-slate-100">
                {previewTarget.kind === "IMAGE" ? (
                  <ImageIcon className="h-4 w-4 text-teal-600" />
                ) : (
                  <FileText className="h-4 w-4 text-rose-600" />
                )}
                <span>پیش‌نمایش امن فایل: {previewTarget.file.name}</span>
                <span className="font-mono text-[11px] font-normal text-slate-500">
                  ({formatBytes(previewTarget.file.size)})
                </span>
              </div>
              <button
                type="button"
                onClick={() => setPreviewTarget(null)}
                className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex flex-1 items-center justify-center overflow-auto bg-slate-100 p-4 dark:bg-slate-950">
              {previewTarget.kind === "IMAGE" && previewTarget.previewUrl ? (
                <img
                  src={previewTarget.previewUrl}
                  alt={previewTarget.title}
                  className="max-h-[75vh] w-auto rounded-lg object-contain shadow-lg"
                />
              ) : previewTarget.kind === "PDF" && previewTarget.previewUrl ? (
                <iframe
                  title={previewTarget.title}
                  src={previewTarget.previewUrl}
                  className="h-[72vh] w-full rounded-lg border border-slate-300 bg-white dark:border-slate-700"
                />
              ) : (
                <div className="p-8 text-center text-xs text-slate-500">
                  پیش‌نمایش مستقیم برای این نوع فایل پشتیبانی نمی‌شود؛ فایل آماده آپلود ایمن است.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
