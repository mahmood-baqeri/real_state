"use client";

import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Eraser, Pentagon, Scan, Square, Undo2 } from "lucide-react";
import "leaflet/dist/leaflet.css";
import { apiFetch } from "@/lib/api-client";
import { useTheme } from "@/lib/theme-context";
import { formatMoney, formatNumberFa } from "@/lib/formatters";
import type { CurrencyCode } from "@/lib/types";

export interface MapMarkerItem {
  id: string;
  title: string;
  lat: number;
  lng: number;
  priceText?: string;
  subtitle?: string;
  coverUrl?: string | null;
  hideExactAddress?: boolean;
  href?: string;
}

export interface GeoBounds {
  min_lat: number;
  max_lat: number;
  min_lng: number;
  max_lng: number;
}

interface LocalizationMapConfig {
  map_provider?: {
    provider_key: string;
    tile_url: string;
    dark_tile_url?: string;
    attribution?: string;
    max_zoom?: number;
  };
}

type DrawTool = "none" | "rectangle" | "polygon";

export function InteractiveMap({
  markers,
  center = [35.7575, 51.41],
  zoom = 12,
  heightClass = "h-[460px]",
  enableDrawing = false,
  selectedId = null,
  highlightedId = null,
  activePolygon = null,
  onBoundsChange,
  onApplyVisibleBounds,
  onPolygonChange,
  onSelectMarker,
}: {
  markers: MapMarkerItem[];
  center?: [number, number];
  zoom?: number;
  heightClass?: string;
  enableDrawing?: boolean;
  selectedId?: string | null;
  highlightedId?: string | null;
  activePolygon?: [number, number][] | null;
  onBoundsChange?: (bounds: GeoBounds) => void;
  onApplyVisibleBounds?: (bounds: GeoBounds) => void;
  onPolygonChange?: (polygon: [number, number][] | null) => void;
  onSelectMarker?: (id: string) => void;
}) {
  const { resolvedTheme } = useTheme();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<import("leaflet").Map | null>(null);
  const tileLayerRef = useRef<import("leaflet").TileLayer | null>(null);
  const markerLayerRef = useRef<import("leaflet").LayerGroup | null>(null);
  const drawLayerRef = useRef<import("leaflet").LayerGroup | null>(null);

  const [drawTool, setDrawTool] = useState<DrawTool>("none");
  const [vertices, setVertices] = useState<[number, number][]>(activePolygon || []);
  const [rectStart, setRectStart] = useState<[number, number] | null>(null);
  const [currentZoom, setCurrentZoom] = useState<number>(zoom);
  const prevMarkerSigRef = useRef<string>("");

  const drawToolRef = useRef<DrawTool>(drawTool);
  const rectStartRef = useRef<[number, number] | null>(rectStart);
  drawToolRef.current = drawTool;
  rectStartRef.current = rectStart;

  const boundsCallbackRef = useRef(onBoundsChange);
  const selectCallbackRef = useRef(onSelectMarker);
  const polygonCallbackRef = useRef(onPolygonChange);
  boundsCallbackRef.current = onBoundsChange;
  selectCallbackRef.current = onSelectMarker;
  polygonCallbackRef.current = onPolygonChange;

  const locQ = useQuery({
    queryKey: ["map-localization-cfg"],
    staleTime: 5 * 60 * 1000,
    queryFn: async () =>
      (await apiFetch<LocalizationMapConfig>("/api/v1/settings/localization")).data,
  });

  const tileUrl =
    resolvedTheme === "dark" && locQ.data?.map_provider?.dark_tile_url
      ? locQ.data.map_provider.dark_tile_url
      : locQ.data?.map_provider?.tile_url ||
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  const tileAttribution =
    locQ.data?.map_provider?.attribution || "&copy; OpenStreetMap contributors";
  const tileMaxZoom = locQ.data?.map_provider?.max_zoom || 19;

  useEffect(() => {
    if (activePolygon === null) {
      setVertices([]);
      setRectStart(null);
    }
  }, [activePolygon]);

  // Init Leaflet map once
  useEffect(() => {
    let active = true;
    (async () => {
      if (!containerRef.current || mapRef.current) return;
      const L = await import("leaflet");
      if (!active || !containerRef.current) return;

      const map = L.map(containerRef.current, {
        center,
        zoom,
        scrollWheelZoom: true,
      });

      const tl = L.tileLayer(tileUrl, {
        attribution: tileAttribution,
        maxZoom: tileMaxZoom,
      }).addTo(map);

      const mGroup = L.layerGroup().addTo(map);
      const dGroup = L.layerGroup().addTo(map);

      mapRef.current = map;
      tileLayerRef.current = tl;
      markerLayerRef.current = mGroup;
      drawLayerRef.current = dGroup;

      map.on("zoomend", () => {
        setCurrentZoom(map.getZoom());
      });

      map.on("moveend", () => {
        if (!boundsCallbackRef.current) return;
        const b = map.getBounds();
        boundsCallbackRef.current({
          min_lat: Number(b.getSouth().toFixed(5)),
          max_lat: Number(b.getNorth().toFixed(5)),
          min_lng: Number(b.getWest().toFixed(5)),
          max_lng: Number(b.getEast().toFixed(5)),
        });
      });

      map.on("click", (e: import("leaflet").LeafletMouseEvent) => {
        const tool = drawToolRef.current;
        if (tool === "none") return;
        const pt: [number, number] = [
          Number(e.latlng.lat.toFixed(5)),
          Number(e.latlng.lng.toFixed(5)),
        ];
        if (tool === "polygon") {
          setVertices((prev) => [...prev, pt]);
        } else if (tool === "rectangle") {
          const start = rectStartRef.current;
          if (!start) {
            setRectStart(pt);
          } else {
            const minLat = Math.min(start[0], pt[0]);
            const maxLat = Math.max(start[0], pt[0]);
            const minLng = Math.min(start[1], pt[1]);
            const maxLng = Math.max(start[1], pt[1]);
            const rectPoly: [number, number][] = [
              [minLat, minLng],
              [maxLat, minLng],
              [maxLat, maxLng],
              [minLat, maxLng],
            ];
            setVertices(rectPoly);
            setRectStart(null);
            setDrawTool("none");
            polygonCallbackRef.current?.(rectPoly);
          }
        }
      });
    })();

    return () => {
      active = false;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        tileLayerRef.current = null;
        markerLayerRef.current = null;
        drawLayerRef.current = null;
      }
    };
  }, []);

  // Update tile layer dynamically when provider config or dark/light theme changes
  useEffect(() => {
    let active = true;
    (async () => {
      const map = mapRef.current;
      if (!map) return;
      const L = await import("leaflet");
      if (!active) return;
      if (tileLayerRef.current) {
        map.removeLayer(tileLayerRef.current);
      }
      tileLayerRef.current = L.tileLayer(tileUrl, {
        attribution: tileAttribution,
        maxZoom: tileMaxZoom,
      }).addTo(map);
    })();
    return () => {
      active = false;
    };
  }, [tileUrl, tileAttribution, tileMaxZoom]);

  // Render drawn rectangle/polygon overlay
  useEffect(() => {
    let active = true;
    (async () => {
      const dGroup = drawLayerRef.current;
      if (!dGroup) return;
      const L = await import("leaflet");
      if (!active) return;

      dGroup.clearLayers();
      if (rectStart) {
        L.circleMarker(rectStart, {
          radius: 6,
          color: "#b45309",
          fillColor: "#f59e0b",
          fillOpacity: 1,
          weight: 2,
        }).addTo(dGroup);
      }
      if (vertices.length >= 2) {
        if (vertices.length >= 3) {
          L.polygon(vertices, {
            color: "#0f766e",
            fillColor: "#14b8a6",
            fillOpacity: 0.16,
            weight: 2.5,
            dashArray: drawTool === "polygon" ? "6 4" : undefined,
          }).addTo(dGroup);
        } else {
          L.polyline(vertices, { color: "#0f766e", weight: 2.5, dashArray: "6 4" }).addTo(dGroup);
        }
      }
      if (drawTool === "polygon") {
        vertices.forEach((v, idx) => {
          L.circleMarker(v, {
            radius: idx === 0 ? 6 : 4,
            color: "#0f766e",
            fillColor: idx === 0 ? "#f59e0b" : "#ffffff",
            fillOpacity: 1,
            weight: 2,
          }).addTo(dGroup);
        });
      }
    })();
    return () => {
      active = false;
    };
  }, [vertices, rectStart, drawTool]);

  // Render clustered / individual markers with rich popups and list-selection highlight
  useEffect(() => {
    let active = true;
    (async () => {
      const map = mapRef.current;
      const mGroup = markerLayerRef.current;
      if (!map || !mGroup) return;
      const L = await import("leaflet");
      if (!active) return;

      mGroup.clearLayers();
      const valid = markers.filter((m) => Number.isFinite(m.lat) && Number.isFinite(m.lng));

      // Spatial grid clustering when zoom <= 12 and marker count >= 6
      const shouldCluster = valid.length >= 6 && currentZoom <= 12;
      if (shouldCluster) {
        const cellDeg = currentZoom <= 10 ? 0.08 : currentZoom === 11 ? 0.035 : 0.018;
        const clusters = new Map<string, MapMarkerItem[]>();
        for (const m of valid) {
          const k = `${Math.floor(m.lat / cellDeg)}:${Math.floor(m.lng / cellDeg)}`;
          const arr = clusters.get(k) || [];
          arr.push(m);
          clusters.set(k, arr);
        }

        clusters.forEach((groupItems) => {
          if (groupItems.length > 1) {
            const avgLat = groupItems.reduce((s, i) => s + i.lat, 0) / groupItems.length;
            const avgLng = groupItems.reduce((s, i) => s + i.lng, 0) / groupItems.length;
            const icon = L.divIcon({
              className: "bm-cluster-badge",
              html: `<div style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:9999px;background:#0f766e;color:#ffffff;border:3px solid #ffffff;box-shadow:0 4px 12px rgba(15,23,42,0.35);font-family:Vazirmatn,sans-serif;font-weight:800;font-size:13px">${formatNumberFa(groupItems.length)}</div>`,
              iconSize: [36, 36],
              iconAnchor: [18, 18],
            });
            const cMarker = L.marker([avgLat, avgLng], { icon });
            cMarker.on("click", () => {
              map.setView([avgLat, avgLng], Math.min(15, currentZoom + 2), { animate: true });
            });
            cMarker.addTo(mGroup);
            return;
          }
          renderSingleMarker(L, map, mGroup, groupItems[0]);
        });
      } else {
        for (const m of valid) {
          renderSingleMarker(L, map, mGroup, m);
        }
      }

      const sig = valid.map((m) => m.id).join(",");
      if (sig && sig !== prevMarkerSigRef.current && !activePolygon?.length) {
        prevMarkerSigRef.current = sig;
        if (valid.length === 1) {
          map.setView([valid[0].lat, valid[0].lng], 14);
        } else if (valid.length > 1) {
          const latLngs = valid.map((m) => [m.lat, m.lng] as [number, number]);
          map.fitBounds(L.latLngBounds(latLngs), { padding: [36, 36], maxZoom: 14 });
        }
      }
    })();

    function renderSingleMarker(
      L: typeof import("leaflet"),
      map: import("leaflet").Map,
      mGroup: import("leaflet").LayerGroup,
      m: MapMarkerItem
    ) {
      const isFocused = m.id === selectedId || m.id === highlightedId;
      const imgHtml = m.coverUrl
        ? `<img src="${m.coverUrl}" alt="" style="width:100%;height:88px;object-fit:cover;border-radius:6px;margin-bottom:6px" />`
        : "";
      const linkHtml = m.href
        ? `<div style="margin-top:6px"><a href="${m.href}" style="display:inline-block;padding:4px 10px;border-radius:6px;background:#0f766e;color:#ffffff;font-weight:700;font-size:11px;text-decoration:none">مشاهده جزئیات ملک</a></div>`
        : "";
      const popupHtml = `<div dir="rtl" style="font-family:Vazirmatn,sans-serif;min-width:190px;max-width:220px">
        ${imgHtml}
        <div style="font-weight:700;font-size:12.5px;margin-bottom:3px;color:#0f172a">${m.title}</div>
        ${m.subtitle ? `<div style="font-size:11px;color:#475569">${m.subtitle}</div>` : ""}
        ${m.priceText ? `<div style="font-weight:800;color:#0f766e;margin-top:4px;font-size:12px">${m.priceText}</div>` : ""}
        ${m.hideExactAddress ? `<div style="font-size:10px;color:#64748b;margin-top:3px">محدوده تقریبی (حفظ حریم مالک)</div>` : ""}
        ${linkHtml}
      </div>`;

      if (m.hideExactAddress) {
        const circle = L.circle([m.lat, m.lng], {
          radius: isFocused ? 520 : 400,
          color: isFocused ? "#b45309" : "#0f766e",
          fillColor: isFocused ? "#f59e0b" : "#14b8a6",
          fillOpacity: isFocused ? 0.36 : 0.2,
          weight: isFocused ? 3 : 2,
        });
        circle.bindPopup(popupHtml);
        circle.on("click", () => selectCallbackRef.current?.(m.id));
        circle.addTo(mGroup);
        if (m.id === selectedId) {
          circle.openPopup();
          map.panTo([m.lat, m.lng], { animate: true });
        }
      } else {
        const marker = L.circleMarker([m.lat, m.lng], {
          radius: isFocused ? 11 : 8,
          color: "#ffffff",
          weight: 2.5,
          fillColor: isFocused ? "#b45309" : "#0f766e",
          fillOpacity: 1,
        });
        marker.bindPopup(popupHtml);
        marker.on("click", () => selectCallbackRef.current?.(m.id));
        marker.addTo(mGroup);
        if (m.id === selectedId) {
          marker.openPopup();
          map.panTo([m.lat, m.lng], { animate: true });
        }
      }
    }

    return () => {
      active = false;
    };
  }, [markers, currentZoom, selectedId, highlightedId, activePolygon]);

  const handleApplyVisible = () => {
    const map = mapRef.current;
    if (!map) return;
    const b = map.getBounds();
    const bounds: GeoBounds = {
      min_lat: Number(b.getSouth().toFixed(5)),
      max_lat: Number(b.getNorth().toFixed(5)),
      min_lng: Number(b.getWest().toFixed(5)),
      max_lng: Number(b.getEast().toFixed(5)),
    };
    onApplyVisibleBounds?.(bounds);
  };

  return (
    <div className="space-y-2">
      {enableDrawing && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-2 text-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={handleApplyVisible}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 font-semibold text-slate-700 hover:border-teal-600 hover:text-teal-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              <Scan className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
              محدوده دید فعلی
            </button>

            <button
              type="button"
              onClick={() => {
                setVertices([]);
                setRectStart(null);
                setDrawTool(drawTool === "rectangle" ? "none" : "rectangle");
              }}
              className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 font-semibold transition-colors ${
                drawTool === "rectangle"
                  ? "border-amber-600 bg-amber-50 text-amber-800 dark:border-amber-500 dark:bg-amber-950/60 dark:text-amber-300"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:border-teal-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              }`}
            >
              <Square className="h-3.5 w-3.5" />
              {drawTool === "rectangle"
                ? rectStart
                  ? "نقطه دوم مستطیل را بزنید"
                  : "نقطه اول مستطیل را بزنید"
                : "انتخاب مستطیل"}
            </button>

            <button
              type="button"
              onClick={() => {
                setRectStart(null);
                if (drawTool === "polygon") {
                  setDrawTool("none");
                } else {
                  setVertices([]);
                  setDrawTool("polygon");
                }
              }}
              className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 font-semibold transition-colors ${
                drawTool === "polygon"
                  ? "border-teal-700 bg-teal-50 text-teal-800 dark:border-teal-500 dark:bg-teal-950/60 dark:text-teal-300"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:border-teal-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              }`}
            >
              <Pentagon className="h-3.5 w-3.5" />
              رسم چندضلعی
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            {drawTool === "polygon" && vertices.length > 0 && (
              <button
                type="button"
                onClick={() => setVertices((prev) => prev.slice(0, -1))}
                className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 px-2 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300"
              >
                <Undo2 className="h-3.5 w-3.5" />
                برگشت
              </button>
            )}
            {drawTool === "polygon" && vertices.length >= 3 && (
              <button
                type="button"
                onClick={() => {
                  setDrawTool("none");
                  onPolygonChange?.(vertices);
                }}
                className="inline-flex h-8 items-center gap-1 rounded-lg bg-teal-700 px-3 font-semibold text-white hover:bg-teal-800"
              >
                <Check className="h-3.5 w-3.5" />
                تأیید چندضلعی ({formatNumberFa(vertices.length)})
              </button>
            )}
            {(vertices.length > 0 || (activePolygon && activePolygon.length > 0)) && (
              <button
                type="button"
                onClick={() => {
                  setVertices([]);
                  setRectStart(null);
                  setDrawTool("none");
                  onPolygonChange?.(null);
                }}
                className="inline-flex h-8 items-center gap-1 rounded-lg border border-rose-200 bg-rose-50 px-2.5 font-semibold text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
              >
                <Eraser className="h-3.5 w-3.5" />
                پاک کردن
              </button>
            )}
          </div>
        </div>
      )}

      <div className="relative">
        <div
          ref={containerRef}
          className={`w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-800 ${
            drawTool !== "none" ? "cursor-crosshair" : ""
          } ${heightClass}`}
        />
        {drawTool !== "none" && (
          <div className="pointer-events-none absolute top-3 right-3 z-20 rounded-lg border border-amber-300 bg-amber-50/95 px-3 py-1.5 text-[11px] font-bold text-amber-900 shadow dark:border-amber-700 dark:bg-slate-900/95 dark:text-amber-300">
            {drawTool === "polygon"
              ? "روی نقشه نقاط محدوده را کلیک کنید و سپس دکمه «تأیید چندضلعی» را بزنید"
              : rectStart
              ? "گوشه مقابل مستطیل را روی نقشه کلیک کنید"
              : "گوشه اول مستطیل جستجو را روی نقشه کلیک کنید"}
          </div>
        )}
      </div>
    </div>
  );
}

export function buildPropertyPriceLabel(
  totalPrice: string,
  depositAmount: string,
  rentAmount: string,
  dealTypeId: string,
  currency: CurrencyCode
): string {
  if (dealTypeId === "MORTGAGE_RENT") {
    return `ودیعه: ${formatMoney(depositAmount, currency, currency)} · اجاره: ${formatMoney(
      rentAmount,
      currency,
      currency
    )}`;
  }
  return formatMoney(totalPrice, currency, currency);
}
