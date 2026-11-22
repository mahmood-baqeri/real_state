"use client";

import React, { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Box,
  DoorOpen,
  Layers,
  Map,
  Plus,
  Ruler,
  Trash2,
  Upload,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa } from "@/lib/formatters";
import type {
  FloorPlanAssetItem,
  RoomGeometryItem,
  TourFloorItem,
  TourSceneItem,
  VirtualTourRoomTypeOption,
  WallSegmentItem,
} from "@/lib/types";

interface FloorPlanEditorProps {
  tourId: string;
  floors: TourFloorItem[];
  scenes: TourSceneItem[];
  roomTypes: VirtualTourRoomTypeOption[];
  floorplans: FloorPlanAssetItem[];
  rooms: RoomGeometryItem[];
  walls: WallSegmentItem[];
  onUpdated: () => void;
  onModelBuilt?: () => void;
}

type ToolMode = "calibrate" | "draw_room" | "draw_wall";

export function FloorPlanEditor({
  tourId,
  floors,
  scenes,
  roomTypes,
  floorplans,
  rooms,
  walls,
  onUpdated,
  onModelBuilt,
}: FloorPlanEditorProps) {
  const { accessToken, activeAgencyId } = useAuth();
  const [selectedFloorId, setSelectedFloorId] = useState<string>(floors[0]?.id || "");
  const [tool, setTool] = useState<ToolMode>("calibrate");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  // Calibration state (image natural pixel space)
  const [calPointA, setCalPointA] = useState<[number, number] | null>(null);
  const [calPointB, setCalPointB] = useState<[number, number] | null>(null);
  const [calRealDist, setCalRealDist] = useState("5.0");

  // Room drawing state
  const [draftVerticesM, setDraftVerticesM] = useState<[number, number][]>([]);
  const [roomLabel, setRoomLabel] = useState("");
  const [roomType, setRoomType] = useState("living_room");
  const [roomSceneId, setRoomSceneId] = useState("");
  const [roomHeightM, setRoomHeightM] = useState("2.9");

  // Wall drawing state
  const [wallStartM, setWallStartM] = useState<[number, number] | null>(null);
  const [wallThicknessM, setWallThicknessM] = useState("0.18");
  const [openingWallId, setOpeningWallId] = useState("");
  const [openingKind, setOpeningKind] = useState<"door" | "window" | "arch" | "balcony">("door");
  const [openingWidthM, setOpeningWidthM] = useState("1.0");

  const activeFloorId = selectedFloorId || floors[0]?.id || "";
  const activePlan = useMemo(
    () => floorplans.find((fp) => fp.floor_id === activeFloorId) || null,
    [floorplans, activeFloorId]
  );

  const floorRooms = useMemo(
    () => rooms.filter((r) => !activeFloorId || r.floor_id === activeFloorId),
    [rooms, activeFloorId]
  );

  const floorWalls = useMemo(
    () => walls.filter((w) => !activeFloorId || w.floor_id === activeFloorId),
    [walls, activeFloorId]
  );

  const scaleMPerPx =
    activePlan?.scale_m_per_px && activePlan.scale_m_per_px > 0
      ? activePlan.scale_m_per_px
      : null;
  const canDraw = Boolean(activePlan && scaleMPerPx);

  const uploadPlanMut = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("floor_id", activeFloorId);
      fd.append("file", file);
      return apiFetch<FloorPlanAssetItem>(`/api/v1/virtual-tours/${tourId}/floorplans`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: fd,
      });
    },
    onSuccess: () => {
      setErrMsg(null);
      setNotice("فایل پلان بارگذاری شد. اکنون با ابزار کالیبراسیون مقیاس واقعی متر را تعیین کنید.");
      setCalPointA(null);
      setCalPointB(null);
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const calibrateMut = useMutation({
    mutationFn: async () => {
      if (!activePlan || !calPointA || !calPointB) {
        throw new Error("ابتدا دو نقطه را روی تصویر پلان انتخاب کنید.");
      }
      return apiFetch<FloorPlanAssetItem>(`/api/v1/floorplans/${activePlan.id}/calibrate`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          point_a: calPointA,
          point_b: calPointB,
          real_distance_m: Number(calRealDist),
        }),
      });
    },
    onSuccess: (res) => {
      setErrMsg(null);
      setNotice(`کالیبراسیون ذخیره شد: هر پیکسل معادل ${res.data.scale_m_per_px} متر است.`);
      setTool("draw_room");
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createRoomMut = useMutation({
    mutationFn: async () =>
      apiFetch<RoomGeometryItem>(`/api/v1/virtual-tours/${tourId}/rooms`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          floor_id: activeFloorId,
          scene_id: roomSceneId || null,
          floorplan_id: activePlan?.id || null,
          label: roomLabel.trim() || "فضای جدید",
          room_type: roomType,
          polygon_points: draftVerticesM,
          height_m: Number(roomHeightM) || 2.9,
        }),
      }),
    onSuccess: (res) => {
      setDraftVerticesM([]);
      setRoomLabel("");
      setErrMsg(null);
      setNotice(`اتاق «${res.data.label}» با مساحت ${res.data.area_sqm} مترمربع ثبت شد.`);
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteRoomMut = useMutation({
    mutationFn: async (roomId: string) =>
      apiFetch(`/api/v1/rooms/${roomId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createWallMut = useMutation({
    mutationFn: async ([s, e]: [[number, number], [number, number]]) =>
      apiFetch<WallSegmentItem>(`/api/v1/virtual-tours/${tourId}/walls`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          floor_id: activeFloorId,
          floorplan_id: activePlan?.id || null,
          start_x: s[0],
          start_y: s[1],
          end_x: e[0],
          end_y: e[1],
          thickness_m: Number(wallThicknessM) || 0.18,
          height_m: Number(roomHeightM) || 2.9,
        }),
      }),
    onSuccess: () => {
      setWallStartM(null);
      setErrMsg(null);
      setNotice("قطعه دیوار به پلان طبقه اضافه شد.");
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteWallMut = useMutation({
    mutationFn: async (wallId: string) =>
      apiFetch(`/api/v1/walls/${wallId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => onUpdated(),
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createOpeningMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/walls/${openingWallId}/openings`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          kind: openingKind,
          offset_ratio: 0.5,
          width_m: Number(openingWidthM) || 1.0,
          height_m: openingKind === "window" ? 1.5 : 2.1,
          sill_height_m: openingKind === "window" ? 0.85 : 0.0,
        }),
      }),
    onSuccess: () => {
      setNotice("درب/پنجره روی دیوار ثبت شد.");
      onUpdated();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const build3DMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/virtual-tours/${tourId}/generate-3d`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          wall_height_m: Number(roomHeightM) || 2.9,
          wall_thickness_m: Number(wallThicknessM) || 0.18,
        }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("مدل سه‌بعدی Dollhouse (GLB) با موفقیت تولید شد.");
      onUpdated();
      onModelBuilt?.();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const handlePlanSvgClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!activePlan) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * activePlan.width_px;
    const py = ((e.clientY - rect.top) / rect.height) * activePlan.height_px;
    if (tool !== "calibrate" && !scaleMPerPx) {
      setErrMsg("برای ترسیم، ابتدا مقیاس همین پلان را کالیبره کنید.");
      return;
    }
    const xm = scaleMPerPx ? Math.round(px * scaleMPerPx * 100) / 100 : 0;
    const ym = scaleMPerPx ? Math.round(py * scaleMPerPx * 100) / 100 : 0;

    if (tool === "calibrate") {
      if (!calPointA || (calPointA && calPointB)) {
        setCalPointA([Math.round(px), Math.round(py)]);
        setCalPointB(null);
      } else {
        setCalPointB([Math.round(px), Math.round(py)]);
      }
      return;
    }

    if (tool === "draw_room") {
      setDraftVerticesM((prev) => [...prev, [xm, ym]]);
      return;
    }

    if (tool === "draw_wall") {
      if (!wallStartM) {
        setWallStartM([xm, ym]);
      } else {
        createWallMut.mutate([wallStartM, [xm, ym]]);
      }
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Right Controls Sidebar */}
      <div className="space-y-4 lg:col-span-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
              <Layers className="h-4 w-4 text-teal-700 dark:text-teal-400" />
              تنظیمات پلان طبقه
            </h3>
            <select
              value={activeFloorId}
              onChange={(e) => {
                setSelectedFloorId(e.target.value);
                setTool("calibrate");
                setCalPointA(null);
                setCalPointB(null);
                setDraftVerticesM([]);
                setWallStartM(null);
                setErrMsg(null);
                setNotice(null);
              }}
              className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
            >
              {floors.map((fl) => (
                <option key={fl.id} value={fl.id}>
                  {fl.title}
                </option>
              ))}
            </select>
          </div>

          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-teal-500/60 bg-teal-50/40 px-3 py-2.5 text-xs font-semibold text-teal-800 hover:bg-teal-50 dark:bg-teal-950/20 dark:text-teal-300">
            <Upload className="h-4 w-4" />
            <span>{uploadPlanMut.isPending ? "در حال آپلود..." : "آپلود تصویر/PDF پلان معماری"}</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,application/pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) uploadPlanMut.mutate(f);
              }}
            />
          </label>

          {!activePlan && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
              برای این طبقه هنوز پلان فعالی ثبت نشده است. ابتدا تصویر یا PDF پلان همین طبقه را بارگذاری کنید.
            </div>
          )}

          {activePlan && (
            <div className="rounded-lg border border-slate-200 p-2.5 text-[11px] text-slate-600 dark:border-slate-800 dark:text-slate-400 space-y-1">
              <div className="flex justify-between">
                <span>فایل فعال:</span>
                <span className="font-mono font-semibold">{activePlan.filename}</span>
              </div>
              <div className="flex justify-between">
                <span>وضعیت مقیاس متری:</span>
                <span className="font-semibold text-teal-700 dark:text-teal-400">
                  {activePlan.scale_m_per_px ? `کالیبره‌شده (${activePlan.scale_m_per_px} m/px)` : "نیاز به کالیبراسیون"}
                </span>
              </div>
            </div>
          )}

          {/* Tool Selector */}
          <div className="grid grid-cols-3 gap-1.5 pt-1">
            {[
              { id: "calibrate" as const, label: "کالیبراسیون", icon: Ruler },
              { id: "draw_room" as const, label: "ترسیم اتاق", icon: Map },
              { id: "draw_wall" as const, label: "ترسیم دیوار", icon: DoorOpen },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setTool(item.id)}
                  disabled={(item.id === "draw_room" || item.id === "draw_wall") && !canDraw}
                  className={`flex h-9 items-center justify-center gap-1 rounded-lg border text-[11px] font-semibold ${
                    tool === item.id
                      ? "border-teal-700 bg-teal-700 text-white"
                      : "border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
                  } disabled:cursor-not-allowed disabled:opacity-40`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Tool-specific Panel */}
        {tool === "calibrate" && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-2.5 text-xs">
            <div className="font-bold text-slate-900 dark:text-slate-100">۱. کالیبراسیون دو‌نقطه‌ای (پیکسل به متر)</div>
            <p className="text-[11px] text-slate-500">
              روی پلان دو نقطه با فاصله مشخص (مثلاً طول یک دیوار یا دهانه پنجره) کلیک کنید و متراژ واقعی آن را وارد نمایید.
            </p>
            <div className="flex items-center justify-between text-[11px] tabular-nums">
              <span>نقطه الف: {calPointA ? `${calPointA[0]}, ${calPointA[1]}` : "انتخاب نشده"}</span>
              <span>نقطه ب: {calPointB ? `${calPointB[0]}, ${calPointB[1]}` : "انتخاب نشده"}</span>
            </div>
            <div className="flex gap-2">
              <input
                type="number"
                step="0.1"
                value={calRealDist}
                onChange={(e) => setCalRealDist(e.target.value)}
                placeholder="متراژ واقعی (متر)"
                className="h-8 flex-1 rounded-lg border border-slate-300 px-2.5 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
              />
              <button
                type="button"
                disabled={!calPointA || !calPointB || calibrateMut.isPending}
                onClick={() => calibrateMut.mutate()}
                className="h-8 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white disabled:opacity-50"
              >
                ثبت مقیاس
              </button>
            </div>
          </div>
        )}

        {tool === "draw_room" && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-2.5 text-xs">
            <div className="font-bold text-slate-900 dark:text-slate-100">۲. ثبت محدوده و متراژ اتاق</div>
            <p className="text-[11px] text-slate-500">
              گوشه‌های اتاق را روی پلان کلیک کنید ({formatNumberFa(draftVerticesM.length)} نقطه ثبت شده، حداقل ۳ نقطه لازم است).
            </p>
            <input
              value={roomLabel}
              onChange={(e) => setRoomLabel(e.target.value)}
              placeholder="نام اتاق (مثلاً سالن پذیرایی)"
              className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <div className="grid grid-cols-2 gap-1.5">
              <select
                value={roomType}
                onChange={(e) => setRoomType(e.target.value)}
                className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
              >
                {roomTypes.map((rt) => (
                  <option key={rt.code} value={rt.code}>
                    {rt.label_fa}
                  </option>
                ))}
              </select>
              <input
                type="number"
                step="0.1"
                value={roomHeightM}
                onChange={(e) => setRoomHeightM(e.target.value)}
                placeholder="ارتفاع سقف (m)"
                className="h-8 rounded-lg border border-slate-300 px-2 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
              />
            </div>
            <select
              value={roomSceneId}
              onChange={(e) => setRoomSceneId(e.target.value)}
              className="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
            >
              <option value="">اتصال اختیاری به صحنه ۳۶۰°...</option>
              {scenes.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.title} ({sc.floor_title})
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={!canDraw || draftVerticesM.length < 3 || createRoomMut.isPending}
                onClick={() => createRoomMut.mutate()}
                className="inline-flex h-8 flex-1 items-center justify-center gap-1 rounded-lg bg-teal-700 text-xs font-semibold text-white disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" />
                ذخیره اتاق
              </button>
              {draftVerticesM.length > 0 && (
                <button
                  type="button"
                  onClick={() => setDraftVerticesM([])}
                  className="h-8 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700"
                >
                  پاک‌کردن
                </button>
              )}
            </div>
          </div>
        )}

        {tool === "draw_wall" && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-2.5 text-xs">
            <div className="font-bold text-slate-900 dark:text-slate-100">۳. ترسیم دیوار و بازشوها (درب/پنجره)</div>
            <p className="text-[11px] text-slate-500">
              {wallStartM
                ? `نقطه شروع دیوار: (${wallStartM[0]}, ${wallStartM[1]}) — نقطه پایان را روی پلان کلیک کنید.`
                : "روی نقطه شروع و سپس نقطه پایان دیوار روی پلان کلیک کنید."}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-[11px]">ضخامت دیوار (m):</span>
              <input
                type="number"
                step="0.02"
                value={wallThicknessM}
                onChange={(e) => setWallThicknessM(e.target.value)}
                className="h-8 w-20 rounded-lg border border-slate-300 px-2 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
              />
            </div>
            {floorWalls.length > 0 && (
              <div className="space-y-2 border-t border-slate-100 pt-2.5 dark:border-slate-800">
                <div className="text-[11px] font-semibold">افزودن درب / پنجره به دیوار:</div>
                <select
                  value={openingWallId}
                  onChange={(e) => setOpeningWallId(e.target.value)}
                  className="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                >
                  <option value="">انتخاب دیوار...</option>
                  {floorWalls.map((w, i) => (
                    <option key={w.id} value={w.id}>
                      دیوار {formatNumberFa(i + 1)} ({w.start_x},{w.start_y} → {w.end_x},{w.end_y})
                    </option>
                  ))}
                </select>
                <div className="grid grid-cols-3 gap-1.5">
                  <select
                    value={openingKind}
                    onChange={(e) => setOpeningKind(e.target.value as "door" | "window" | "arch" | "balcony")}
                    className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="door">درب</option>
                    <option value="window">پنجره</option>
                    <option value="arch">قوس</option>
                    <option value="balcony">بالکن</option>
                  </select>
                  <input
                    type="number"
                    step="0.1"
                    value={openingWidthM}
                    onChange={(e) => setOpeningWidthM(e.target.value)}
                    placeholder="عرض (m)"
                    className="h-8 rounded-lg border border-slate-300 px-2 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
                  />
                  <button
                    type="button"
                    disabled={!openingWallId || createOpeningMut.isPending}
                    onClick={() => createOpeningMut.mutate()}
                    className="h-8 rounded-lg bg-slate-900 text-xs font-semibold text-white disabled:opacity-50 dark:bg-teal-700"
                  >
                    افزودن
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <button
          type="button"
          disabled={build3DMut.isPending || (rooms.length === 0 && walls.length === 0)}
          onClick={() => build3DMut.mutate()}
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-teal-700 text-xs font-bold text-white hover:bg-teal-800 disabled:opacity-50"
        >
          <Box className="h-4 w-4" />
          {build3DMut.isPending ? "در حال ساخت مدل GLB..." : "تولید مدل سه‌بعدی Dollhouse (GLB)"}
        </button>

        {notice && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-xs text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200">
            {notice}
          </div>
        )}
        {errMsg && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-900 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
            {errMsg}
          </div>
        )}
      </div>

      {/* Main Blueprint Canvas + Lists */}
      <div className="space-y-4 lg:col-span-8">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
          {activePlan ? (
            <div className="relative w-full">
              <img
                src={activePlan.file_url}
                alt={activePlan.filename}
                className="block h-auto w-full select-none"
              />
              <svg
                viewBox={`0 0 ${activePlan.width_px} ${activePlan.height_px}`}
                onClick={handlePlanSvgClick}
                className="absolute inset-0 h-full w-full cursor-crosshair"
              >
                {/* Existing room polygons */}
                {floorRooms.map((rm) => {
                  const pts = rm.polygon_points
                    .map(([xm, ym]) => `${xm / (scaleMPerPx ?? 1)},${ym / (scaleMPerPx ?? 1)}`)
                    .join(" ");
                  return (
                    <polygon
                      key={rm.id}
                      points={pts}
                      fill={rm.color_hex || "#0F766E"}
                      fillOpacity={0.28}
                      stroke={rm.color_hex || "#0F766E"}
                      strokeWidth={3}
                    />
                  );
                })}

                {/* Existing wall segments */}
                {(scaleMPerPx ? floorWalls : []).map((w) => (
                  <line
                    key={w.id}
                    x1={w.start_x / (scaleMPerPx ?? 1)}
                    y1={w.start_y / (scaleMPerPx ?? 1)}
                    x2={w.end_x / (scaleMPerPx ?? 1)}
                    y2={w.end_y / (scaleMPerPx ?? 1)}
                    stroke="#0F172A"
                    strokeWidth={Math.max(4, w.thickness_m / (scaleMPerPx ?? 1))}
                    strokeLinecap="round"
                  />
                ))}

                {/* Draft polygon preview */}
                {draftVerticesM.length > 0 && (
                  <>
                    <polyline
                      points={draftVerticesM
                        .map(([xm, ym]) => `${xm / (scaleMPerPx ?? 1)},${ym / (scaleMPerPx ?? 1)}`)
                        .join(" ")}
                      fill="none"
                      stroke="#D97706"
                      strokeWidth={3}
                      strokeDasharray="6 4"
                    />
                    {draftVerticesM.map(([xm, ym], i) => (
                      <circle
                        key={i}
                        cx={xm / (scaleMPerPx ?? 1)}
                        cy={ym / (scaleMPerPx ?? 1)}
                        r={6}
                        fill="#D97706"
                      />
                    ))}
                  </>
                )}

                {/* Calibration line */}
                {calPointA && (
                  <circle cx={calPointA[0]} cy={calPointA[1]} r={7} fill="#E11D48" />
                )}
                {calPointB && (
                  <circle cx={calPointB[0]} cy={calPointB[1]} r={7} fill="#E11D48" />
                )}
                {calPointA && calPointB && (
                  <line
                    x1={calPointA[0]}
                    y1={calPointA[1]}
                    x2={calPointB[0]}
                    y2={calPointB[1]}
                    stroke="#E11D48"
                    strokeWidth={3}
                    strokeDasharray="5 4"
                  />
                )}
              </svg>
            </div>
          ) : (
            <div className="p-10 text-center text-xs text-slate-500">
              هنوز پلانی برای این طبقه بارگذاری نشده است. فایل پلان (PNG/JPG/PDF) را از ستون کناری آپلود کنید.
            </div>
          )}
        </div>

        {/* Rooms & Walls summary */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-2">
            <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
              اتاق‌های ثبت‌شده ({formatNumberFa(floorRooms.length)})
            </h4>
            {floorRooms.length === 0 ? (
              <p className="text-[11px] text-slate-500">اتاقی در این طبقه تعریف نشده است.</p>
            ) : (
              <div className="space-y-1.5">
                {(scaleMPerPx ? floorRooms : []).map((rm) => (
                  <div
                    key={rm.id}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-800"
                  >
                    <div>
                      <div className="font-semibold">{rm.label}</div>
                      <div className="text-[11px] text-slate-500 tabular-nums">
                        {formatNumberFa(rm.area_sqm)} م² · محیط {formatNumberFa(rm.perimeter_m)} متر
                        {rm.scene_title ? ` · متصل به ${rm.scene_title}` : ""}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => deleteRoomMut.mutate(rm.id)}
                      className="text-rose-600 hover:text-rose-800"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-2">
            <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
              دیوارها و بازشوها ({formatNumberFa(floorWalls.length)})
            </h4>
            {floorWalls.length === 0 ? (
              <p className="text-[11px] text-slate-500">
                دیوار صریح تعریف نشده (هنگام ساخت مدل سه‌بعدی به‌طور خودکار از محیط اتاق‌ها تولید می‌شود).
              </p>
            ) : (
              <div className="space-y-1.5">
                {floorWalls.map((w, idx) => (
                  <div
                    key={w.id}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-800"
                  >
                    <div className="tabular-nums">
                      <span className="font-semibold">دیوار {formatNumberFa(idx + 1)}</span>
                      <span className="mr-2 text-[11px] text-slate-500">
                        ({w.start_x},{w.start_y}) → ({w.end_x},{w.end_y}) · {(w.openings || []).length} بازشو
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => deleteWallMut.mutate(w.id)}
                      className="text-rose-600 hover:text-rose-800"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
