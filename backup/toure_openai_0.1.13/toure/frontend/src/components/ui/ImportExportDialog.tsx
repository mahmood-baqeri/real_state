"use client";

import React, { useState } from "react";
import { Download, FileSpreadsheet, Upload, X } from "lucide-react";
import { apiDownloadBlob, apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa } from "@/lib/formatters";

interface ImportPreviewResponse {
  filename: string;
  headers: string[];
  total_rows: number;
  imported_count: number;
  duplicate_count: number;
  error_count: number;
  errors: { row: number; reason: string }[];
  committed: boolean;
}

export function ImportExportDialog({
  module,
  moduleLabel,
  onImported,
}: {
  module: "properties" | "customers" | "accounting";
  moduleLabel: string;
  onImported?: () => void;
}) {
  const { accessToken, activeAgencyId } = useAuth();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const canImport = module === "properties" || module === "customers";

  async function runExport(fmt: "xlsx" | "csv") {
    if (!accessToken) return;
    setExporting(true);
    setErrorMsg(null);
    try {
      await apiDownloadBlob(
        `/api/v1/reports/export?module=${encodeURIComponent(module)}&fmt=${fmt}`,
        {
          token: accessToken,
          agencyId: activeAgencyId,
          filenameFallback: `${module}_export.${fmt}`,
        }
      );
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "خطا در دریافت خروجی فایل");
    } finally {
      setExporting(false);
    }
  }

  async function runImport(commit: boolean) {
    if (!accessToken || !file) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("module", module);
      form.append("column_mapping_json", "{}");
      form.append("commit", commit ? "true" : "false");

      const env = await apiFetch<ImportPreviewResponse>("/api/v1/reports/import", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: form,
      });
      setPreview(env.data);
      if (commit && env.data.committed && onImported) {
        onImported();
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "خطا در پردازش فایل اکسل/CSV");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={exporting}
          onClick={() => runExport("xlsx")}
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <Download className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
          خروجی Excel
        </button>
        <button
          type="button"
          disabled={exporting}
          onClick={() => runExport("csv")}
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <FileSpreadsheet className="h-3.5 w-3.5 text-slate-500 dark:text-slate-400" />
          CSV
        </button>
        {canImport && (
          <button
            type="button"
            onClick={() => {
              setOpen(true);
              setPreview(null);
              setErrorMsg(null);
            }}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-teal-700/30 bg-teal-50 px-3 text-xs font-semibold text-teal-800 hover:bg-teal-100 dark:border-teal-500/40 dark:bg-teal-950/60 dark:text-teal-300 dark:hover:bg-teal-950"
          >
            <Upload className="h-3.5 w-3.5" />
            ورود دسته‌ای ({moduleLabel})
          </button>
        )}
      </div>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                ورود دسته‌ای {moduleLabel} از Excel / CSV
              </h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
                  انتخاب فایل (.xlsx یا .csv)
                </label>
                <input
                  type="file"
                  accept=".xlsx,.csv"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    setPreview(null);
                  }}
                  className="block w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
                />
              </div>

              {errorMsg && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300">
                  {errorMsg}
                </div>
              )}

              {preview && (
                <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/50">
                  <div className="grid grid-cols-3 gap-2 tabular-nums">
                    <div>
                      <span className="text-slate-500">کل ردیف‌ها: </span>
                      <strong className="text-slate-900 dark:text-slate-100">
                        {formatNumberFa(preview.total_rows)}
                      </strong>
                    </div>
                    <div>
                      <span className="text-slate-500">تکراری: </span>
                      <strong className="text-amber-700 dark:text-amber-400">
                        {formatNumberFa(preview.duplicate_count)}
                      </strong>
                    </div>
                    <div>
                      <span className="text-slate-500">خطا: </span>
                      <strong className="text-rose-700 dark:text-rose-400">
                        {formatNumberFa(preview.error_count)}
                      </strong>
                    </div>
                  </div>
                  {preview.committed && (
                    <div className="font-semibold text-emerald-700 dark:text-emerald-400">
                      تعداد {formatNumberFa(preview.imported_count)} ردیف با موفقیت ثبت شد.
                    </div>
                  )}
                  {preview.errors.length > 0 && (
                    <ul className="max-h-32 space-y-1 overflow-y-auto pt-1 text-[11px] text-rose-700 dark:text-rose-300">
                      {preview.errors.slice(0, 8).map((err, i) => (
                        <li key={i}>
                          ردیف {formatNumberFa(err.row)}: {err.reason}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  disabled={!file || busy}
                  onClick={() => runImport(false)}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
                >
                  پیش‌نمایش و اعتبارسنجی
                </button>
                <button
                  type="button"
                  disabled={!file || busy}
                  onClick={() => runImport(true)}
                  className="rounded-lg bg-teal-700 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                >
                  {busy ? "در حال پردازش..." : "ثبت نهایی در سامانه"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
