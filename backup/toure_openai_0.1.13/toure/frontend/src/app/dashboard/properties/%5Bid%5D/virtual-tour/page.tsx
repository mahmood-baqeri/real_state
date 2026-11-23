"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Archive,
  BarChart3,
  Box,
  Camera,
  Check,
  CheckCircle2,
  Compass,
  Cpu,
  ExternalLink,
  Layers,
  Map,
  MapPin,
  Navigation,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
  Trash2,
  XCircle,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa, translateStatus } from "@/lib/formatters";
import type {
  ProcessingJobItem,
  TourAnalyticsSummary,
  TourQualityReportItem,
  VirtualTourDetail,
  VirtualTourGetEnvelope,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";
import {
  PanoramaViewer,
  type PanoramaViewerScene,
} from "@/components/virtual-tour/PanoramaViewer";
import { GuidedMobileCapture } from "@/components/virtual-tour/GuidedMobileCapture";
import { FloorPlanEditor } from "@/components/virtual-tour/FloorPlanEditor";
import { DollhouseViewer } from "@/components/virtual-tour/DollhouseViewer";
import { DEFAULT_VIRTUAL_TOUR_ROOM_TYPES, roomTypeLabel } from "@/lib/virtual-tour-room-types";

type StudioTab = "overview" | "capture" | "editor" | "floorplan" | "dollhouse" | "jobs" | "analytics";

export default function PropertyVirtualTourStudioPage() {
  const params = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { accessToken, activeAgencyId, effectiveRole, hasPermission } = useAuth();

  const [tab, setTab] = useState<StudioTab>("overview");
  const [selectedSceneId, setSelectedSceneId] = useState<string>("");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  // Form states
  const [newFloorTitle, setNewFloorTitle] = useState("");
  const [newFloorElev, setNewFloorElev] = useState("3.0");
  const [newSceneTitle, setNewSceneTitle] = useState("");
  const [newSceneFloorId, setNewSceneFloorId] = useState("");
  const [newSceneRoomType, setNewSceneRoomType] = useState("living_room");

  // Link & Hotspot editor states
  const [pickTarget, setPickTarget] = useState<"none" | "link" | "hotspot">("none");
  const [linkTargetSceneId, setLinkTargetSceneId] = useState("");
  const [linkTitle, setLinkTitle] = useState("");
  const [linkYaw, setLinkYaw] = useState(0);
  const [linkPitch, setLinkPitch] = useState(0);
  const [linkBidirectional, setLinkBidirectional] = useState(true);

  const [hsKind, setHsKind] = useState<"info" | "feature" | "measurement">("info");
  const [hsTitle, setHsTitle] = useState("");
  const [hsBody, setHsBody] = useState("");
  const [hsYaw, setHsYaw] = useState(20);
  const [hsPitch, setHsPitch] = useState(-5);
  const [rejectReason, setRejectReason] = useState("");

  // Live WS jobs override
  const [liveJobs, setLiveJobs] = useState<ProcessingJobItem[] | null>(null);

  const vtQuery = useQuery({
    queryKey: ["property-virtual-tour", params.id, activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () => {
      const res = await apiFetch<VirtualTourDetail | VirtualTourGetEnvelope>(
        `/api/v1/properties/${params.id}/virtual-tour`,
        {
          token: accessToken,
          agencyId: activeAgencyId,
        }
      );
      return res.data;
    },
  });

  const tour: VirtualTourDetail | null = useMemo(() => {
    const raw = vtQuery.data;
    if (!raw || ("tour" in raw && raw.tour === null)) return null;
    return raw as VirtualTourDetail;
  }, [vtQuery.data]);

  const configBundle = vtQuery.data?.config;

  useEffect(() => {
    if (!tour) return;
    if (!newSceneFloorId && tour.floors.length > 0) {
      setNewSceneFloorId(tour.floors[0].id);
    }
    if ((!selectedSceneId || !tour.scenes.some((s) => s.id === selectedSceneId)) && tour.scenes.length > 0) {
      const start = tour.scenes.find((s) => s.is_start_scene) || tour.scenes[0];
      setSelectedSceneId(start.id);
    }
  }, [tour, newSceneFloorId, selectedSceneId]);

  const selectedScene = useMemo(() => {
    if (!tour) return null;
    return tour.scenes.find((s) => s.id === selectedSceneId) || tour.scenes[0] || null;
  }, [tour, selectedSceneId]);

  const qualityQ = useQuery({
    queryKey: ["vt-quality-report", tour?.id],
    enabled: !!accessToken && !!tour?.id && tab === "overview",
    queryFn: async () =>
      (
        await apiFetch<TourQualityReportItem>(`/api/v1/virtual-tours/${tour!.id}/quality-report`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const analyticsQ = useQuery({
    queryKey: ["vt-analytics", tour?.id],
    enabled: !!accessToken && !!tour?.id && tab === "analytics",
    queryFn: async () =>
      (
        await apiFetch<TourAnalyticsSummary>(`/api/v1/virtual-tours/${tour!.id}/analytics`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  // WebSocket live processing jobs monitor when Jobs tab is open
  useEffect(() => {
    if (!tour?.id || !accessToken || tab !== "jobs") return;
    if (typeof window === "undefined") return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${proto}://${window.location.hostname}:8020/api/v1/ws/virtual-tours/${tour.id}/jobs?token=${encodeURIComponent(
      accessToken
    )}${activeAgencyId ? `&agency_id=${encodeURIComponent(activeAgencyId)}` : ""}`;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg?.event === "tour_jobs_snapshot" && Array.isArray(msg?.data?.jobs)) {
            setLiveJobs(msg.data.jobs);
          }
        } catch {
          // ignore
        }
      };
    } catch {
      // fallback silently to HTTP state
    }
    return () => {
      if (ws && ws.readyState < 2) ws.close();
    };
  }, [tour?.id, accessToken, activeAgencyId, tab]);

  const refreshTour = () => {
    qc.invalidateQueries({ queryKey: ["property-virtual-tour", params.id] });
    qc.invalidateQueries({ queryKey: ["vt-quality-report", tour?.id] });
  };

  const canApproveOrPublish =
    effectiveRole === "SUPER_ADMIN" ||
    effectiveRole === "AGENCY_MANAGER" ||
    effectiveRole === "BRANCH_MANAGER" ||
    effectiveRole === "SALES_MANAGER" ||
    hasPermission("virtual_tour.approve") ||
    hasPermission("virtual_tour.publish");

  const createTourMut = useMutation({
    mutationFn: async () =>
      apiFetch<VirtualTourDetail>(`/api/v1/properties/${params.id}/virtual-tour`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ create_default_floor: true }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("تور مجازی جدید با طبقه پایه ایجاد شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createFloorMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/virtual-tours/${tour!.id}/floors`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          title: newFloorTitle.trim(),
          elevation_m: Number(newFloorElev) || 0,
        }),
      }),
    onSuccess: () => {
      setNewFloorTitle("");
      setErrMsg(null);
      setNotice("طبقه جدید به تور اضافه شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteFloorMut = useMutation({
    mutationFn: async (floorId: string) =>
      apiFetch(`/api/v1/floors/${floorId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("طبقه حذف شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createSceneMut = useMutation({
    mutationFn: async () =>
      apiFetch<{ id: string }>(`/api/v1/virtual-tours/${tour!.id}/scenes`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          floor_id: newSceneFloorId || tour!.floors[0]?.id,
          title: newSceneTitle.trim(),
          room_type: newSceneRoomType,
        }),
      }),
    onSuccess: (res) => {
      setNewSceneTitle("");
      setSelectedSceneId(res.data.id);
      setErrMsg(null);
      setNotice("اتاق/صحنه جدید ایجاد شد. اکنون می‌توانید عکاسی ۳۶۰ درجه آن را آغاز کنید.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const setStartSceneMut = useMutation({
    mutationFn: async (sceneId: string) =>
      apiFetch(`/api/v1/scenes/${sceneId}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ is_start_scene: true }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("نقطه شروع تور به‌روزرسانی شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteSceneMut = useMutation({
    mutationFn: async (sceneId: string) =>
      apiFetch(`/api/v1/scenes/${sceneId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("صحنه حذف شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const approvePanoMut = useMutation({
    mutationFn: async ({ sceneId, versionId }: { sceneId: string; versionId?: string }) =>
      apiFetch(`/api/v1/scenes/${sceneId}/approve-panorama`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ panorama_version_id: versionId || null }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("نسخه پانوراما تأیید نهایی شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const rejectPanoMut = useMutation({
    mutationFn: async ({ sceneId, versionId }: { sceneId: string; versionId?: string }) =>
      apiFetch(`/api/v1/scenes/${sceneId}/reject-panorama`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          panorama_version_id: versionId || null,
          reason: rejectReason.trim() || "کیفیت تصویر نیاز به عکاسی مجدد دارد",
        }),
      }),
    onSuccess: () => {
      setRejectReason("");
      setErrMsg(null);
      setNotice("نسخه پانوراما رد شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const restorePanoMut = useMutation({
    mutationFn: async ({ sceneId, versionId }: { sceneId: string; versionId: string }) =>
      apiFetch(`/api/v1/scenes/${sceneId}/panoramas/${versionId}/restore`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("نسخه انتخاب‌شده به‌عنوان پانورامای فعال بازیابی شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createLinkMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/virtual-tours/${tour!.id}/links`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          source_scene_id: selectedScene!.id,
          target_scene_id: linkTargetSceneId,
          yaw: linkYaw,
          pitch: linkPitch,
          title: linkTitle.trim(),
          bidirectional: linkBidirectional,
        }),
      }),
    onSuccess: () => {
      setLinkTitle("");
      setPickTarget("none");
      setErrMsg(null);
      setNotice("نقطه جابجایی بین صحنه‌ها ثبت شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteLinkMut = useMutation({
    mutationFn: async (linkId: string) =>
      apiFetch(`/api/v1/links/${linkId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createHotspotMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/scenes/${selectedScene!.id}/hotspots`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          kind: hsKind,
          title: hsTitle.trim(),
          body: hsBody.trim(),
          yaw: hsYaw,
          pitch: hsPitch,
        }),
      }),
    onSuccess: () => {
      setHsTitle("");
      setHsBody("");
      setPickTarget("none");
      setErrMsg(null);
      setNotice("نقطه اطلاعاتی (Hotspot) ثبت شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteHotspotMut = useMutation({
    mutationFn: async (hsId: string) =>
      apiFetch(`/api/v1/hotspots/${hsId}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const publishMut = useMutation({
    mutationFn: async (unpublish: boolean) =>
      apiFetch(`/api/v1/virtual-tours/${tour!.id}/${unpublish ? "unpublish" : "publish"}`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: (_, unpublish) => {
      setErrMsg(null);
      setNotice(unpublish ? "انتشار عمومی تور متوقف شد." : "تور مجازی با موفقیت منتشر شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const archiveMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/virtual-tours/${tour!.id}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("تور آرشیو شد. می‌توانید یک تور جدید راه‌اندازی کنید.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const retryJobMut = useMutation({
    mutationFn: async (jobId: string) =>
      apiFetch(`/api/v1/processing-jobs/${jobId}/retry`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setNotice("اجرای مجدد پردازش آغاز شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const approveModelMut = useMutation({
    mutationFn: async (modelId: string) =>
      apiFetch(`/api/v1/models/${modelId}/approve`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("مدل سه‌بعدی Dollhouse تأیید نهایی شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const restoreModelMut = useMutation({
    mutationFn: async (modelId: string) =>
      apiFetch(`/api/v1/models/${modelId}/restore`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("نسخه انتخاب‌شده مدل سه‌بعدی بازیابی شد.");
      refreshTour();
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

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
      panorama_url: sc.current_panorama?.panorama_url || null,
      thumbnail_url: sc.thumbnail_url,
      links: (sc.outgoing_links || []).map((l) => ({
        id: l.id,
        target_scene_id: l.target_scene_id,
        target_scene_title: l.target_scene_title,
        yaw: l.yaw,
        pitch: l.pitch,
        title: l.title,
      })),
      hotspots: (sc.hotspots || []).map((h) => ({
        id: h.id,
        kind: h.kind,
        title: h.title,
        body: h.body,
        yaw: h.yaw,
        pitch: h.pitch,
        target_scene_id: h.target_scene_id,
      })),
    }));
  }, [tour]);

  const activeJobsList = liveJobs ?? tour?.recent_jobs ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={tour ? tour.title : "استودیوی تور مجازی ۳۶۰ درجه و مدل سه‌بعدی"}
        subtitle={
          tour
            ? `کد ملک: ${tour.property_code} · ${tour.property_title}`
            : "راه‌اندازی، عکاسی هدایت‌شده موبایل، بازبینی ۳۶۰° و انتشار تور مجازی ملک"
        }
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "فهرست املاک", href: "/dashboard/properties" },
          { label: tour?.property_code || "جزئیات ملک", href: `/dashboard/properties/${params.id}` },
          { label: "تور مجازی ۳۶۰°" },
        ]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {tour && <StatusText status={tour.status} />}
            <Link
              href={`/dashboard/properties/${params.id}`}
              className="inline-flex h-9 items-center rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              بازگشت به فایل ملک
            </Link>
            {tour?.status === "published" && tour.property_status === "PUBLISHED" && (
              <Link
                href={`/properties/${params.id}#virtual-tour`}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                نمای عمومی پورتال
              </Link>
            )}
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {vtQuery.isLoading ? (
        <LoadingState />
      ) : vtQuery.error instanceof Error ? (
        <ErrorState message={vtQuery.error.message} onRetry={() => vtQuery.refetch()} />
      ) : !tour ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-900 space-y-4">
          <Compass className="mx-auto h-10 w-10 text-teal-700 dark:text-teal-400" />
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
            هنوز تور مجازی برای این ملک ایجاد نشده است
          </h2>
          <p className="mx-auto max-w-lg text-xs leading-relaxed text-slate-600 dark:text-slate-400">
            با ایجاد تور مجازی می‌توانید طبقات و اتاق‌ها را تعریف کنید، با دوربین گوشی هوشمند ۱۲ نمای افقی بگیرید یا فایل ۳۶۰ درجه آماده آپلود کنید و تور تعاملی را روی پورتال منتشر نمایید.
          </p>
          <button
            type="button"
            disabled={createTourMut.isPending}
            onClick={() => createTourMut.mutate()}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-teal-700 px-5 text-xs font-bold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            {createTourMut.isPending ? "در حال ایجاد..." : "راه‌اندازی تور مجازی ۳۶۰ درجه"}
          </button>
        </div>
      ) : (
        <>
          {/* Tab Strip */}
          <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-200 bg-white p-1.5 dark:border-slate-800 dark:bg-slate-900">
            {(
              [
                { id: "overview", label: "چک‌لیست کیفیت و انتشار", icon: CheckCircle2 },
                { id: "capture", label: "طبقات، اتاق‌ها و عکاسی موبایل", icon: Camera },
                { id: "editor", label: "ویرایشگر ۳۶۰°، نقاط اتصال و بازبینی", icon: Compass },
                { id: "floorplan", label: "پلان دو‌بعدی و کالیبراسیون", icon: Map },
                { id: "dollhouse", label: "مدل سه‌بعدی Dollhouse", icon: Box },
                { id: "jobs", label: `صف پردازش (${formatNumberFa(activeJobsList.length)})`, icon: Cpu },
                { id: "analytics", label: "آمار بازدید", icon: BarChart3 },
              ] as const
            ).map((t) => {
              const Icon = t.icon;
              const active = tab === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTab(t.id)}
                  className={`inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg px-3.5 text-xs font-semibold transition-colors ${
                    active
                      ? "bg-teal-700 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {t.label}
                </button>
              );
            })}
          </div>

          {/* TAB 1: Overview, Quality Report & Publication */}
          {tab === "overview" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <div className="space-y-4 lg:col-span-8">
                <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
                    <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      گزارش کنترل کیفیت پیش از انتشار (Quality Gate)
                    </h2>
                    <button
                      type="button"
                      onClick={() => qualityQ.refetch()}
                      className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 px-2.5 text-xs text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      بروزرسانی بررسی
                    </button>
                  </div>

                  {qualityQ.isLoading ? (
                    <LoadingState />
                  ) : qualityQ.data ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                          <div className="text-[11px] text-slate-500">تعداد اتاق‌ها</div>
                          <div className="mt-1 text-lg font-bold tabular-nums">
                            {formatNumberFa(qualityQ.data.report_data.scenes_count ?? 0)}
                          </div>
                        </div>
                        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                          <div className="text-[11px] text-slate-500">پانورامای تأییدشده</div>
                          <div className="mt-1 text-lg font-bold tabular-nums text-teal-700 dark:text-teal-400">
                            {formatNumberFa(qualityQ.data.report_data.approved_panoramas_count ?? 0)}
                          </div>
                        </div>
                        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                          <div className="text-[11px] text-slate-500">خطاهای مسدودکننده</div>
                          <div className="mt-1 text-lg font-bold tabular-nums text-rose-600">
                            {formatNumberFa(qualityQ.data.blocking_issues_count)}
                          </div>
                        </div>
                        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                          <div className="text-[11px] text-slate-500">نقاط جابجایی</div>
                          <div className="mt-1 text-lg font-bold tabular-nums">
                            {formatNumberFa(qualityQ.data.report_data.links_count ?? 0)}
                          </div>
                        </div>
                      </div>

                      {(qualityQ.data.report_data.blocking_issues || []).length > 0 && (
                        <div className="space-y-2 rounded-xl border border-rose-200 bg-rose-50/70 p-4 text-xs text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
                          <div className="font-bold">موارد الزامی پیش از انتشار:</div>
                          {qualityQ.data.report_data.blocking_issues!.map((iss, i) => (
                            <div key={i} className="space-y-0.5">
                              <div className="font-semibold">• {iss.message}</div>
                              {iss.fix && <div className="pr-3 opacity-85">راه‌حل: {iss.fix}</div>}
                            </div>
                          ))}
                        </div>
                      )}

                      {(qualityQ.data.report_data.warnings || []).length > 0 && (
                        <div className="space-y-1.5 rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                          <div className="flex items-center gap-1.5 font-bold">
                            <AlertTriangle className="h-4 w-4" />
                            توصیه‌های بهبود تجربه کاربری:
                          </div>
                          {qualityQ.data.report_data.warnings!.map((w, i) => (
                            <div key={i}>• {w.message}</div>
                          ))}
                        </div>
                      )}

                      {qualityQ.data.is_ready_to_publish && (
                        <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-xs font-semibold text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200">
                          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                          تمام پیش‌نیازهای P0 تکمیل شده است و تور آماده انتشار عمومی است.
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="space-y-4 lg:col-span-4">
                <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    وضعیت انتشار عمومی تور
                  </h3>
                  <div className="space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
                    <div className="flex justify-between">
                      <span>وضعیت ملک:</span>
                      <StatusText status={tour.property_status} />
                    </div>
                    <div className="flex justify-between">
                      <span>دسترسی پورتال ملک:</span>
                      <span>{tour.property_visibility === "PUBLIC_PORTAL" ? "عمومی" : "داخلی آژانس"}</span>
                    </div>
                    {tour.active_publication && (
                      <div className="flex justify-between">
                        <span>نسخه منتشرشده فعال:</span>
                        <span className="font-mono font-bold">v{tour.active_publication.version}</span>
                      </div>
                    )}
                  </div>

                  {tour.property_status !== "PUBLISHED" || tour.property_visibility !== "PUBLIC_PORTAL" ? (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-[11px] text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
                      نکته امنیتی: حتی پس از انتشار تور، تا زمانی که خود ملک در پورتال عمومی منتشر نشده باشد، تور به صورت عمومی نمایش داده نمی‌شود.
                    </div>
                  ) : null}

                  {canApproveOrPublish && (
                    <div className="flex flex-col gap-2 pt-2">
                      {tour.status === "published" ? (
                        <button
                          type="button"
                          disabled={publishMut.isPending}
                          onClick={() => publishMut.mutate(true)}
                          className="h-9 w-full rounded-lg border border-amber-400 bg-amber-50 text-xs font-bold text-amber-900 hover:bg-amber-100"
                        >
                          توقف انتشار عمومی تور
                        </button>
                      ) : (
                        <button
                          type="button"
                          disabled={publishMut.isPending || !(qualityQ.data?.is_ready_to_publish)}
                          onClick={() => publishMut.mutate(false)}
                          className="inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-lg bg-teal-700 text-xs font-bold text-white hover:bg-teal-800 disabled:opacity-50"
                        >
                          <Send className="h-3.5 w-3.5" />
                          انتشار تور مجازی روی پورتال
                        </button>
                      )}

                      <button
                        type="button"
                        disabled={archiveMut.isPending}
                        onClick={() => archiveMut.mutate()}
                        className="inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg border border-rose-300 text-xs font-semibold text-rose-700 hover:bg-rose-50 dark:border-rose-900 dark:text-rose-400"
                      >
                        <Archive className="h-3.5 w-3.5" />
                        آرشیوکردن این تور
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Floors, Scenes & Guided Mobile Capture */}
          {tab === "capture" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <div className="space-y-4 lg:col-span-4">
                {/* Floors manager */}
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                  <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
                    <Layers className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                    طبقات ({formatNumberFa(tour.floors.length)})
                  </h3>
                  <div className="space-y-1.5">
                    {tour.floors.map((fl) => (
                      <div
                        key={fl.id}
                        className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-800"
                      >
                        <div>
                          <span className="font-semibold">{fl.title}</span>
                          <span className="mr-2 tabular-nums text-[11px] text-slate-500">
                            تراز {fl.elevation_m}m
                          </span>
                        </div>
                        {tour.floors.length > 1 && (
                          <button
                            type="button"
                            onClick={() => deleteFloorMut.mutate(fl.id)}
                            className="text-rose-600 hover:text-rose-800"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (newFloorTitle.trim()) createFloorMut.mutate();
                    }}
                    className="flex gap-1.5 pt-1"
                  >
                    <input
                      value={newFloorTitle}
                      onChange={(e) => setNewFloorTitle(e.target.value)}
                      placeholder="نام طبقه (مثلاً طبقه اول)"
                      className="h-8 flex-1 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                    />
                    <input
                      type="number"
                      step="0.1"
                      value={newFloorElev}
                      onChange={(e) => setNewFloorElev(e.target.value)}
                      className="h-8 w-16 rounded-lg border border-slate-300 px-2 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
                      title="ارتفاع تراز (متر)"
                    />
                    <button
                      type="submit"
                      disabled={createFloorMut.isPending}
                      className="h-8 rounded-lg bg-slate-900 px-2.5 text-xs font-semibold text-white dark:bg-teal-700"
                    >
                      افزودن
                    </button>
                  </form>
                </div>

                {/* Scenes manager */}
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    اتاق‌ها و صحنه‌ها ({formatNumberFa(tour.scenes.length)})
                  </h3>
                  <div className="space-y-1.5">
                    {tour.scenes.map((sc) => {
                      const active = selectedScene?.id === sc.id;
                      return (
                        <div
                          key={sc.id}
                          onClick={() => setSelectedSceneId(sc.id)}
                          className={`cursor-pointer rounded-lg border p-2.5 text-xs transition-colors ${
                            active
                              ? "border-teal-600 bg-teal-50/60 dark:border-teal-500 dark:bg-teal-950/30"
                              : "border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-bold text-slate-900 dark:text-slate-100">
                              {sc.title}
                              {sc.is_start_scene ? " (نقطه شروع)" : ""}
                            </span>
                            {sc.current_panorama ? (
                              <StatusText status={sc.current_panorama.state} />
                            ) : (
                              <span className="text-[11px] text-slate-400">بدون پانوراما</span>
                            )}
                          </div>
                          <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                            <span>{sc.floor_title}</span>
                            <div className="flex items-center gap-2">
                              {!sc.is_start_scene && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setStartSceneMut.mutate(sc.id);
                                  }}
                                  className="text-teal-700 hover:underline dark:text-teal-400"
                                >
                                  تنظیم به‌عنوان شروع
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  deleteSceneMut.mutate(sc.id);
                                }}
                                className="text-rose-600 hover:text-rose-800"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (newSceneTitle.trim()) createSceneMut.mutate();
                    }}
                    className="space-y-2 border-t border-slate-100 pt-3 dark:border-slate-800"
                  >
                    <input
                      value={newSceneTitle}
                      onChange={(e) => setNewSceneTitle(e.target.value)}
                      placeholder="نام اتاق یا فضا (مثلاً سالن پذیرایی)"
                      className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                    />
                    <div className="grid grid-cols-2 gap-1.5">
                      <select
                        value={newSceneFloorId}
                        onChange={(e) => setNewSceneFloorId(e.target.value)}
                        className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                      >
                        {tour.floors.map((fl) => (
                          <option key={fl.id} value={fl.id}>
                            {fl.title}
                          </option>
                        ))}
                      </select>
                      <select
                        value={newSceneRoomType}
                        onChange={(e) => setNewSceneRoomType(e.target.value)}
                        className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                      >
                        {(configBundle?.room_types?.length ? configBundle.room_types : DEFAULT_VIRTUAL_TOUR_ROOM_TYPES).map((rt) => (
                          <option key={rt.code} value={rt.code}>
                            {roomTypeLabel(rt)}
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      type="submit"
                      disabled={createSceneMut.isPending}
                      className="inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      افزودن اتاق به تور
                    </button>
                  </form>
                </div>
              </div>

              <div className="lg:col-span-8">
                {selectedScene ? (
                  <GuidedMobileCapture scene={selectedScene} onUpdated={refreshTour} />
                ) : (
                  <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-xs text-slate-500">
                    ابتدا از پنل سمت راست یک اتاق/صحنه ایجاد یا انتخاب کنید تا ابزار عکاسی ۳۶۰ درجه آن باز شود.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: 360° Editor, Links, Hotspots & Panorama Review/Rollback */}
          {tab === "editor" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <div className="space-y-4 lg:col-span-8">
                {selectedScene && (
                  <PanoramaViewer
                    scenes={viewerScenes}
                    floors={tour.floors}
                    activeSceneId={selectedScene.id}
                    onSceneChange={(id) => setSelectedSceneId(id)}
                    pickMode={pickTarget !== "none"}
                    onPickPosition={(yaw, pitch) => {
                      if (pickTarget === "link") {
                        setLinkYaw(yaw);
                        setLinkPitch(pitch);
                      } else if (pickTarget === "hotspot") {
                        setHsYaw(yaw);
                        setHsPitch(pitch);
                      }
                      setPickTarget("none");
                      setNotice(`مختصات (${yaw}° / ${pitch}°) با کلیک روی صحنه انتخاب شد.`);
                    }}
                  />
                )}

                {/* Panorama Versions & Review */}
                {selectedScene && (
                  <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                        تاریخچه نسخه‌های پانوراما: {selectedScene.title}
                      </h3>
                    </div>

                    {(selectedScene.panoramas || []).length === 0 ? (
                      <p className="text-xs text-slate-500">
                        هنوز پانورامایی برای این صحنه پردازش نشده است.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {(selectedScene.panoramas || []).map((pv) => (
                          <div
                            key={pv.id}
                            className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 text-xs ${
                              pv.is_current
                                ? "border-teal-500 bg-teal-50/40 dark:bg-teal-950/20"
                                : "border-slate-200 dark:border-slate-800"
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              {pv.thumbnail_url && (
                                <img
                                  src={pv.thumbnail_url}
                                  alt={`v${pv.version}`}
                                  className="h-12 w-20 rounded object-cover"
                                />
                              )}
                              <div>
                                <div className="flex items-center gap-2 font-bold">
                                  <span>نسخه {formatNumberFa(pv.version)}</span>
                                  {pv.is_current && (
                                    <span className="text-teal-700 dark:text-teal-400">· فعال</span>
                                  )}
                                  <StatusText status={pv.state} />
                                </div>
                                <div className="mt-0.5 tabular-nums text-[11px] text-slate-500">
                                  {pv.width_px}×{pv.height_px}px · {translateStatus(pv.engine)} ·{" "}
                                  {formatNumberFa(pv.source_image_count)} تصویر
                                </div>
                                {pv.rejection_reason && (
                                  <div className="mt-0.5 text-[11px] text-rose-600">
                                    دلیل رد: {pv.rejection_reason}
                                  </div>
                                )}
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-1.5">
                              {canApproveOrPublish && pv.state !== "approved" && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    approvePanoMut.mutate({ sceneId: selectedScene.id, versionId: pv.id })
                                  }
                                  className="inline-flex h-8 items-center gap-1 rounded-lg bg-emerald-700 px-2.5 text-[11px] font-semibold text-white hover:bg-emerald-800"
                                >
                                  <Check className="h-3.5 w-3.5" />
                                  تأیید
                                </button>
                              )}
                              {canApproveOrPublish && pv.state === "review" && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    rejectPanoMut.mutate({ sceneId: selectedScene.id, versionId: pv.id })
                                  }
                                  className="inline-flex h-8 items-center gap-1 rounded-lg border border-rose-300 px-2.5 text-[11px] font-semibold text-rose-700 hover:bg-rose-50"
                                >
                                  <XCircle className="h-3.5 w-3.5" />
                                  رد
                                </button>
                              )}
                              {!pv.is_current && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    restorePanoMut.mutate({ sceneId: selectedScene.id, versionId: pv.id })
                                  }
                                  className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 px-2.5 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200"
                                >
                                  <RotateCcw className="h-3.5 w-3.5" />
                                  بازگردانی
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                        {canApproveOrPublish && (
                          <input
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            placeholder="در صورت رد پانوراما، دلیل بازبینی مجدد را اینجا بنویسید (اختیاری)..."
                            className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                          />
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Right: Links & Hotspots Placement Controls */}
              <div className="space-y-4 lg:col-span-4">
                {selectedScene && (
                  <>
                    {/* Scene Links */}
                    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
                          <Navigation className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                          نقاط حرکت بین اتاق‌ها
                        </h3>
                        <button
                          type="button"
                          onClick={() => setPickTarget((p) => (p === "link" ? "none" : "link"))}
                          className={`rounded-md px-2 py-1 text-[11px] font-semibold ${
                            pickTarget === "link"
                              ? "bg-amber-500 text-white"
                              : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                          }`}
                        >
                          {pickTarget === "link" ? "در حال انتخاب روی ۳۶۰°..." : "انتخاب نقطه با کلیک"}
                        </button>
                      </div>

                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          if (linkTargetSceneId) createLinkMut.mutate();
                        }}
                        className="space-y-2 text-xs"
                      >
                        <select
                          required
                          value={linkTargetSceneId}
                          onChange={(e) => setLinkTargetSceneId(e.target.value)}
                          className="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                        >
                          <option value="">انتخاب اتاق مقصد...</option>
                          {tour.scenes
                            .filter((s) => s.id !== selectedScene.id)
                            .map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.title} ({s.floor_title})
                              </option>
                            ))}
                        </select>
                        <input
                          value={linkTitle}
                          onChange={(e) => setLinkTitle(e.target.value)}
                          placeholder="عنوان دکمه (مثلاً ورود به آشپزخانه)"
                          className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                        />
                        <div className="grid grid-cols-2 gap-1.5">
                          <input
                            type="number"
                            step="0.5"
                            value={linkYaw}
                            onChange={(e) => setLinkYaw(Number(e.target.value))}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
                            placeholder="Yaw"
                          />
                          <input
                            type="number"
                            step="0.5"
                            value={linkPitch}
                            onChange={(e) => setLinkPitch(Number(e.target.value))}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
                            placeholder="Pitch"
                          />
                        </div>
                        <label className="flex items-center gap-2 text-[11px]">
                          <input
                            type="checkbox"
                            checked={linkBidirectional}
                            onChange={(e) => setLinkBidirectional(e.target.checked)}
                            className="h-3.5 w-3.5 accent-teal-700"
                          />
                          ایجاد مسیر برگشت دوطرفه خودکار
                        </label>
                        <button
                          type="submit"
                          disabled={createLinkMut.isPending || !linkTargetSceneId}
                          className="h-8 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
                        >
                          ثبت لینک انتقال
                        </button>
                      </form>

                      {(selectedScene.outgoing_links || []).length > 0 && (
                        <div className="space-y-1 border-t border-slate-100 pt-2 text-[11px] dark:border-slate-800">
                          {selectedScene.outgoing_links!.map((l) => (
                            <div key={l.id} className="flex items-center justify-between py-1">
                              <span>
                                {l.title} → {l.target_scene_title} ({l.yaw}°/{l.pitch}°)
                              </span>
                              <button
                                type="button"
                                onClick={() => deleteLinkMut.mutate(l.id)}
                                className="text-rose-600"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Hotspots */}
                    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
                          <MapPin className="h-4 w-4 text-amber-600" />
                          نقاط اطلاعاتی (Hotspots)
                        </h3>
                        <button
                          type="button"
                          onClick={() => setPickTarget((p) => (p === "hotspot" ? "none" : "hotspot"))}
                          className={`rounded-md px-2 py-1 text-[11px] font-semibold ${
                            pickTarget === "hotspot"
                              ? "bg-amber-500 text-white"
                              : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                          }`}
                        >
                          {pickTarget === "hotspot" ? "در حال انتخاب روی ۳۶۰°..." : "انتخاب نقطه با کلیک"}
                        </button>
                      </div>

                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          if (hsTitle.trim()) createHotspotMut.mutate();
                        }}
                        className="space-y-2 text-xs"
                      >
                        <select
                          value={hsKind}
                          onChange={(e) => setHsKind(e.target.value as typeof hsKind)}
                          className="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                        >
                          <option value="info">توضیح معماری / متریال</option>
                          <option value="feature">امکانات ویژه</option>
                          <option value="measurement">ابعاد و اندازه‌گیری</option>
                        </select>
                        <input
                          required
                          value={hsTitle}
                          onChange={(e) => setHsTitle(e.target.value)}
                          placeholder="عنوان نقطه اطلاعاتی"
                          className="h-8 w-full rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                        />
                        <textarea
                          rows={2}
                          value={hsBody}
                          onChange={(e) => setHsBody(e.target.value)}
                          placeholder="توضیحات تکمیلی برای خریدار یا مستأجر..."
                          className="w-full rounded-lg border border-slate-300 p-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                        />
                        <div className="grid grid-cols-2 gap-1.5">
                          <input
                            type="number"
                            step="0.5"
                            value={hsYaw}
                            onChange={(e) => setHsYaw(Number(e.target.value))}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
                          />
                          <input
                            type="number"
                            step="0.5"
                            value={hsPitch}
                            onChange={(e) => setHsPitch(Number(e.target.value))}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
                          />
                        </div>
                        <button
                          type="submit"
                          disabled={createHotspotMut.isPending}
                          className="h-8 w-full rounded-lg bg-amber-600 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
                        >
                          افزودن نقطه اطلاعاتی
                        </button>
                      </form>

                      {(selectedScene.hotspots || []).length > 0 && (
                        <div className="space-y-1 border-t border-slate-100 pt-2 text-[11px] dark:border-slate-800">
                          {selectedScene.hotspots!.map((h) => (
                            <div key={h.id} className="flex items-center justify-between py-1">
                              <span>
                                {h.title} ({h.yaw}°/{h.pitch}°)
                              </span>
                              <button
                                type="button"
                                onClick={() => deleteHotspotMut.mutate(h.id)}
                                className="text-rose-600"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* TAB 4A: 2D Calibrated Floorplan Editor */}
          {tab === "floorplan" && (
            <FloorPlanEditor
              tourId={tour.id}
              floors={tour.floors}
              scenes={tour.scenes}
              roomTypes={configBundle?.room_types?.length ? configBundle.room_types : DEFAULT_VIRTUAL_TOUR_ROOM_TYPES}
              floorplans={tour.floorplans || []}
              rooms={tour.rooms || []}
              walls={tour.walls || []}
              onUpdated={refreshTour}
              onModelBuilt={() => setTab("dollhouse")}
            />
          )}

          {/* TAB 4B: 3D Dollhouse Viewer & Model Versions */}
          {tab === "dollhouse" && (
            <div className="space-y-4">
              <DollhouseViewer
                model={tour.current_model}
                floors={tour.floors}
                rooms={tour.rooms || []}
                onSelectScene={(sceneId) => {
                  setSelectedSceneId(sceneId);
                  setTab("editor");
                }}
              />

              {(tour.generated_models || []).length > 0 && (
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-2.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    تاریخچه نسخه‌های مدل سه‌بعدی (GLB)
                  </h3>
                  <div className="space-y-2">
                    {tour.generated_models!.map((gm) => (
                      <div
                        key={gm.id}
                        className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-xs ${
                          gm.is_current ? "border-teal-500 bg-teal-50/40 dark:bg-teal-950/20" : "border-slate-200 dark:border-slate-800"
                        }`}
                      >
                        <div>
                          <div className="flex items-center gap-2 font-bold">
                            <span>نسخه {formatNumberFa(gm.version)}</span>
                            <StatusText status={gm.state} />
                          </div>
                          <div className="mt-0.5 text-[11px] text-slate-500 tabular-nums">
                            {gm.estimated_accuracy} · متراژ: {formatNumberFa(gm.total_area_sqm)} م² · حجم:{" "}
                            {formatNumberFa(Math.round(gm.size_bytes / 1024))} KB
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {canApproveOrPublish && gm.state !== "approved" && gm.state !== "failed" && (
                            <button
                              type="button"
                              onClick={() => approveModelMut.mutate(gm.id)}
                              className="inline-flex h-8 items-center gap-1 rounded-lg bg-emerald-700 px-2.5 text-[11px] font-semibold text-white"
                            >
                              <Check className="h-3.5 w-3.5" />
                              تأیید مدل
                            </button>
                          )}
                          {!gm.is_current && gm.state !== "failed" && (
                            <button
                              type="button"
                              onClick={() => restoreModelMut.mutate(gm.id)}
                              className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 px-2.5 text-[11px] font-semibold dark:border-slate-700"
                            >
                              <RotateCcw className="h-3.5 w-3.5" />
                              بازگردانی
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: Processing Jobs */}
          {tab === "jobs" && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  وضعیت پردازش‌های پس‌زمینه (Celery / OpenCV)
                </h2>
                <button
                  type="button"
                  onClick={refreshTour}
                  className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  بروزرسانی
                </button>
              </div>
              {activeJobsList.length === 0 ? (
                <p className="text-xs text-slate-500">هنوز پردازشی برای این تور ثبت نشده است.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-right text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                        <th className="py-2 font-semibold">نوع عملیات</th>
                        <th className="py-2 font-semibold">اتاق</th>
                        <th className="py-2 font-semibold">وضعیت</th>
                        <th className="py-2 font-semibold">پیشرفت</th>
                        <th className="py-2 font-semibold">مرحله فعلی</th>
                        <th className="py-2 font-semibold">زمان ثبت</th>
                        <th className="py-2 font-semibold">اقدام</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {activeJobsList.map((j) => (
                        <tr key={j.id}>
                          <td className="py-2.5 font-medium">{j.job_type}</td>
                          <td className="py-2.5">{j.scene_title || "کل تور"}</td>
                          <td className="py-2.5">
                            <StatusText status={j.state} />
                          </td>
                          <td className="py-2.5 tabular-nums">{formatNumberFa(j.progress)}٪</td>
                          <td className="py-2.5 text-slate-600 dark:text-slate-400">
                            {j.error || j.current_step}
                          </td>
                          <td className="py-2.5 tabular-nums">
                            <DateDisplay value={j.created_at} />
                          </td>
                          <td className="py-2.5">
                            {j.state === "failed" && (
                              <button
                                type="button"
                                onClick={() => retryJobMut.mutate(j.id)}
                                className="rounded bg-teal-700 px-2 py-1 text-[11px] font-semibold text-white"
                              >
                                تلاش مجدد
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: Analytics */}
          {tab === "analytics" && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                گزارش بازدید و تعامل کاربران در تور مجازی
              </h2>
              {analyticsQ.isLoading ? (
                <LoadingState />
              ) : analyticsQ.data ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                      <div className="text-[11px] text-slate-500">بازدید کل تور</div>
                      <div className="mt-1 text-lg font-bold tabular-nums">
                        {formatNumberFa(analyticsQ.data.total_views)}
                      </div>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                      <div className="text-[11px] text-slate-500">بازدیدکننده یکتا</div>
                      <div className="mt-1 text-lg font-bold tabular-nums">
                        {formatNumberFa(analyticsQ.data.unique_visitors)}
                      </div>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                      <div className="text-[11px] text-slate-500">نرخ تکمیل تور</div>
                      <div className="mt-1 text-lg font-bold tabular-nums text-teal-700 dark:text-teal-400">
                        {formatNumberFa(analyticsQ.data.completion_rate_percent)}٪
                      </div>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                      <div className="text-[11px] text-slate-500">میانگین ماندگاری</div>
                      <div className="mt-1 text-lg font-bold tabular-nums">
                        {formatNumberFa(analyticsQ.data.avg_duration_seconds)} ثانیه
                      </div>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                      <div className="text-[11px] text-slate-500">کلیک روی نقاط تعاملی</div>
                      <div className="mt-1 text-lg font-bold tabular-nums">
                        {formatNumberFa(analyticsQ.data.hotspot_clicks)}
                      </div>
                    </div>
                  </div>

                  {analyticsQ.data.popular_scenes.length > 0 && (
                    <div className="space-y-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                      <h3 className="text-xs font-bold text-slate-700 dark:text-slate-300">
                        پربازدیدترین فضاها
                      </h3>
                      <div className="space-y-1.5 text-xs">
                        {analyticsQ.data.popular_scenes.map((ps) => (
                          <div key={ps.scene_id} className="flex justify-between">
                            <span>{ps.title}</span>
                            <span className="font-bold tabular-nums">{formatNumberFa(ps.visits)} بازدید</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </>
      )}
    </div>
  );
}
