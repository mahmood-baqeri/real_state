"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import {
  ChevronDown,
  ChevronUp,
  Compass,
  Expand,
  Info,
  Minimize2,
  Navigation,
  Pause,
  Play,
  RotateCcw,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

export interface PanoramaViewerLink {
  id: string;
  target_scene_id: string;
  target_scene_title: string;
  yaw: number;
  pitch: number;
  title: string;
}

export interface PanoramaViewerHotspot {
  id: string;
  kind: string;
  title: string;
  body: string;
  yaw: number;
  pitch: number;
  target_scene_id: string | null;
}

export interface PanoramaViewerScene {
  id: string;
  floor_id: string;
  floor_title: string;
  title: string;
  room_type?: string;
  initial_yaw: number;
  initial_pitch: number;
  panorama_url: string | null;
  thumbnail_url?: string | null;
  links?: PanoramaViewerLink[];
  hotspots?: PanoramaViewerHotspot[];
}

export interface PanoramaViewerFloor {
  id: string;
  title: string;
  order: number;
}

interface ProjectedMarker {
  key: string;
  type: "link" | "hotspot";
  x: number;
  y: number;
  visible: boolean;
  title: string;
  link?: PanoramaViewerLink;
  hotspot?: PanoramaViewerHotspot;
}

interface PanoramaViewerProps {
  scenes: PanoramaViewerScene[];
  floors?: PanoramaViewerFloor[];
  activeSceneId: string;
  onSceneChange: (sceneId: string) => void;
  onHotspotClick?: (hotspot: PanoramaViewerHotspot) => void;
  pickMode?: boolean;
  onPickPosition?: (yaw: number, pitch: number) => void;
  heightClass?: string;
  className?: string;
}

const _tmpVec = new THREE.Vector3();
const _targetVec = new THREE.Vector3();
const _raycaster = new THREE.Raycaster();
const _ndc = new THREE.Vector2();

function detectSoftwareWebGL(): boolean {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    if (!gl) return true;
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    const param = ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER;
    const gpu = String(gl.getParameter(param) || "");
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return /SwiftShader|llvmpipe|softpipe|Software|Basic Render/i.test(gpu);
  } catch {
    return false;
  }
}

function yawPitchToDirection(yawDeg: number, pitchDeg: number, radius = 420): THREE.Vector3 {
  const phi = THREE.MathUtils.degToRad(90 - pitchDeg);
  const theta = THREE.MathUtils.degToRad(yawDeg);
  return new THREE.Vector3(
    radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

function directionToYawPitch(point: THREE.Vector3): { yaw: number; pitch: number } {
  const n = point.clone().normalize();
  const pitch = THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(n.y, -0.99, 0.99)));
  const yaw = THREE.MathUtils.radToDeg(Math.atan2(n.z, n.x));
  return {
    yaw: Math.round(yaw * 10) / 10,
    pitch: Math.round(pitch * 10) / 10,
  };
}

