"use client";

import React, { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Box,
  Cpu,
  Download,
  Eye,
  FileCode2,
  ScanLine,
  Trash2,
  Upload,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa, translateStatus } from "@/lib/formatters";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { DollhouseViewer } from "@/components/virtual-tour/DollhouseViewer";
import type {
  GeneratedModelAssetItem,
  ScanAssetItem,
  TourFloorItem,
  TourSceneItem,
} from "@/lib/types";

interface ScanManagerProps {
  tourId: string;
  floors: TourFloorItem[];
  scenes: TourSceneItem[];
  scans: ScanAssetItem[];
  onUpdated: () => void;
}

const ACCEPTED_SCAN_EXTENSIONS =
  ".ply,.pcd,.xyz,.pts,.npy,.npz,.obj,.glb,.las,.png,.tif,.tiff";

function formatBytesFa(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "۰ بایت";
  if (bytes < 1024) return `${formatNumberFa(bytes)} بایت`;
  if (bytes < 1024 * 1024) return `${formatNumberFa(Math.round(bytes / 102.4) / 10)} کیلوبایت`;
  return `${formatNumberFa(Math.round((bytes / (1024 * 1024)) * 10) / 10)} مگابایت`;
}

export function ScanManager({
  tourId,
  floors,
  scenes,
  scans,
  onUpdated,
}: ScanManagerProps) {
  const { accessToken, activeAgencyId } = useAuth();
  const [selectedScanId, setSelectedScanId] = useState<string>(scans[0]?.id || "");
  const [uploadFloorId, setUploadFloorId] = useState<string>(floors[0]?.id || "");
  const [uploadSceneId, setUploadSceneId] = useState<string>("");
  const [sourceDevice, setSourceDevice] = useState<string>("lidar_ios");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [show3DPreview, setShow3DPreview] = useState<boolean>(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const activeScan = useMemo(
    () => scans.find((s) => s.id === selectedScanId) || scans[0] || null,
    [scans, selectedScanId]
  );

  const previewAsModel: GeneratedModelAssetItem | null = useMemo(() => {
    if (!activeScan?.preview_glb_url) return null;
    const footprint = activeScan.processing_result?.estimated_footprint_sqm || "0";
    return {
      id: `scan-preview-${activeScan.id}`,
      tour_id: activeScan.tour_id,
      version: 1,
      format: "glb",
      state: activeScan.status,
      geometry_source: activeScan.source_device,
      estimated_accuracy: `${formatNumberFa(activeScan.points_count)} نقطه واقعی`,
      total_area_sqm: footprint,
      file_url: activeScan.preview_glb_url,
      size_bytes: activeScan.size_bytes,
      metadata: {
        source: "point_cloud_scan",
        scan_id: activeScan.id,
      },
      is_current: true,
      created_at: activeScan.created_at,
    };
  }, [activeScan]);

  const uploadScanMut = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error("ابتدا فایل اسکن سه‌بعدی یا نقشه عمق را انتخاب کنید.");
      const fd = new FormData();
      fd.append("file", selectedFile);
      fd.append("source_device", sourceDevice);
      if (uploadFloorId) fd.append("floor_id", uploadFloorId);
      if (uploadSceneId) fd.append("scene_id", uploadSceneId);
      return apiFetch<ScanAssetItem>(`/api/v1/virtual-tours/${tourId}/scans`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: fd,
      });
    },
    onSuccess: (res) => {
      setErrMsg(null);
      setSelectedFile(null);
      setSelectedScanId(res.data.id);
      setNotice(
        "فایل اسکن با موفقیت ذخیره شد. اکنون روی دکمه «پردازش و استخراج هندسه سه‌بعدی» کلیک کنید."
      );
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const processScanMut = useMutation({
    mutationFn: async (scanId: string) =>
      apiFetch(`/api/v1/scans/${scanId}/process`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("پردازش اسکن سه‌بعدی، حذف نویز، نقشه تراکم و خروجی GLB تکمیل یا در صف ثبت شد.");
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteScanMut = useMutation({
    mutationFn: async (scanId: string) =>
      apiFetch(`/api/v1/scans/${scanId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("اسکن انتخاب‌شده حذف شد.");
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const dims = activeScan?.bounding_box?.dimensions_m;
  const proc = activeScan?.processing_result;

  return (
    <div className="space-y-4">
      {notice && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-3.5 py-2.5 text-xs font-medium text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
          {notice}
        </div>
      )}
      {errMsg && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-medium text-rose-900 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-200">
          {errMsg}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Upload & List Column */}
        <div className="space-y-4 lg:col-span-4">
          {/* Upload Scan Form */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
            <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
              <Upload className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              بارگذاری اسکن LiDAR / ابرنقاط / مش سه‌بعدی
            </h3>
            <p className="text-[11px] leading-relaxed text-slate-500">
              فرمت‌های پشتیبانی‌شده واقعی: PLY، PCD، XYZ، PTS، NPY/NPZ، OBJ، GLB، LAS و نقشه عمق PNG/TIFF (سنسور ۱۶ بیتی).
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                uploadScanMut.mutate();
              }}
              className="space-y-2.5 text-xs"
            >
              <div>
                <label className="mb-1 block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                  تجهیز یا منبع اسکن
                </label>
                <select
                  value={sourceDevice}
                  onChange={(e) => setSourceDevice(e.target.value)}
                  className="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                >
                  <option value="lidar_ios">اسکنر LiDAR آیفون / آیپد</option>
                  <option value="depth_android">سنسور عمق اندروید (ARCore Depth)</option>
                  <option value="laser_scanner">اسکنر لیزری معماری (LAS/PTS)</option>
                  <option value="photogrammetry">خروجی فتوگرامتری (OBJ/GLB/PLY)</option>
                  <option value="other">سایر تجهیزات</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="mb-1 block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                    طبقه مرتبط
                  </label>
                  <select
                    value={uploadFloorId}
                    onChange={(e) => setUploadFloorId(e.target.value)}
                    className="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="">کل ملک / نامشخص</option>
                    {floors.map((fl) => (
                      <option key={fl.id} value={fl.id}>
                        {fl.title}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                    اتاق مرتبط
                  </label>
                  <select
                    value={uploadSceneId}
                    onChange={(e) => setUploadSceneId(e.target.value)}
                    className="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="">انتخابی</option>
                    {scenes.map((sc) => (
                      <option key={sc.id} value={sc.id}>
                        {sc.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                  فایل اسکن سه‌بعدی
                </label>
                <input
                  type="file"
                  accept={ACCEPTED_SCAN_EXTENSIONS}
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="block w-full rounded-lg border border-slate-300 bg-slate-50 px-2 py-1.5 text-[11px] file:ml-2 file:rounded file:border-0 file:bg-teal-700 file:px-2.5 file:py-1 file:text-[11px] file:font-semibold file:text-white dark:border-slate-700 dark:bg-slate-950"
                />
              </div>

              <button
                type="submit"
                disabled={uploadScanMut.isPending || !selectedFile}
                className="inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                <Upload className="h-3.5 w-3.5" />
                {uploadScanMut.isPending ? "در حال آپلود اسکن..." : "آپلود فایل اسکن سه‌بعدی"}
              </button>
            </form>
          </div>

          {/* Scan List */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-2.5">
            <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
              <ScanLine className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              فایل‌های اسکن ثبت‌شده ({formatNumberFa(scans.length)})
            </h3>

            {scans.length === 0 ? (
              <p className="py-4 text-center text-xs text-slate-500">
                هنوز اسکن LiDAR یا ابرنقاطی برای این تور بارگذاری نشده است.
              </p>
            ) : (
              <div className="space-y-2">
                {scans.map((s) => {
                  const selected = activeScan?.id === s.id;
                  return (
                    <div
                      key={s.id}
                      onClick={() => setSelectedScanId(s.id)}
                      className={`cursor-pointer rounded-lg border p-3 text-xs transition-colors ${
                        selected
                          ? "border-teal-600 bg-teal-50/50 dark:border-teal-500 dark:bg-teal-950/30"
                          : "border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/40"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate font-bold text-slate-900 dark:text-slate-100" dir="ltr">
                          {s.filename}
                        </span>
                        <StatusText status={s.status} />
                      </div>
                      <div className="mt-1 flex flex-wrap items-center justify-between gap-1 text-[11px] text-slate-500">
                        <span>{translateStatus(s.source_device)}</span>
                        <span className="tabular-nums">
                          {s.format.toUpperCase()} · {formatBytesFa(s.size_bytes)}
                        </span>
                      </div>
                      {s.points_count > 0 && (
                        <div className="mt-1 text-[11px] tabular-nums text-teal-700 dark:text-teal-400">
                          {formatNumberFa(s.points_count)} نقطه هندسی
                          {s.scene_title ? ` · ${s.scene_title}` : ""}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Inspection & 3D Preview Column */}
        <div className="space-y-4 lg:col-span-8">
          {!activeScan ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-900">
              یک فایل اسکن سه‌بعدی (LiDAR / Depth / Point Cloud / Mesh) را بارگذاری یا از فهرست سمت راست انتخاب کنید تا هندسه، ابعاد واقعی، نقشه تراکم و پیش‌نمایش سه‌بعدی آن نمایش داده شود.
            </div>
          ) : (
            <>
              {/* Header & Actions */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <FileCode2 className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100" dir="ltr">
                        {activeScan.filename}
                      </h3>
                      <StatusText status={activeScan.status} />
                    </div>
                    <div className="text-[11px] text-slate-500">
                      منبع: {translateStatus(activeScan.source_device)}
                      {activeScan.floor_title ? ` · ${activeScan.floor_title}` : ""}
                      {activeScan.scene_title ? ` · ${activeScan.scene_title}` : ""}
                      {" · "}ثبت: <DateDisplay value={activeScan.created_at} />
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={processScanMut.isPending}
                      onClick={() => processScanMut.mutate(activeScan.id)}
                      className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                    >
                      <Cpu className="h-3.5 w-3.5" />
                      {processScanMut.isPending
                        ? "در حال پردازش..."
                        : "پردازش و استخراج هندسه سه‌بعدی"}
                    </button>

                    {activeScan.raw_file_url && (
                      <a
                        href={activeScan.raw_file_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200"
                      >
                        <Download className="h-3.5 w-3.5" />
                        فایل خام
                      </a>
                    )}

                    {activeScan.preview_glb_url && (
                      <a
                        href={activeScan.preview_glb_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200"
                      >
                        <Box className="h-3.5 w-3.5" />
                        دانلود GLB
                      </a>
                    )}

                    <button
                      type="button"
                      disabled={deleteScanMut.isPending}
                      onClick={() => deleteScanMut.mutate(activeScan.id)}
                      className="inline-flex h-8 items-center gap-1 rounded-lg border border-rose-300 px-2.5 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-900 dark:text-rose-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      حذف
                    </button>
                  </div>
                </div>

                {/* Extracted Metrics */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                    <div className="text-[11px] text-slate-500">تعداد نقاط سالم</div>
                    <div className="mt-1 text-base font-bold tabular-nums text-slate-900 dark:text-slate-100">
                      {formatNumberFa(activeScan.points_count)}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                    <div className="text-[11px] text-slate-500">ابعاد فضای اسکن (متر)</div>
                    <div className="mt-1 text-sm font-bold tabular-nums text-slate-900 dark:text-slate-100" dir="ltr">
                      {dims
                        ? `${dims.width ?? 0} × ${dims.length ?? 0} × ${dims.height ?? 0} m`
                        : "پردازش‌نشده"}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                    <div className="text-[11px] text-slate-500">زیربنای تخمینی (Footprint)</div>
                    <div className="mt-1 text-base font-bold tabular-nums text-teal-700 dark:text-teal-400">
                      {proc ? `${formatNumberFa(proc.estimated_footprint_sqm)} م²` : "—"}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                    <div className="text-[11px] text-slate-500">تراکم و نقاط پرت</div>
                    <div className="mt-1 text-xs font-semibold tabular-nums text-slate-800 dark:text-slate-200">
                      {proc
                        ? `${formatNumberFa(proc.point_density_per_sqm)} نقطه/م² · ${formatNumberFa(
                            proc.outlier_points_count
                          )} نویز`
                        : "—"}
                    </div>
                  </div>
                </div>

                {activeScan.processing_notes && (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
                    {activeScan.processing_notes}
                  </div>
                )}

                {proc && (
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
                    <span>موتور پردازش: {translateStatus(proc.engine)}</span>
                    {proc.height_stats?.height_m !== undefined && (
                      <span className="tabular-nums">
                        کف تا سقف واقعی: {formatNumberFa(proc.height_stats.height_m)} متر
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Preview Switcher: 3D GLB & Top-Down Density Map */}
              {(previewAsModel || activeScan.density_map_url) && (
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
                      <Eye className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                      بازبینی بصری خروجی اسکن سه‌بعدی
                    </h4>
                    <div className="flex items-center gap-1.5">
                      {previewAsModel && (
                        <button
                          type="button"
                          onClick={() => setShow3DPreview(true)}
                          className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${
                            show3DPreview
                              ? "bg-teal-700 text-white"
                              : "border border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200"
                          }`}
                        >
                          نمای تعاملی ۳D (GLB)
                        </button>
                      )}
                      {activeScan.density_map_url && (
                        <button
                          type="button"
                          onClick={() => setShow3DPreview(false)}
                          className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${
                            !show3DPreview
                              ? "bg-teal-700 text-white"
                              : "border border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200"
                          }`}
                        >
                          نقشه تراکم پلان (Top-Down)
                        </button>
                      )}
                    </div>
                  </div>

                  {show3DPreview && previewAsModel ? (
                    <DollhouseViewer model={previewAsModel} floors={floors} heightClass="h-[420px]" />
                  ) : activeScan.density_map_url ? (
                    <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-950 p-3 dark:border-slate-800">
                      <img
                        src={activeScan.density_map_url}
                        alt={`نقشه تراکم ${activeScan.filename}`}
                        className="mx-auto max-h-[400px] w-auto rounded object-contain"
                      />
                    </div>
                  ) : null}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
