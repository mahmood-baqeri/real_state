"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import {
  Box,
  Compass,
  Download,
  Eye,
  Layers,
  RotateCcw,
} from "lucide-react";
import { formatNumberFa } from "@/lib/formatters";
import type { GeneratedModelAssetItem, RoomGeometryItem, TourFloorItem } from "@/lib/types";

interface DollhouseViewerProps {
  model: GeneratedModelAssetItem | null | undefined;
  floors: TourFloorItem[];
  rooms?: RoomGeometryItem[];
  onSelectScene?: (sceneId: string) => void;
  heightClass?: string;
}

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

export function DollhouseViewer({
  model,
  floors,
  rooms = [],
  onSelectScene,
  heightClass = "h-[460px] md:h-[540px]",
}: DollhouseViewerProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const rootGroupRef = useRef<THREE.Group | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const needsRenderRef = useRef<boolean>(true);
  const hoveredRoomIdRef = useRef<string | null>(null);

  const [selectedFloorOrder, setSelectedFloorOrder] = useState<number | "all">("all");
  const [wallOpacity, setWallOpacity] = useState<number>(0.85);
  const [showRoomOverlay, setShowRoomOverlay] = useState<boolean>(true);
  const [selectedRoom, setSelectedRoom] = useState<RoomGeometryItem | null>(null);
  const [loadStatus, setLoadStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [contextLost, setContextLost] = useState(false);

  const roomsById = useMemo(() => {
    const m = new Map<string, RoomGeometryItem>();
    for (const r of rooms) m.set(r.id, r);
    return m;
  }, [rooms]);

  const applyFloorAndOpacity = useCallback(
    (group: THREE.Group, floorFilter: number | "all", opacityVal: number) => {
      group.traverse((obj) => {
        const mesh = obj as THREE.Mesh;
        const name = obj.name || "";

        const floorMatch = name.match(/__floor__(\d+)/);
        if (floorMatch) {
          const orderNum = Number(floorMatch[1]);
          obj.visible = floorFilter === "all" || orderNum <= floorFilter;
        }

        if (mesh.isMesh && (name.startsWith("wall__") || name.startsWith("autowall__"))) {
          const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          for (const mat of mats) {
            if (!mat) continue;
            const stdMat = mat as THREE.MeshStandardMaterial;
            stdMat.transparent = opacityVal < 0.99;
            stdMat.opacity = opacityVal;
            stdMat.depthWrite = opacityVal >= 0.99;
            stdMat.needsUpdate = true;
          }
        }
      });
      needsRenderRef.current = true;
    },
    []
  );

  useEffect(() => {
    const container = mountRef.current;
    if (!container || !model?.file_url) return;

    const isSoftwareGl = detectSoftwareWebGL();
    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 320);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#0f172a");

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 250);
    camera.position.set(14, 12, 16);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      antialias: !isSoftwareGl,
      powerPreference: isSoftwareGl ? "low-power" : "high-performance",
      alpha: false,
    });
    renderer.setPixelRatio(isSoftwareGl ? 1 : Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.domElement.style.display = "block";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // Lighting with RoomEnvironment PMREM
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = envTex;

    const hemi = new THREE.HemisphereLight(0xf1f5f9, 0x334155, 0.75);
    scene.add(hemi);
    const keyLight = new THREE.DirectionalLight(0xfffbeb, 1.35);
    keyLight.position.set(18, 28, 14);
    scene.add(keyLight);

    const grid = new THREE.GridHelper(36, 36, 0x334155, 0x1e293b);
    grid.position.y = -0.25;
    scene.add(grid);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 4;
    controls.maxDistance = 60;
    controls.maxPolarAngle = Math.PI * 0.48;
    controlsRef.current = controls;
    controls.addEventListener("change", () => {
      needsRenderRef.current = true;
    });

    const onLost = (e: Event) => {
      e.preventDefault();
      setContextLost(true);
    };
    const onRestored = () => {
      setContextLost(false);
      needsRenderRef.current = true;
    };
    renderer.domElement.addEventListener("webglcontextlost", onLost);
    renderer.domElement.addEventListener("webglcontextrestored", onRestored);

    const loader = new GLTFLoader();
    let disposed = false;
    setLoadStatus("loading");

    loader.load(
      model.file_url,
      (gltf) => {
        if (disposed) return;
        const root = new THREE.Group();
        root.add(gltf.scene);
        rootGroupRef.current = root;
        scene.add(root);

        // Fit camera cleanly to bounding box
        const box = new THREE.Box3().setFromObject(root);
        const size = new THREE.Vector3();
        const center = new THREE.Vector3();
        box.getSize(size);
        box.getCenter(center);
        const maxDim = Math.max(size.x, size.y, size.z, 6);
        camera.position.set(center.x + maxDim * 0.95, center.y + maxDim * 0.85, center.z + maxDim * 1.05);
        controls.target.copy(center);
        controls.update();

        applyFloorAndOpacity(root, selectedFloorOrder, wallOpacity);
        setLoadStatus("ready");
        needsRenderRef.current = true;
      },
      undefined,
      () => {
        if (!disposed) setLoadStatus("error");
      }
    );

    // Raycast click to select room pad
    const raycaster = new THREE.Raycaster();
    const ndc = new THREE.Vector2();
    let pointerDownPos = { x: 0, y: 0 };

    const onPointerDown = (e: PointerEvent) => {
      pointerDownPos = { x: e.clientX, y: e.clientY };
    };
    const onPointerUp = (e: PointerEvent) => {
      if (Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y) > 6) return;
      if (!rootGroupRef.current) return;
      const rect = renderer.domElement.getBoundingClientRect();
      ndc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      ndc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(ndc, camera);
      const hits = raycaster.intersectObjects(rootGroupRef.current.children, true);
      for (const h of hits) {
        let cur: THREE.Object3D | null = h.object;
        while (cur) {
          const m = (cur.name || "").match(/^room__([^_]+)__/);
          if (m) {
            const roomObj = roomsById.get(m[1]);
            if (roomObj) {
              setSelectedRoom(roomObj);
              hoveredRoomIdRef.current = roomObj.id;
              return;
            }
          }
          cur = cur.parent;
        }
      }
    };
    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointerup", onPointerUp);

    const resizeObs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.max(entry.contentRect.width, 280);
        const h = Math.max(entry.contentRect.height, 280);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
        needsRenderRef.current = true;
      }
    });
    resizeObs.observe(container);

    let rafId = 0;
    let lastDraw = 0;
    const minInterval = isSoftwareGl ? 66 : 0;

    const tick = (ts: number) => {
      rafId = requestAnimationFrame(tick);
      if (controls.update()) {
        needsRenderRef.current = true;
      }
      if (!needsRenderRef.current) return;
      if (minInterval > 0 && ts - lastDraw < minInterval) return;
      lastDraw = ts;
      needsRenderRef.current = false;
      renderer.render(scene, camera);
    };
    rafId = requestAnimationFrame(tick);

    return () => {
      disposed = true;
      cancelAnimationFrame(rafId);
      resizeObs.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("webglcontextlost", onLost);
      renderer.domElement.removeEventListener("webglcontextrestored", onRestored);
      controls.dispose();
      scene.traverse((obj) => {
        const m = obj as THREE.Mesh;
        if (m.geometry) m.geometry.dispose();
        if (m.material) {
          const mats = Array.isArray(m.material) ? m.material : [m.material];
          mats.forEach((mt) => mt.dispose());
        }
      });
      envTex.dispose();
      pmrem.dispose();
      renderer.dispose();
      rootGroupRef.current = null;
    };
  }, [model?.id, model?.file_url]);

  useEffect(() => {
    if (rootGroupRef.current) {
      applyFloorAndOpacity(rootGroupRef.current, selectedFloorOrder, wallOpacity);
    }
  }, [selectedFloorOrder, wallOpacity, applyFloorAndOpacity]);

  const resetCamera = () => {
    if (!rootGroupRef.current || !cameraRef.current || !controlsRef.current) return;
    const box = new THREE.Box3().setFromObject(rootGroupRef.current);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);
    const maxDim = Math.max(size.x, size.y, size.z, 6);
    cameraRef.current.position.set(center.x + maxDim * 0.95, center.y + maxDim * 0.85, center.z + maxDim * 1.05);
    controlsRef.current.target.copy(center);
    controlsRef.current.update();
    needsRenderRef.current = true;
  };

  if (!model) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center dark:border-slate-700 dark:bg-slate-900">
        <Box className="h-9 w-9 text-slate-400" />
        <p className="mt-3 text-xs font-semibold text-slate-700 dark:text-slate-300">
          هنوز مدل سه‌بعدی Dollhouse برای این تور تولید نشده است.
        </p>
        <p className="mt-1 text-[11px] text-slate-500">
          ابتدا در تب «پلان دو‌بعدی و کالیبراسیون»، پلان را بارگذاری و اتاق‌ها را رسم کنید، سپس دکمه ساخت مدل سه‌بعدی را بزنید.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className={`relative w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950 ${heightClass}`}>
        <div ref={mountRef} className="h-full w-full" />

        {loadStatus === "loading" && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-950/80 text-xs font-semibold text-slate-200">
            در حال بارگذاری فایل سه‌بعدی Dollhouse (GLB)...
          </div>
        )}

        {(loadStatus === "error" || contextLost) && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/90 p-6 text-center text-xs text-rose-300">
            {contextLost
              ? "حافظه گرافیکی مرورگر (WebGL) موقتاً متوقف شد؛ در حال تلاش برای بازیابی..."
              : "امکان بارگذاری فایل سه‌بعدی وجود نداشت."}
          </div>
        )}

        {/* Top-Right Compact Controls (no backdrop-filter over WebGL) */}
        <div className="absolute top-3 right-3 flex flex-wrap items-center gap-2 rounded-lg border border-slate-700 bg-slate-950/90 px-3 py-1.5 text-[11px] text-slate-200">
          <span className="flex items-center gap-1 font-semibold text-teal-400">
            <Box className="h-3.5 w-3.5" />
            نسخه {formatNumberFa(model.version)} (GLB)
          </span>
          <span className="text-slate-500">|</span>
          <span>متراژ کل: {formatNumberFa(model.total_area_sqm)} م²</span>
          <span className="text-slate-500 hidden sm:inline">|</span>
          <span className="hidden sm:inline text-slate-300">{model.estimated_accuracy}</span>
        </div>

        {/* Bottom HUD Bar */}
        <div className="absolute bottom-3 left-3 right-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-700 bg-slate-950/90 px-3 py-2 text-xs text-slate-100">
          <div className="flex flex-wrap items-center gap-3">
            {floors.length > 0 && (
              <label className="flex items-center gap-1.5 text-[11px]">
                <Layers className="h-3.5 w-3.5 text-teal-400" />
                <span>نمایش طبقه:</span>
                <select
                  value={selectedFloorOrder === "all" ? "all" : String(selectedFloorOrder)}
                  onChange={(e) =>
                    setSelectedFloorOrder(e.target.value === "all" ? "all" : Number(e.target.value))
                  }
                  className="h-7 rounded border border-slate-700 bg-slate-900 px-2 text-[11px] text-slate-100"
                >
                  <option value="all">کل ساختمان</option>
                  {floors.map((fl) => (
                    <option key={fl.id} value={fl.order}>
                      {fl.title}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <label className="flex items-center gap-2 text-[11px]">
              <span>شفافیت دیوارها:</span>
              <input
                type="range"
                min={0.2}
                max={1.0}
                step={0.05}
                value={wallOpacity}
                onChange={(e) => setWallOpacity(Number(e.target.value))}
                className="w-24 accent-teal-500"
              />
              <span className="tabular-nums text-slate-300">{Math.round(wallOpacity * 100)}%</span>
            </label>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowRoomOverlay((v) => !v)}
              className="inline-flex h-7 items-center gap-1 rounded border border-slate-700 bg-slate-900 px-2.5 text-[11px] hover:bg-slate-800"
            >
              <Eye className="h-3.5 w-3.5" />
              فهرست اتاق‌ها ({formatNumberFa(rooms.length)})
            </button>
            <button
              type="button"
              onClick={resetCamera}
              className="inline-flex h-7 items-center gap-1 rounded border border-slate-700 bg-slate-900 px-2.5 text-[11px] hover:bg-slate-800"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              نمای پیش‌فرض
            </button>
            <a
              href={model.file_url}
              download={`dollhouse-v${model.version}.glb`}
              className="inline-flex h-7 items-center gap-1 rounded bg-teal-700 px-2.5 text-[11px] font-semibold text-white hover:bg-teal-600"
            >
              <Download className="h-3.5 w-3.5" />
              دانلود GLB
            </a>
          </div>
        </div>
      </div>

      {/* Selected Room Action Banner (Jump directly into 360° Scene) */}
      {selectedRoom && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-500/40 bg-teal-50/70 p-3 text-xs dark:bg-teal-950/30">
          <div>
            <span className="font-bold text-slate-900 dark:text-slate-100">{selectedRoom.label}</span>
            <span className="mx-2 text-slate-400">·</span>
            <span className="tabular-nums text-slate-700 dark:text-slate-300">
              مساحت: {formatNumberFa(selectedRoom.area_sqm)} م² · محیط: {formatNumberFa(selectedRoom.perimeter_m)} متر
            </span>
          </div>
          {selectedRoom.scene_id && onSelectScene ? (
            <button
              type="button"
              onClick={() => onSelectScene(selectedRoom.scene_id!)}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-teal-700 px-3 text-xs font-bold text-white hover:bg-teal-800"
            >
              <Compass className="h-3.5 w-3.5" />
              ورود به نمای ۳۶۰° این اتاق
            </button>
          ) : (
            <span className="text-[11px] text-slate-500">این اتاق هنوز به صحنه ۳۶۰° متصل نشده است.</span>
          )}
        </div>
      )}

      {/* Compact Room Area Breakdown Bar */}
      {showRoomOverlay && rooms.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
          {rooms.map((rm) => (
            <div
              key={rm.id}
              onClick={() => setSelectedRoom(rm)}
              className={`cursor-pointer rounded-lg border p-2.5 text-xs transition-colors ${
                selectedRoom?.id === rm.id
                  ? "border-teal-600 bg-teal-50/50 dark:bg-teal-950/30"
                  : "border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-bold text-slate-900 dark:text-slate-100">{rm.label}</span>
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{ backgroundColor: rm.color_hex || "#0F766E" }}
                />
              </div>
              <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500 tabular-nums">
                <span>{formatNumberFa(rm.area_sqm)} م²</span>
                {rm.scene_id && onSelectScene && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectScene(rm.scene_id!);
                    }}
                    className="font-semibold text-teal-700 hover:underline dark:text-teal-400"
                  >
                    بازدید ۳۶۰°
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