export function PanoramaViewer({
  scenes,
  floors = [],
  activeSceneId,
  onSceneChange,
  onHotspotClick,
  pickMode = false,
  onPickPosition,
  heightClass = "h-[460px] lg:h-[540px]",
  className = "",
}: PanoramaViewerProps) {
  const outerRef = useRef<HTMLDivElement | null>(null);
  const mountRef = useRef<HTMLDivElement | null>(null);

  const activeScene = useMemo(
    () => scenes.find((s) => s.id === activeSceneId) || scenes[0] || null,
    [scenes, activeSceneId]
  );

  const [selectedFloorId, setSelectedFloorId] = useState<string>("");
  const [dockCollapsed, setDockCollapsed] = useState(false);
  const [autoRotate, setAutoRotate] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [webglError, setWebglError] = useState<string | null>(null);
  const [textureLoading, setTextureLoading] = useState(false);
  const [panoramaFormatWarning, setPanoramaFormatWarning] = useState<string | null>(null);
  const [selectedHotspot, setSelectedHotspot] = useState<PanoramaViewerHotspot | null>(null);
  const [markers, setMarkers] = useState<ProjectedMarker[]>([]);
  const [fovDisplay, setFovDisplay] = useState(72);

  // Refs synced into the Three.js render loop without recreating the WebGL context
  const activeSceneRef = useRef<PanoramaViewerScene | null>(activeScene);
  const autoRotateRef = useRef(autoRotate);
  const pickModeRef = useRef(pickMode);
  const onPickPositionRef = useRef(onPickPosition);

  activeSceneRef.current = activeScene;
  autoRotateRef.current = autoRotate;
  pickModeRef.current = pickMode;
  onPickPositionRef.current = onPickPosition;

  const camStateRef = useRef({
    yaw: activeScene?.initial_yaw ?? 0,
    pitch: activeScene?.initial_pitch ?? 0,
    targetYaw: activeScene?.initial_yaw ?? 0,
    targetPitch: activeScene?.initial_pitch ?? 0,
    fov: 72,
    targetFov: 72,
    isDragging: false,
    pointerDownX: 0,
    pointerDownY: 0,
    lastX: 0,
    lastY: 0,
    movedDist: 0,
  });

  const threeRef = useRef<{
    renderer: THREE.WebGLRenderer | null;
    scene: THREE.Scene | null;
    camera: THREE.PerspectiveCamera | null;
    mesh: THREE.Mesh | null;
    material: THREE.MeshBasicMaterial | null;
    currentTexture: THREE.Texture | null;
    requestRender: () => void;
  }>({
    renderer: null,
    scene: null,
    camera: null,
    mesh: null,
    material: null,
    currentTexture: null,
    requestRender: () => {},
  });

  useEffect(() => {
    if (activeScene) {
      setSelectedFloorId(activeScene.floor_id);
      setSelectedHotspot(null);
      camStateRef.current.targetYaw = activeScene.initial_yaw || 0;
      camStateRef.current.targetPitch = THREE.MathUtils.clamp(activeScene.initial_pitch || 0, -80, 80);
      threeRef.current.requestRender();
    }
  }, [activeScene?.id]);

  // Initialize WebGLRenderer & inverted sphere once
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const isSoftwareGl = detectSoftwareWebGL();
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: !isSoftwareGl,
        powerPreference: "high-performance",
      });
    } catch {
      setWebglError("مرورگر شما از WebGL برای نمایش ۳۶۰ درجه پشتیبانی نمی‌کند.");
      return;
    }

    const width = Math.max(300, container.clientWidth);
    const height = Math.max(260, container.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.setPixelRatio(isSoftwareGl ? 1 : Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    renderer.domElement.style.display = "block";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.touchAction = "none";

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);
    const camera = new THREE.PerspectiveCamera(72, width / height, 1, 1100);
    camera.position.set(0, 0, 0);

    const geometry = new THREE.SphereGeometry(500, isSoftwareGl ? 40 : 64, isSoftwareGl ? 24 : 32);
    geometry.scale(-1, 1, 1);
    const material = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const sphereMesh = new THREE.Mesh(geometry, material);
    scene.add(sphereMesh);

    const handleContextLost = (e: Event) => {
      e.preventDefault();
      setWebglError("ارتباط گرافیکی WebGL موقتاً قطع شد. در حال بازیابی...");
    };
    const handleContextRestored = () => {
      setWebglError(null);
      requestRender();
    };
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost);
    renderer.domElement.addEventListener("webglcontextrestored", handleContextRestored);

    let disposed = false;
    let frameId = 0;
    let renderBusy = false;
    let renderDirty = false;
    let lastTime = performance.now();

    const projectMarkers = () => {
      const sc = activeSceneRef.current;
      if (!sc) {
        setMarkers([]);
        return;
      }
      const w = renderer.domElement.clientWidth || container.clientWidth;
      const h = renderer.domElement.clientHeight || container.clientHeight;
      const next: ProjectedMarker[] = [];

      for (const lnk of sc.links || []) {
        const pos = yawPitchToDirection(lnk.yaw, lnk.pitch, 400);
        _tmpVec.copy(pos).project(camera);
        const visible = _tmpVec.z < 1 && Math.abs(_tmpVec.x) <= 1.05 && Math.abs(_tmpVec.y) <= 1.05;
        next.push({
          key: `lnk-${lnk.id}`,
          type: "link",
          x: ((_tmpVec.x + 1) / 2) * w,
          y: ((-_tmpVec.y + 1) / 2) * h,
          visible,
          title: lnk.title || lnk.target_scene_title,
          link: lnk,
        });
      }

      for (const hs of sc.hotspots || []) {
        const pos = yawPitchToDirection(hs.yaw, hs.pitch, 400);
        _tmpVec.copy(pos).project(camera);
        const visible = _tmpVec.z < 1 && Math.abs(_tmpVec.x) <= 1.05 && Math.abs(_tmpVec.y) <= 1.05;
        next.push({
          key: `hs-${hs.id}`,
          type: "hotspot",
          x: ((_tmpVec.x + 1) / 2) * w,
          y: ((-_tmpVec.y + 1) / 2) * h,
          visible,
          title: hs.title,
          hotspot: hs,
        });
      }
      setMarkers(next);
    };

    const afterDraw = (cb: () => void) => {
      const gl = renderer.getContext() as WebGL2RenderingContext;
      if (!gl || typeof gl.fenceSync !== "function") {
        frameId = window.setTimeout(cb, 80);
        return;
      }
      const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
      gl.flush();
      const poll = () => {
        if (disposed) return;
        const status = sync ? gl.getSyncParameter(sync, gl.SYNC_STATUS) : gl.SIGNALED;
        if (status === gl.UNSIGNALED) {
          frameId = window.setTimeout(poll, 5);
        } else {
          if (sync) gl.deleteSync(sync);
          frameId = window.setTimeout(cb, 80);
        }
      };
      frameId = window.setTimeout(poll, 5);
    };

    function requestRender() {
      if (disposed) return;
      if (renderBusy) {
        renderDirty = true;
        return;
      }
      renderBusy = true;
      frameId = requestAnimationFrame((now) => {
        if (disposed) return;
        renderDirty = false;
        const dt = Math.min(0.1, Math.max(0.001, (now - lastTime) / 1000));
        lastTime = now;

        const st = camStateRef.current;
        if (autoRotateRef.current && !st.isDragging) {
          st.targetYaw += dt * 11;
        }
        if (isSoftwareGl) {
          st.yaw = st.targetYaw;
          st.pitch = st.targetPitch;
          st.fov = st.targetFov;
        } else {
          st.yaw = THREE.MathUtils.damp(st.yaw, st.targetYaw, 10, dt);
          st.pitch = THREE.MathUtils.damp(st.pitch, st.targetPitch, 10, dt);
          st.fov = THREE.MathUtils.damp(st.fov, st.targetFov, 10, dt);
        }

        if (Math.abs(camera.fov - st.fov) > 0.05) {
          camera.fov = st.fov;
          camera.updateProjectionMatrix();
        }

        const dir = yawPitchToDirection(st.yaw, st.pitch, 100);
        _targetVec.copy(dir);
        camera.lookAt(_targetVec);
        renderer.render(scene, camera);
        projectMarkers();

        const needsMore =
          autoRotateRef.current ||
          Math.abs(st.yaw - st.targetYaw) > 0.04 ||
          Math.abs(st.pitch - st.targetPitch) > 0.04 ||
          Math.abs(st.fov - st.targetFov) > 0.04;

        const done = () => {
          renderBusy = false;
          if (!disposed && (renderDirty || needsMore)) {
            requestRender();
          }
        };
        if (isSoftwareGl) {
          afterDraw(done);
        } else {
          done();
        }
      });
    }

    threeRef.current = {
      renderer,
      scene,
      camera,
      mesh: sphereMesh,
      material,
      currentTexture: threeRef.current.currentTexture,
      requestRender,
    };

    const canvas = renderer.domElement;

    const onPointerDown = (e: PointerEvent) => {
      canvas.setPointerCapture(e.pointerId);
      const st = camStateRef.current;
      st.isDragging = true;
      st.pointerDownX = e.clientX;
      st.pointerDownY = e.clientY;
      st.lastX = e.clientX;
      st.lastY = e.clientY;
      st.movedDist = 0;
    };

    const onPointerMove = (e: PointerEvent) => {
      const st = camStateRef.current;
      if (!st.isDragging) return;
      const dx = e.clientX - st.lastX;
      const dy = e.clientY - st.lastY;
      st.movedDist += Math.hypot(dx, dy);
      st.lastX = e.clientX;
      st.lastY = e.clientY;
      const sensitivity = (st.fov / 75) * 0.16;
      st.targetYaw -= dx * sensitivity;
      st.targetPitch = THREE.MathUtils.clamp(st.targetPitch + dy * sensitivity, -82, 82);
      requestRender();
    };

    const onPointerUp = (e: PointerEvent) => {
      const st = camStateRef.current;
      const moved = st.movedDist;
      st.isDragging = false;
      try {
        canvas.releasePointerCapture(e.pointerId);
      } catch {
        // ignore if already released
      }

      if (moved < 6 && pickModeRef.current && onPickPositionRef.current) {
        const rect = canvas.getBoundingClientRect();
        _ndc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        _ndc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        _raycaster.setFromCamera(_ndc, camera);
        const hits = _raycaster.intersectObject(sphereMesh, false);
        if (hits.length > 0) {
          const { yaw, pitch } = directionToYawPitch(hits[0].point);
          onPickPositionRef.current(yaw, pitch);
        }
      }
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const st = camStateRef.current;
      st.targetFov = THREE.MathUtils.clamp(st.targetFov + e.deltaY * 0.04, 35, 95);
      setFovDisplay(Math.round(st.targetFov));
      requestRender();
    };

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    const ro = new ResizeObserver(() => {
      if (disposed) return;
      const nw = Math.max(280, container.clientWidth);
      const nh = Math.max(240, container.clientHeight);
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
      requestRender();
    });
    ro.observe(container);

    requestRender();

    return () => {
      disposed = true;
      cancelAnimationFrame(frameId);
      clearTimeout(frameId);
      ro.disconnect();
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("wheel", onWheel);
      canvas.removeEventListener("webglcontextlost", handleContextLost);
      canvas.removeEventListener("webglcontextrestored", handleContextRestored);

      if (threeRef.current.currentTexture) {
        threeRef.current.currentTexture.dispose();
        threeRef.current.currentTexture = null;
      }
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      threeRef.current.renderer = null;
    };
  }, []);

  // Load equirectangular texture when activeScene.panorama_url changes
  useEffect(() => {
    const url = activeScene?.panorama_url;
    const mat = threeRef.current.material;
    setPanoramaFormatWarning(null);

    // Never leave the previous room's panorama visible while a new room is loading
    // or when the selected room has no approved panorama.
    if (mat) {
      mat.map = null;
      mat.needsUpdate = true;
      const previousTexture = threeRef.current.currentTexture;
      threeRef.current.currentTexture = null;
      previousTexture?.dispose();
      threeRef.current.requestRender();
    }
    if (!url || !mat) {
      setTextureLoading(false);
      return;
    }

    let cancelled = false;
    setTextureLoading(true);
    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(
      url,
      (tex) => {
        if (cancelled) {
          tex.dispose();
          return;
        }
        const image = tex.image as { width?: number; height?: number } | undefined;
        const imageAspect = (image?.width || 0) / Math.max(1, image?.height || 1);
        if (!image?.width || !image?.height || imageAspect < 1.95 || imageAspect > 2.05) {
          tex.dispose();
          setTextureLoading(false);
          setPanoramaFormatWarning(
            "ابعاد این تصویر با استاندارد پانورامای ۳۶۰ درجه (نسبت نزدیک به ۲:۱) سازگار نیست؛ نمایش آن روی کره باعث کشیدگی می‌شود. فایل صحیح ۳۶۰ درجه را دوباره بارگذاری کنید."
          );
          return;
        }
        setPanoramaFormatWarning(null);
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        if (threeRef.current.renderer) {
          tex.anisotropy = Math.min(4, threeRef.current.renderer.capabilities.getMaxAnisotropy());
        }
        const prev = threeRef.current.currentTexture;
        threeRef.current.currentTexture = tex;
        mat.map = tex;
        mat.needsUpdate = true;
        if (prev && prev !== tex) prev.dispose();
        setTextureLoading(false);
        threeRef.current.requestRender();
      },
      undefined,
      () => {
        if (!cancelled) {
          setTextureLoading(false);
          setPanoramaFormatWarning(
            "بارگذاری تصویر این فضا ناموفق بود. آدرس فایل، دسترسی ذخیره‌سازی و وضعیت پردازش پانوراما را بررسی کنید."
          );
        }
      }
    );

    return () => {
      cancelled = true;
    };
  }, [activeScene?.panorama_url]);

  // Kick render loop when autoRotate toggles
  useEffect(() => {
    threeRef.current.requestRender();
  }, [autoRotate]);

  useEffect(() => {
    const onFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
      threeRef.current.requestRender();
    };
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  const handleToggleFullscreen = useCallback(() => {
    const el = outerRef.current;
    if (!el) return;
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    } else {
      el.requestFullscreen().catch(() => {});
    }
  }, []);

  const handleZoom = (delta: number) => {
    const st = camStateRef.current;
    st.targetFov = THREE.MathUtils.clamp(st.targetFov + delta, 35, 95);
    setFovDisplay(Math.round(st.targetFov));
    threeRef.current.requestRender();
  };

  const handleResetView = () => {
    if (!activeScene) return;
    const st = camStateRef.current;
    st.targetYaw = activeScene.initial_yaw || 0;
    st.targetPitch = THREE.MathUtils.clamp(activeScene.initial_pitch || 0, -80, 80);
    st.targetFov = 72;
    setFovDisplay(72);
    threeRef.current.requestRender();
  };

  const activeSceneIndex = Math.max(0, scenes.findIndex((scene) => scene.id === activeSceneId));

  if (!activeScene) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-slate-100 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
        هنوز صحنه ۳۶۰ درجه‌ای برای نمایش ثبت نشده است.
      </div>
    );
  }

  return (
    <div
      ref={outerRef}
      className={`relative w-full overflow-hidden rounded-xl border border-slate-300 bg-slate-950 select-none dark:border-slate-800 ${
        isFullscreen ? "h-screen rounded-none" : heightClass
      } ${className}`}
    >
      {/* Isolated WebGL mount container */}
      <div
        ref={mountRef}
        className={`h-full w-full ${pickMode ? "cursor-crosshair" : "cursor-grab active:cursor-grabbing"}`}
      />

      {/* Fallback or loading scrim */}
      {(webglError || !activeScene.panorama_url) && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-slate-900 p-6 text-center text-white">
          {activeScene.thumbnail_url && (
            <img
              src={activeScene.thumbnail_url}
              alt={activeScene.title}
              className="max-h-56 rounded-lg border border-white/15 object-cover"
            />
          )}
          <p className="text-sm font-semibold">
            {webglError || "پانورامای این صحنه هنوز پردازش یا تأیید نشده است."}
          </p>
        </div>
      )}

      {textureLoading && activeScene.panorama_url && !webglError && (
        <div className="pointer-events-none absolute top-4 left-4 z-10 rounded-lg border border-slate-700 bg-slate-900/90 px-3 py-1.5 text-xs font-medium text-slate-100">
          در حال بارگذاری تصویر ۳۶۰ درجه...
        </div>
      )}

      {panoramaFormatWarning && (
        <div className="absolute inset-x-3 top-16 z-30 mx-auto max-w-2xl rounded-xl border border-amber-400/70 bg-amber-950/95 p-3 text-xs leading-6 text-amber-100 shadow-xl">
          <div className="font-bold">تصویر انتخاب‌شده پانورامای استاندارد نیست</div>
          <p>{panoramaFormatWarning}</p>
        </div>
      )}

      {/* Minimal Top Bar over Scene (No Backdrop Blur over WebGL) */}
      <div className="pointer-events-none absolute top-3 right-3 left-3 z-20 flex flex-wrap items-center justify-between gap-2">
        <div className="pointer-events-auto flex items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-950/90 px-3 py-1.5 text-xs text-slate-100">
          <Compass className="h-3.5 w-3.5 text-teal-400" />
          <span className="font-bold">{activeScene.title}</span>
          <span className="text-slate-400">·</span>
          <span className="text-slate-300">{activeScene.floor_title}</span>
          {pickMode && (
            <>
              <span className="text-slate-400">·</span>
              <span className="font-semibold text-amber-300">
                روی تصویر ۳۶۰ درجه کلیک کنید تا مختصات ثبت شود
              </span>
            </>
          )}
        </div>

        <div className="pointer-events-auto flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setAutoRotate((v) => !v)}
            title={autoRotate ? "توقف چرخش خودکار" : "چرخش آرام خودکار"}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-950/90 px-2.5 text-xs font-medium text-slate-100 hover:bg-slate-900"
          >
            {autoRotate ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{autoRotate ? "توقف" : "چرخش"}</span>
          </button>
          <button
            type="button"
            onClick={() => handleZoom(-10)}
            title="بزرگنمایی"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700/80 bg-slate-950/90 text-slate-100 hover:bg-slate-900"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => handleZoom(10)}
            title="کوچک‌نمایی"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700/80 bg-slate-950/90 text-slate-100 hover:bg-slate-900"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={handleResetView}
            title="بازگشت به زاویه پیش‌فرض"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700/80 bg-slate-950/90 text-slate-100 hover:bg-slate-900"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={handleToggleFullscreen}
            title={isFullscreen ? "خروج از تمام‌صفحه" : "تمام‌صفحه"}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700/80 bg-slate-950/90 text-slate-100 hover:bg-slate-900"
          >
            {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Expand className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Room navigation buttons replace the old thumbnail carousel as the primary navigation. */}
      {scenes.length > 1 && (
        <div className="absolute top-[3.65rem] right-3 left-3 z-20 max-h-28 overflow-y-auto rounded-xl border border-slate-700/80 bg-slate-950/90 p-2.5 shadow-xl">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <span className="text-[11px] font-bold text-slate-100">رفتن به فضای دیگر</span>
            <span className="text-[10px] text-slate-400">فضاهای دارای مسیر اتصال با نشان «مجاور» مشخص‌اند</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {scenes.filter((target) => target.id !== activeScene.id).map((target) => {
              const connectedLink = (activeScene.links || []).find((link) => link.target_scene_id === target.id);
              return (
                <button
                  key={target.id}
                  type="button"
                  onClick={() => onSceneChange(target.id)}
                  className={`inline-flex min-h-8 items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold transition ${
                    connectedLink
                      ? "border-teal-400/80 bg-teal-900/90 text-white hover:bg-teal-700"
                      : "border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400 hover:bg-slate-700"
                  }`}
                  title={connectedLink ? `مسیر متصل: ${connectedLink.title}` : `دسترسی مستقیم به ${target.title}؛ مسیر مجاور هنوز تعریف نشده است`}
                >
                  <Navigation className={`h-3.5 w-3.5 ${connectedLink ? "text-teal-300" : "text-slate-400"}`} />
                  <span>{target.title}</span>
                  {connectedLink && <span className="rounded bg-teal-500/20 px-1 text-[9px] text-teal-200">مجاور</span>}
                </button>
              );
            })}
          </div>
          {(!activeScene.links || activeScene.links.length === 0) && (
            <p className="mt-2 text-[10px] leading-5 text-amber-200">
              برای نمایش مسیرهای واقعی از داخل اتاق، در ویرایشگر ۳۶۰° نقاط اتصال را روی محل درگاه‌ها ثبت کنید. دکمه‌های بالا فعلاً دسترسی مستقیم به فضاها هستند.
            </p>
          )}
        </div>
      )}

      {/* Projected 3D Scene Links & Info Hotspots */}
      <div className="pointer-events-none absolute inset-0 z-10 overflow-hidden">
        {markers
          .filter((m) => m.visible)
          .map((m) =>
            m.type === "link" && m.link ? (
              <button
                key={m.key}
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSceneChange(m.link!.target_scene_id);
                }}
                style={{ transform: `translate(${m.x}px, ${m.y}px) translate(-50%, -50%)` }}
                className="pointer-events-auto absolute top-0 left-0 flex items-center gap-1.5 rounded-lg border border-teal-400/70 bg-slate-950/90 px-2.5 py-1.5 text-xs font-semibold text-white shadow-lg transition-transform hover:scale-105 hover:bg-teal-700"
              >
                <Navigation className="h-3.5 w-3.5 text-teal-300" />
                <span className="whitespace-nowrap">{m.title}</span>
              </button>
            ) : m.hotspot ? (
              <button
                key={m.key}
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedHotspot(m.hotspot!);
                  onHotspotClick?.(m.hotspot!);
                  if (m.hotspot!.target_scene_id) {
                    onSceneChange(m.hotspot!.target_scene_id);
                  }
                }}
                style={{ transform: `translate(${m.x}px, ${m.y}px) translate(-50%, -50%)` }}
                className="pointer-events-auto absolute top-0 left-0 flex items-center gap-1.5 rounded-lg border border-amber-400/70 bg-slate-950/90 px-2.5 py-1 text-xs font-semibold text-amber-100 shadow-lg hover:bg-amber-700"
              >
                <Info className="h-3.5 w-3.5 text-amber-300" />
                <span className="whitespace-nowrap">{m.title}</span>
              </button>
            ) : null
          )}
      </div>

      {/* Hotspot Detail Popover */}
      {selectedHotspot && (
        <div className="absolute top-14 right-3 z-30 w-72 rounded-xl border border-slate-700 bg-slate-950/95 p-3.5 text-xs text-slate-100 shadow-xl">
          <div className="flex items-start justify-between gap-2">
            <span className="font-bold text-amber-300">{selectedHotspot.title}</span>
            <button
              type="button"
              onClick={() => setSelectedHotspot(null)}
              className="rounded px-1.5 py-0.5 text-[11px] text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              بستن
            </button>
          </div>
          {selectedHotspot.body && (
            <p className="mt-1.5 leading-relaxed text-slate-300">{selectedHotspot.body}</p>
          )}
        </div>
      )}

      {/* Collapsible Unified Bottom Control Dock */}
      <div className="pointer-events-none absolute right-3 bottom-3 left-3 z-20 flex flex-col items-center">
        <button
          type="button"
          onClick={() => setDockCollapsed((v) => !v)}
          className="pointer-events-auto mb-1.5 inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-950/90 px-3 py-1 text-[11px] font-medium text-slate-200 hover:bg-slate-900"
        >
          {dockCollapsed ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          <span>{dockCollapsed ? "نمایش نوار فضاها" : "جمع‌کردن نوار"}</span>
          <span className="text-slate-500">·</span>
          <span className="tabular-nums text-slate-400">FOV {fovDisplay}°</span>
        </button>

        {!dockCollapsed && (
          <div className="pointer-events-auto flex w-full max-w-4xl flex-col gap-2 rounded-xl border border-slate-700/80 bg-slate-950/92 p-2.5 text-slate-100">
            <div className="flex flex-wrap items-center gap-2">
              <label htmlFor="panorama-scene-jump" className="shrink-0 text-[11px] font-semibold text-slate-300">
                رفتن مستقیم به فضا
              </label>
              <select
                id="panorama-scene-jump"
                value={activeScene.id}
                onChange={(event) => onSceneChange(event.target.value)}
                aria-label="انتخاب مستقیم فضای خانه"
                className="h-9 min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 text-xs font-semibold text-slate-100"
              >
                {scenes.map((scene) => (
                  <option key={scene.id} value={scene.id}>
                    {scene.floor_title} — {scene.title}
                  </option>
                ))}
              </select>
              <span className="shrink-0 text-[10px] tabular-nums text-slate-400">فضای {activeSceneIndex + 1} از {scenes.length}</span>
            </div>
            {floors.length > 1 && (
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                {floors.map((fl) => (
                  <button
                    key={fl.id}
                    type="button"
                    onClick={() => {
                      setSelectedFloorId(fl.id);
                      const firstInFloor = scenes.find((scene) => scene.floor_id === fl.id);
                      if (firstInFloor) onSceneChange(firstInFloor.id);
                    }}
                    className={`shrink-0 whitespace-nowrap rounded-md px-2.5 py-1.5 text-[11px] font-semibold transition-colors ${
                      selectedFloorId === fl.id
                        ? "bg-teal-600 text-white"
                        : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    {fl.title}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
