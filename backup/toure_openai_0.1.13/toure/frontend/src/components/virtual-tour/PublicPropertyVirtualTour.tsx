"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Box, Compass, Map as MapIcon } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { formatNumberFa } from "@/lib/formatters";
import type { PublicVirtualTourData, VirtualTourDetail } from "@/lib/types";
import {
  PanoramaViewer,
  type PanoramaViewerHotspot,
  type PanoramaViewerScene,
} from "./PanoramaViewer";
import { DollhouseViewer } from "./DollhouseViewer";

interface PublicPropertyVirtualTourProps {
  propertyId?: string;
  publicSlug?: string;
  /** Present for authenticated agency users; enables a permission-checked draft/preview view. */
  tourId?: string | null;
  accessToken?: string | null;
  agencyId?: string | null;
}

function normalizePrivateTour(raw: VirtualTourDetail): PublicVirtualTourData {
  const scenes = (raw.scenes || []).flatMap((scene) => {
    const panorama =
      scene.current_panorama ||
      scene.panoramas?.find((item) => item.is_current) ||
      scene.panoramas?.[0] ||
      null;
    if (!scene.active || !panorama?.panorama_url) return [];

    return [{
      id: scene.id,
      floor_id: scene.floor_id,
      floor_title: scene.floor_title,
      title: scene.title,
      room_type: scene.room_type,
      description: scene.description,
      is_start_scene: scene.is_start_scene,
      initial_yaw: scene.initial_yaw,
      initial_pitch: scene.initial_pitch,
      panorama_version_id: panorama.id,
      panorama_url: panorama.panorama_url,
      thumbnail_url: panorama.thumbnail_url || scene.thumbnail_url || "",
      width_px: panorama.width_px,
      height_px: panorama.height_px,
      links: (scene.outgoing_links || []).map((link) => ({
        id: link.id,
        target_scene_id: link.target_scene_id,
        target_scene_title: link.target_scene_title,
        yaw: link.yaw,
        pitch: link.pitch,
        title: link.title,
      })),
      hotspots: (scene.hotspots || []).map((hotspot) => ({
        id: hotspot.id,
        kind: hotspot.kind,
        title: hotspot.title,
        body: hotspot.body,
        yaw: hotspot.yaw,
        pitch: hotspot.pitch,
        target_scene_id: hotspot.target_scene_id,
        metadata: hotspot.metadata,
      })),
    }];
  });

  return {
    tour_id: raw.id,
    property_id: raw.property_id,
    publication_version: raw.active_publication?.version || 0,
    public_slug: raw.active_publication?.public_slug || "",
    published_at: raw.published_at || raw.created_at,
    title: raw.title,
    description: raw.description,
    floors: raw.floors,
    scenes,
    floorplans: raw.floorplans || [],
    rooms: raw.rooms || [],
    dollhouse: raw.current_model || null,
  };
}

type PublicViewMode = "panorama" | "dollhouse" | "floorplan";

