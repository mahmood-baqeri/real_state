"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Camera,
  CheckCircle2,
  Compass,
  Play,
  RotateCcw,
  SkipForward,
  Sparkles,
  Upload,
  VideoOff,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa, translateStatus } from "@/lib/formatters";
import type {
  CaptureGuideStepItem,
  CaptureImageItem,
  CaptureSessionItem,
  PanoramaVersionItem,
  ProcessingJobItem,
  TourSceneItem,
} from "@/lib/types";
import { StatusText } from "@/components/ui/StatusText";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

interface GuidedMobileCaptureProps {
  scene: TourSceneItem;
  onUpdated: () => void;
}

export function GuidedMobileCapture({ scene, onUpdated }: GuidedMobileCaptureProps) {
  const { accessToken, activeAgencyId } = useAuth();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [session, setSession] = useState<CaptureSessionItem | null>(null);
  const [selectedSeq, setSelectedSeq] = useState<number>(1);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [sensorYaw, setSensorYaw] = useState<number | null>(null);
  const [sensorPitch, setSensorPitch] = useState<number | null>(null);
  const [allowPartial, setAllowPartial] = useState(true);
  const [busy, setBusy] = useState(false);
  const [lastFeedback, setLastFeedback] = useState<CaptureImageItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  // Load latest capture session for the selected scene
  useEffect(() => {
    let cancelled = false;
    setSession(null);
    setLastFeedback(null);
    setErrMsg(null);
    setNotice(null);

    if (!accessToken || !scene.id) return;
    apiFetch<CaptureSessionItem[]>(`/api/v1/scenes/${scene.id}/capture-sessions`, {
      token: accessToken,
      agencyId: activeAgencyId,
    })
      .then((res) => {
        if (cancelled) return;
        const latest = res.data.find((s) => s.status !== "cancelled") || res.data[0] || null;
        setSession(latest);
        if (latest) {
          const nextPending = latest.steps.find((st) => st.state === "pending" || st.state === "needs_retake");
          setSelectedSeq(nextPending ? nextPending.sequence : 1);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [scene.id, accessToken, activeAgencyId]);

  // Listen to device orientation compass & tilt when enabled
  useEffect(() => {
    const onOrientation = (ev: DeviceOrientationEvent) => {
      if (typeof ev.alpha === "number") {
        setSensorYaw(Math.round((360 - ev.alpha) % 360));
      }
      if (typeof ev.beta === "number") {
        setSensorPitch(Math.round(Math.max(-85, Math.min(85, ev.beta - 90))));
      }
    };
    window.addEventListener("deviceorientation", onOrientation);
    return () => window.removeEventListener("deviceorientation", onOrientation);
  }, []);

  // Stop camera stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  const activeStep: CaptureGuideStepItem | null = useMemo(() => {
    if (!session) return null;
    return session.steps.find((s) => s.sequence === selectedSeq) || session.steps[0] || null;
  }, [session, selectedSeq]);

  const startCamera = async () => {
    setCameraError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("دسترسی مستقیم دوربین در این مرورگر فعال نیست؛ می‌توانید فایل تصاویر را مستقیم آپلود کنید.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraActive(true);
    } catch {
      setCameraError("امکان باز کردن دوربین وجود ندارد (مجوز یا سخت‌افزار دوربین در دسترس نیست). از بخش آپلود دستی استفاده کنید.");
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const refreshSession = async (sessionId: string) => {
    const res = await apiFetch<CaptureSessionItem>(`/api/v1/capture-sessions/${sessionId}`, {
      token: accessToken,
      agencyId: activeAgencyId,
    });
    setSession(res.data);
    const nextPending = res.data.steps.find((st) => st.state === "pending" || st.state === "needs_retake");
    if (nextPending) setSelectedSeq(nextPending.sequence);
    onUpdated();
  };

  const handleStartSession = async () => {
    setBusy(true);
    setErrMsg(null);
    setNotice(null);
    try {
      const res = await apiFetch<CaptureSessionItem>(`/api/v1/scenes/${scene.id}/capture-sessions`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          allow_partial_stitch: allowPartial,
          device_info: {
            platform: typeof navigator !== "undefined" ? navigator.platform : "web",
            userAgent: typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 120) : "",
          },
        }),
      });
      setSession(res.data);
      setSelectedSeq(1);
      setNotice("جلسه عکاسی هدایت‌شده آماده شد. طبق زاویه‌های قطب‌نما عکس‌ها را ثبت کنید.");
      onUpdated();
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : "خطا در ایجاد جلسه عکاسی");
    } finally {
      setBusy(false);
    }
  };

  const uploadSingleFrame = async (file: File | Blob, seq: number, yawVal: number, pitchVal: number, filename: string) => {
    if (!session) return;
    const form = new FormData();
    form.append("file", file, filename);
    form.append("sequence", String(seq));
    form.append("yaw", String(yawVal));
    form.append("pitch", String(pitchVal));

    const res = await apiFetch<{ image: CaptureImageItem; session_summary: CaptureSessionItem["summary"] }>(
      `/api/v1/capture-sessions/${session.id}/images`,
      {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: form,
      }
    );
    setLastFeedback(res.data.image);
    await refreshSession(session.id);
  };

  const handleCaptureFromCamera = async () => {
    if (!videoRef.current || !session || !activeStep) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    setBusy(true);
    setErrMsg(null);
    try {
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
      if (!blob) throw new Error("خطا در ثبت تصویر از دوربین");
      await uploadSingleFrame(
        blob,
        activeStep.sequence,
        sensorYaw ?? activeStep.yaw,
        sensorPitch ?? activeStep.pitch,
        `capture-seq-${activeStep.sequence}.jpg`
      );
      setNotice(`فریم مرحله ${formatNumberFa(activeStep.sequence)} ارسال و بررسی کیفیت شد.`);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : "خطا در ارسال فریم");
    } finally {
      setBusy(false);
    }
  };

  const handleBatchFilesUpload = async (files: FileList | null) => {
    if (!files || !files.length || !session) return;
    setBusy(true);
    setErrMsg(null);
    setNotice(null);
    try {
      const fileArr = Array.from(files);
      let cursor = selectedSeq;
      for (let i = 0; i < fileArr.length; i++) {
        const f = fileArr[i];
        const step = session.steps.find((s) => s.sequence === cursor) || session.steps[i];
        const seq = step ? step.sequence : i + 1;
        await uploadSingleFrame(
          f,
          seq,
          step ? step.yaw : seq * 30,
          step ? step.pitch : 0,
          f.name
        );
        cursor = seq + 1;
      }
      setNotice(`${formatNumberFa(fileArr.length)} تصویر بررسی کیفیت و در جلسه عکاسی ذخیره شد.`);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : "خطا در آپلود دسته‌ای تصاویر");
    } finally {
      setBusy(false);
    }
  };

  const handleSkipOptional = async (seq: number) => {
    if (!session) return;
    setBusy(true);
    setErrMsg(null);
    try {
      await apiFetch(`/api/v1/capture-sessions/${session.id}/steps/${seq}/skip`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      });
      await refreshSession(session.id);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : "خطا در ردکردن مرحله");
    } finally {
      setBusy(false);
    }
  };

  const handleStitchPanorama = async () => {
    if (!session) return;
    setBusy(true);
    setErrMsg(null);
    setNotice(null);
    try {
      await apiFetch(`/api/v1/capture-sessions/${session.id}/complete`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      });
      const res = await apiFetch<ProcessingJobItem>(`/api/v1/scenes/${scene.id}/process`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        headers: { "Idempotency-Key": `stitch-${scene.id}-${session.id}-${Date.now()}` },
        body: JSON.stringify({ session_id: session.id, reprocess: false }),
      });
      setNotice(
        res.data.state === "succeeded"
          ? "پانورامای ۳۶۰ درجه با موفقیت دوخته شد و آماده بازبینی است."
          : `پردازش در صف اجرا قرار گرفت (${translateStatus(res.data.state)}).`
      );
      await refreshSession(session.id);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : "خطا در اجرای پردازش پانوراما");
    } finally {
      setBusy(false);
    }
  };

  const handleDirectPanoramaUpload = async (file: File | null) => {
    if (!file) return;
    setBusy(true);
    setErrMsg(null);
    setNotice(null);
    try {
      const form = new FormData();
      form.append("file", file, file.name);
      const res = await apiFetch<PanoramaVersionItem>(`/api/v1/scenes/${scene.id}/panoramas/upload`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: form,
      });
      setNotice(`پانورامای مستقیم نسخه ${formatNumberFa(res.data.version)} ثبت شد.`);
      onUpdated();
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : "خطا در آپلود پانورامای آماده");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {/* Header & Direct 360 Upload Shortcut */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/50">
        <div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            عکاسی هدایت‌شده موبایل / آپلود تصویر ۳۶۰ درجه: {scene.title}
          </h3>
          <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">
            با ۱۲ گام افقی (هر ۳۰ درجه) + سقف/کف اختیاری، یا آپلود مستقیم فایل ۳۶۰ درجه Equirectangular.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
            <Upload className="h-3.5 w-3.5" />
            آپلود مستقیم فایل ۳۶۰° آماده
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={busy}
              onChange={(e) => handleDirectPanoramaUpload(e.target.files?.[0] || null)}
            />
          </label>
          <button
            type="button"
            disabled={busy}
            onClick={handleStartSession}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            {session ? "شروع جلسه عکاسی جدید" : "شروع عکاسی هدایت‌شده"}
          </button>
        </div>
      </div>

      {!session && (
        <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-600 dark:border-slate-700 dark:text-slate-400 space-y-3">
          <label className="inline-flex items-center gap-2 font-medium">
            <input
              type="checkbox"
              checked={allowPartial}
              onChange={(e) => setAllowPartial(e.target.checked)}
              className="h-4 w-4 accent-teal-700"
            />
            اجازه دوخت آزمایشی با حداقل ۲ فریم (مناسب برای فضاهای محدود یا تست سریع)
          </label>
          <div>برای ثبت گام‌به‌گام فریم‌ها با دوربین گوشی، روی «شروع عکاسی هدایت‌شده» کلیک کنید.</div>
        </div>
      )}

      {session && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          {/* Left: Camera + Active Target + QC Banner */}
          <div className="space-y-3 lg:col-span-7">
            <div className="rounded-xl border border-slate-200 bg-slate-950 p-3 text-slate-100 dark:border-slate-800">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <Compass className="h-4 w-4 text-teal-400" />
                  <span className="font-bold">{activeStep?.label || `گام ${selectedSeq}`}</span>
                  <span className="tabular-nums text-slate-400">
                    هدف: Yaw {activeStep?.yaw ?? 0}° · Pitch {activeStep?.pitch ?? 0}°
                  </span>
                </div>
                {sensorYaw !== null && (
                  <span className="tabular-nums text-teal-300">
                    قطب‌نما: {sensorYaw}° / شیب {sensorPitch ?? 0}°
                  </span>
                )}
              </div>

              <div className="relative aspect-[16/10] w-full overflow-hidden rounded-lg bg-slate-900">
                <video
                  ref={videoRef}
                  playsInline
                  muted
                  className={`h-full w-full object-cover ${cameraActive ? "block" : "hidden"}`}
                />
                {!cameraActive && (
                  <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-xs text-slate-400">
                    <VideoOff className="h-7 w-7 text-slate-500" />
                    <p>{activeStep?.guidance || "دوربین را روشن کنید یا تصویر این زاویه را از گالری انتخاب نمایید."}</p>
                    {cameraError && <p className="text-amber-400">{cameraError}</p>}
                  </div>
                )}
                {/* Center Crosshair */}
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <div className="h-12 w-12 rounded-full border-2 border-dashed border-teal-400/70" />
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {!cameraActive ? (
                    <button
                      type="button"
                      onClick={startCamera}
                      className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-slate-800 px-3 text-xs font-semibold text-white hover:bg-slate-700"
                    >
                      <Camera className="h-3.5 w-3.5" />
                      فعال‌سازی دوربین زنده
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={handleCaptureFromCamera}
                        className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-600 px-4 text-xs font-semibold text-white hover:bg-teal-500 disabled:opacity-50"
                      >
                        <Camera className="h-3.5 w-3.5" />
                        ثبت تصویر این زاویه
                      </button>
                      <button
                        type="button"
                        onClick={stopCamera}
                        className="h-9 rounded-lg border border-slate-700 px-2.5 text-xs text-slate-300 hover:bg-slate-800"
                      >
                        توقف دوربین
                      </button>
                    </>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <label className="inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 text-xs font-semibold text-slate-100 hover:bg-slate-800">
                    <Upload className="h-3.5 w-3.5" />
                    آپلود فریم (تکی یا دسته‌ای)
                    <input
                      type="file"
                      multiple
                      accept="image/jpeg,image/png,image/webp"
                      className="hidden"
                      disabled={busy}
                      onChange={(e) => handleBatchFilesUpload(e.target.files)}
                    />
                  </label>
                  {activeStep && !activeStep.required && activeStep.state === "pending" && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleSkipOptional(activeStep.sequence)}
                      className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-700 px-2.5 text-xs text-slate-300 hover:bg-slate-800"
                    >
                      <SkipForward className="h-3.5 w-3.5" />
                      ردکردن
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Live Server Quality Inspection Feedback */}
            {lastFeedback && (
              <div
                className={`rounded-xl border p-3.5 text-xs ${
                  lastFeedback.status === "rejected"
                    ? "border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"
                    : lastFeedback.status === "warning"
                    ? "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200"
                    : "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 font-bold">
                  <span>
                    نتیجه بررسی کیفیت گام {formatNumberFa(lastFeedback.sequence)}: {translateStatus(lastFeedback.status)}
                  </span>
                  <span className="tabular-nums font-normal">
                    وضوح: {lastFeedback.analysis.blur_score ?? "—"} · روشنایی: {lastFeedback.analysis.brightness ?? "—"} · ابعاد:{" "}
                    {lastFeedback.width}×{lastFeedback.height}
                  </span>
                </div>
                {(lastFeedback.analysis.issues || []).map((iss, idx) => (
                  <p key={idx} className="mt-1">
                    • {iss}
                  </p>
                ))}
                {(lastFeedback.analysis.warnings || []).map((w, idx) => (
                  <p key={idx} className="mt-1">
                    • {w}
                  </p>
                ))}
                {(lastFeedback.analysis.recommendations || []).length > 0 && (
                  <p className="mt-1 opacity-90">
                    پیشنهاد: {lastFeedback.analysis.recommendations![0]}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Right: 14-Step Guide Grid + Stitch Trigger */}
          <div className="space-y-3 lg:col-span-5">
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2 dark:border-slate-800">
                <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
                  پیشرفت گام‌های عکاسی ({formatNumberFa(session.summary.completion_percent)}٪)
                </div>
                <StatusText status={session.status} />
              </div>

              <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                {session.steps.map((st) => {
                  const isSel = st.sequence === selectedSeq;
                  const tone =
                    st.state === "passed" || st.state === "captured"
                      ? "border-emerald-300 bg-emerald-50/70 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200"
                      : st.state === "needs_retake"
                      ? "border-rose-300 bg-rose-50/70 text-rose-900 dark:border-rose-800 dark:bg-rose-950/30 dark:text-rose-200"
                      : st.state === "skipped"
                      ? "border-slate-200 bg-slate-100 text-slate-500 dark:border-slate-800 dark:bg-slate-800"
                      : "border-slate-200 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200";
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => setSelectedSeq(st.sequence)}
                      className={`rounded-lg border p-2 text-right text-[11px] transition-colors ${tone} ${
                        isSel ? "ring-2 ring-teal-600" : ""
                      }`}
                    >
                      <div className="flex items-center justify-between font-bold">
                        <span>#{formatNumberFa(st.sequence)}</span>
                        {(st.state === "passed" || st.state === "captured") && (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                        )}
                      </div>
                      <div className="mt-0.5 truncate">{st.label}</div>
                    </button>
                  );
                })}
              </div>

              <div className="space-y-1 border-t border-slate-100 pt-2.5 text-[11px] text-slate-600 dark:border-slate-800 dark:text-slate-400">
                <div className="flex justify-between tabular-nums">
                  <span>تصاویر قابل استفاده:</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">
                    {formatNumberFa(session.summary.usable_images_count)} از حداقل {formatNumberFa(session.summary.min_usable_required)}
                  </span>
                </div>
                {session.summary.angular_gaps.length > 0 && (
                  <p className="text-amber-700 dark:text-amber-400">
                    شکاف زاویه‌ای: {session.summary.angular_gaps[0]}
                  </p>
                )}
              </div>

              <button
                type="button"
                disabled={busy || !session.summary.ready_to_stitch}
                onClick={handleStitchPanorama}
                className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-teal-700 text-xs font-bold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                <Sparkles className="h-4 w-4" />
                {busy ? "در حال پردازش..." : "تکمیل و ساخت پانورامای ۳۶۰° (OpenCV)"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