export function PublicPropertyVirtualTour({
  propertyId,
  publicSlug,
  tourId,
  accessToken,
  agencyId,
}: PublicPropertyVirtualTourProps) {
  const openedRef = useRef<string | null>(null);
  const visitedScenesRef = useRef<Set<string>>(new Set());
  const sessionKeyRef = useRef<string>("");

  const [viewMode, setViewMode] = useState<PublicViewMode>("panorama");

  const tourQ = useQuery({
    queryKey: ["public-property-virtual-tour", propertyId, publicSlug, tourId, agencyId, Boolean(accessToken)],
    enabled: Boolean(publicSlug || propertyId),
    retry: false,
    queryFn: async () => {
      // An authenticated agency user may preview a draft or ready tour. This endpoint
      // enforces tenant permissions and returns signed asset URLs; public visitors never
      // use it and can only receive an active publication snapshot.
      if (!publicSlug && propertyId && tourId && accessToken) {
        try {
          const privateRes = await apiFetch<VirtualTourDetail | { tour: null }>(
            `/api/v1/properties/${propertyId}/virtual-tour`,
            { token: accessToken, agencyId }
          );
          if (privateRes.data && "id" in privateRes.data) {
            return normalizePrivateTour(privateRes.data as VirtualTourDetail);
          }
        } catch {
          // A user without studio access may still view the public publication below.
        }
      }

      const endpoint = publicSlug
        ? `/api/v1/public/virtual-tours/${encodeURIComponent(publicSlug)}`
        : `/api/v1/public/properties/${propertyId}/virtual-tour`;
      const res = await apiFetch<PublicVirtualTourData>(endpoint);
      return res.data;
    },
  });

  const tour = tourQ.data;

  const viewerScenes: PanoramaViewerScene[] = useMemo(() => {
    if (!tour) return [];
    return tour.scenes.map((sc) => ({
      id: sc.id,
      floor_id: sc.floor_id,
      floor_title: sc.floor_title,
      title: sc.title,
      room_type: sc.room_type,
      initial_yaw: sc.initial_yaw,
      initial_pitch: sc.initial_pitch,
      panorama_url: sc.panorama_url,
      thumbnail_url: sc.thumbnail_url,
      links: sc.links,
      hotspots: sc.hotspots,
    }));
  }, [tour]);

  const startScene = useMemo(() => {
    if (!tour) return "";
    return (tour.scenes.find((s) => s.is_start_scene) || tour.scenes[0])?.id || "";
  }, [tour]);

  const [activeSceneId, setActiveSceneId] = useState<string>("");

  useEffect(() => {
    if (startScene && !activeSceneId) {
      setActiveSceneId(startScene);
    }
  }, [startScene, activeSceneId]);

  const recordEvent = (
    eventType: string,
    extra: { scene_id?: string; hotspot_id?: string; duration_sec?: number } = {}
  ) => {
    if (!tour || !tour.public_slug || tour.publication_version < 1) return;
    if (!sessionKeyRef.current) {
      const stored =
        typeof window !== "undefined" ? sessionStorage.getItem("vt_session_key") : null;
      const generated = stored || `vt-${Math.random().toString(36).slice(2, 12)}`;
      if (typeof window !== "undefined") sessionStorage.setItem("vt_session_key", generated);
      sessionKeyRef.current = generated;
    }
    const isMobile = typeof window !== "undefined" && window.innerWidth < 768;
    apiFetch(`/api/v1/public/virtual-tours/${tour.tour_id}/analytics`, {
      method: "POST",
      body: JSON.stringify({
        event_type: eventType,
        session_key: sessionKeyRef.current,
        device_type: isMobile ? "mobile" : "desktop",
        ...extra,
      }),
    }).catch(() => {});
  };

  useEffect(() => {
    if (tour && openedRef.current !== tour.tour_id) {
      openedRef.current = tour.tour_id;
      visitedScenesRef.current = new Set();
      recordEvent("tour_open", { scene_id: startScene || undefined });
    }
  }, [tour?.tour_id, startScene]);

  const handleModeSwitch = (next: PublicViewMode) => {
    setViewMode(next);
    if (next === "dollhouse") {
      recordEvent("dollhouse_open");
    } else if (next === "floorplan") {
      recordEvent("floorplan_open");
    }
  };

  const handleSceneChange = (sceneId: string) => {
    setActiveSceneId(sceneId);
    setViewMode("panorama");
    recordEvent("scene_enter", { scene_id: sceneId });
    visitedScenesRef.current.add(sceneId);
    if (tour && visitedScenesRef.current.size >= tour.scenes.length && tour.scenes.length > 1) {
      recordEvent("tour_complete", { scene_id: sceneId });
    }
  };

  const handleHotspotClick = (hs: PanoramaViewerHotspot) => {
    recordEvent("hotspot_click", { scene_id: activeSceneId, hotspot_id: hs.id });
  };

  if (tourQ.isLoading) {
    return publicSlug ? <div className="mx-auto max-w-6xl p-8 text-center text-sm text-slate-500">در حال بارگذاری تور مجازی…</div> : null;
  }
  if (tourQ.isError) {
    if (publicSlug) {
      return <div className="mx-auto max-w-4xl p-8 text-center"><h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">تور مجازی در دسترس نیست</h1><p className="mt-2 text-sm text-slate-600 dark:text-slate-400">این تور ممکن است از انتشار خارج شده باشد یا لینک آن معتبر نباشد.</p></div>;
    }
    if (tourId) {
      return (
        <section id="virtual-tour" className="rounded-xl border border-amber-200 bg-amber-50 p-5 dark:border-amber-900/60 dark:bg-amber-950/20">
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">تور مجازی این ملک هنوز برای نمایش عمومی آماده نیست</h2>
          <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">تور ثبت شده، اما دریافت اطلاعات آن ممکن نشد. بررسی کن تور منتشر شده باشد و صحنه‌های آن پانورامای معتبر داشته باشند.</p>
        </section>
      );
    }
    return null;
  }
  if (!tour) return null;
  if (viewerScenes.length === 0) {
    return (
      <section id="virtual-tour" className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">تور مجازی ملک</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">تور ساخته شده است، اما هنوز صحنه‌ای با تصویر پانورامای قابل نمایش ندارد.</p>
      </section>
    );
  }

  const hasDollhouse = Boolean(tour.dollhouse?.file_url);
  const hasFloorplans = (tour.floorplans || []).length > 0;
  const activePlan = tour.floorplans?.[0] || null;
  const scaleMPerPx = activePlan?.scale_m_per_px || 0.02;

  return (
    <section
      id="virtual-tour"
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
        <div>
          <h2 className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
            <Compass className="h-4 w-4 text-teal-700 dark:text-teal-400" />
            تور مجازی ۳۶۰ درجه و نمای سه‌بعدی ملک
          </h2>
          {tour.description && (
            <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">{tour.description}</p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {(hasDollhouse || hasFloorplans) && (
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 dark:border-slate-800 dark:bg-slate-950">
              <button
                type="button"
                onClick={() => handleModeSwitch("panorama")}
                className={`inline-flex h-8 items-center gap-1 rounded-md px-3 text-xs font-semibold ${
                  viewMode === "panorama"
                    ? "bg-teal-700 text-white"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-300"
                }`}
              >
                <Compass className="h-3.5 w-3.5" />
                نمای ۳۶۰°
              </button>
              {hasDollhouse && (
                <button
                  type="button"
                  onClick={() => handleModeSwitch("dollhouse")}
                  className={`inline-flex h-8 items-center gap-1 rounded-md px-3 text-xs font-semibold ${
                    viewMode === "dollhouse"
                      ? "bg-teal-700 text-white"
                      : "text-slate-600 hover:text-slate-900 dark:text-slate-300"
                  }`}
                >
                  <Box className="h-3.5 w-3.5" />
                  مدل سه‌بعدی
                </button>
              )}
              {hasFloorplans && (
                <button
                  type="button"
                  onClick={() => handleModeSwitch("floorplan")}
                  className={`inline-flex h-8 items-center gap-1 rounded-md px-3 text-xs font-semibold ${
                    viewMode === "floorplan"
                      ? "bg-teal-700 text-white"
                      : "text-slate-600 hover:text-slate-900 dark:text-slate-300"
                  }`}
                >
                  <MapIcon className="h-3.5 w-3.5" />
                  پلان دو‌بعدی
                </button>
              )}
            </div>
          )}
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {formatNumberFa(tour.floors.length)} طبقه · {formatNumberFa(tour.scenes.length)} فضای سه‌بعدی
          </span>
        </div>
      </div>

      {viewMode === "panorama" && (
        <PanoramaViewer
          scenes={viewerScenes}
          floors={tour.floors}
          activeSceneId={activeSceneId || startScene}
          onSceneChange={handleSceneChange}
          onHotspotClick={handleHotspotClick}
        />
      )}

      {viewMode === "dollhouse" && (
        <DollhouseViewer
          model={tour.dollhouse}
          floors={tour.floors.map((f) => ({ ...f, tour_id: tour.tour_id, description: "", created_at: "" }))}
          rooms={tour.rooms || []}
          onSelectScene={(sceneId) => handleSceneChange(sceneId)}
        />
      )}

      {viewMode === "floorplan" && activePlan && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-slate-50 lg:col-span-8 dark:border-slate-800 dark:bg-slate-950">
            <img src={activePlan.file_url} alt={activePlan.filename} className="block h-auto w-full" />
            <svg
              viewBox={`0 0 ${activePlan.width_px} ${activePlan.height_px}`}
              className="pointer-events-none absolute inset-0 h-full w-full"
            >
              {(tour.rooms || [])
                .filter((r) => r.floor_id === activePlan.floor_id)
                .map((rm) => (
                  <polygon
                    key={rm.id}
                    points={rm.polygon_points
                      .map(([xm, ym]) => `${xm / scaleMPerPx},${ym / scaleMPerPx}`)
                      .join(" ")}
                    fill={rm.color_hex || "#0F766E"}
                    fillOpacity={0.22}
                    stroke={rm.color_hex || "#0F766E"}
                    strokeWidth={3}
                  />
                ))}
            </svg>
          </div>
          <div className="space-y-2 lg:col-span-4">
            <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
              فضاهای پلان ({activePlan.floor_title || "طبقه"})
            </div>
            {(tour.rooms || []).map((rm) => (
              <div
                key={rm.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 p-2.5 text-xs dark:border-slate-800"
              >
                <div>
                  <div className="font-semibold">{rm.label}</div>
                  <div className="text-[11px] text-slate-500 tabular-nums">
                    {formatNumberFa(rm.area_sqm)} م² · محیط {formatNumberFa(rm.perimeter_m)} متر
                  </div>
                </div>
                {rm.scene_id && (
                  <button
                    type="button"
                    onClick={() => handleSceneChange(rm.scene_id!)}
                    className="rounded-md bg-teal-700 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-teal-800"
                  >
                    نمای ۳۶۰°
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
