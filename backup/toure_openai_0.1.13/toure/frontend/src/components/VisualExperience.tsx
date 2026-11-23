"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { usePathname } from "next/navigation";

type VisualSettings = {
  enabled: boolean;
  particles: boolean;
  waves: boolean;
  grain: boolean;
  video: boolean;
  videoUrl: string;
  intensity: number;
};

const DEFAULT_SETTINGS: VisualSettings = {
  enabled: true,
  particles: true,
  waves: true,
  grain: true,
  video: false,
  videoUrl: "",
  intensity: 68,
};
const SETTINGS_KEY = "toure-visual-experience-settings";
const PROFILES = new Set(["aurora", "obsidian", "crystal", "holographic", "off"]);

function readSettings(): VisualSettings {
  try {
    const parsed = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") as Partial<VisualSettings>;
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      intensity: Math.max(0, Math.min(100, Number(parsed.intensity ?? DEFAULT_SETTINGS.intensity))),
      videoUrl: typeof parsed.videoUrl === "string" ? parsed.videoUrl : "",
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function ParticleField({ active, intensity }: { active: boolean; intensity: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !active) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    let width = 0, height = 0, frame = 0, last = 0;
    let visible = !document.hidden;
    const pointer = { x: -1000, y: -1000 };
    const points: { x: number; y: number; vx: number; vy: number; r: number; phase: number }[] = [];
    const count = Math.round((window.innerWidth < 700 ? 38 : 84) * (0.5 + intensity / 165));
    const resize = () => {
      width = window.innerWidth; height = window.innerHeight;
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
      canvas.style.width = `${width}px`; canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!points.length) for (let i = 0; i < count; i++) points.push({
        x: Math.random() * width, y: Math.random() * height,
        vx: (Math.random() - .5) * .34, vy: (Math.random() - .5) * .34,
        r: Math.random() * 1.7 + .65, phase: Math.random() * Math.PI * 2,
      });
    };
    const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent-primary").trim() || "#38bdf8";
    // Use a high-contrast neutral core plus palette accent so particles remain visible
    // over both light and dark surfaces (palette colors alone can blend into the UI).
    const color = accent;
    const onPointer = (event: PointerEvent) => { if (event.pointerType !== "touch") { pointer.x = event.clientX; pointer.y = event.clientY; } };
    const onLeave = () => { pointer.x = -1000; pointer.y = -1000; };
    const draw = (time: number) => {
      if (!visible) { frame = requestAnimationFrame(draw); return; }
      if (!reduced && time - last < 32) { frame = requestAnimationFrame(draw); return; }
      const dt = last ? Math.min(2, (time - last) / 16.67) : 1; last = time;
      ctx.clearRect(0, 0, width, height);
      const pointAlpha = Math.min(0.94, 0.72 + intensity / 420);
      points.forEach((p, i) => {
        if (!reduced) {
          p.x += p.vx * dt; p.y += p.vy * dt;
          if (p.x < -10 || p.x > width + 10) p.vx *= -1;
          if (p.y < -10 || p.y > height + 10) p.vy *= -1;
          // Smooth, bounded mouse repulsion with easing back into the particle's natural drift.
          const dx = p.x - pointer.x, dy = p.y - pointer.y, dist = Math.hypot(dx, dy);
          if (dist > 0 && dist < 145) {
            const force = (1 - dist / 145) * 0.65;
            p.x += (dx / dist) * force * dt; p.y += (dy / dist) * force * dt;
          }
        }
        const twinkle = reduced ? 1 : .82 + Math.sin(time * .0014 + p.phase) * .18;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r + 0.35, 0, Math.PI * 2);
        ctx.fillStyle = "#ffffff"; ctx.globalAlpha = Math.min(0.98, pointAlpha * twinkle);
        ctx.shadowColor = color; ctx.shadowBlur = 10 * twinkle; ctx.fill(); ctx.shadowBlur = 0;
        ctx.beginPath(); ctx.arc(p.x, p.y, Math.max(0.65, p.r * 0.62), 0, Math.PI * 2);
        ctx.fillStyle = color; ctx.globalAlpha = Math.min(0.92, pointAlpha * twinkle); ctx.fill();
        for (let j = i + 1; j < points.length; j++) {
          const q = points[j], dx = p.x - q.x, dy = p.y - q.y, distance = Math.hypot(dx, dy);
          if (distance < 168) {
            ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = color; ctx.globalAlpha = (1 - distance / 168) * (0.28 + intensity / 430);
            ctx.lineWidth = 1; ctx.stroke();
          }
        }
      });
      ctx.globalAlpha = 1;
      if (!reduced) frame = requestAnimationFrame(draw);
    };
    const onVisibility = () => { visible = !document.hidden; };
    resize();
    const observer = new ResizeObserver(resize); observer.observe(document.documentElement);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pointermove", onPointer, { passive: true });
    window.addEventListener("pointerleave", onLeave);
    frame = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(frame); observer.disconnect(); document.removeEventListener("visibilitychange", onVisibility); window.removeEventListener("pointermove", onPointer); window.removeEventListener("pointerleave", onLeave); };
  }, [active, intensity]);
  if (!active) return null;
  return <canvas ref={canvasRef} aria-hidden="true" className="toure-particle-canvas" />;
}

function WaveField({ active, intensity }: { active: boolean; intensity: number }) {
  if (!active) return null;
  return (
    <div className="toure-wave-field" aria-hidden="true" style={{ opacity: 0.18 + intensity / 250 }}>
      <svg viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path className="toure-wave toure-wave-one" d="M0,160 C180,230 360,70 540,145 C720,220 900,265 1080,170 C1260,75 1350,110 1440,145 L1440,320 L0,320Z" />
        <path className="toure-wave toure-wave-two" d="M0,205 C190,125 340,245 540,195 C740,145 850,90 1050,160 C1250,230 1350,205 1440,170 L1440,320 L0,320Z" />
        <path className="toure-wave toure-wave-three" d="M0,235 C170,180 350,285 560,225 C770,165 910,190 1090,220 C1270,250 1370,170 1440,210 L1440,320 L0,320Z" />
      </svg>
    </div>
  );
}

/** One presentation layer wraps every route, including public, auth, user and admin pages. */
export function VisualExperience({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const reduceMotion = useReducedMotion();
  const [settings, setSettings] = useState<VisualSettings>(DEFAULT_SETTINGS);
  const [profile, setProfile] = useState("aurora");
  const [ready, setReady] = useState(false);
  const visualOn = settings.enabled && profile !== "off";

  useEffect(() => {
    const apply = () => {
      const next = readSettings();
      setSettings(next);
      setReady(true);
      const root = document.documentElement;
      let profile = "aurora";
      try { const saved = localStorage.getItem("toure-visual-effects") || "aurora"; profile = PROFILES.has(saved) ? saved : "aurora"; } catch { /* ignore */ }
      setProfile(profile);
      root.dataset.visualEffects = next.enabled ? profile : "off";
      root.dataset.fxParticles = String(next.enabled && next.particles);
      root.dataset.fxWaves = String(next.enabled && next.waves);
      root.dataset.fxGrain = String(next.enabled && next.grain);
      root.dataset.fxVideo = String(next.enabled && next.video && !!next.videoUrl);
      root.style.setProperty("--fx-intensity", String(next.intensity / 100));
    };
    apply();
    window.addEventListener("toure:visual-settings", apply);
    window.addEventListener("storage", apply);
    return () => { window.removeEventListener("toure:visual-settings", apply); window.removeEventListener("storage", apply); };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType === "touch" || !visualOn) return;
      root.style.setProperty("--fx-pointer-x", `${event.clientX}px`);
      root.style.setProperty("--fx-pointer-y", `${event.clientY}px`);
    };
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    if (reduceMotion) root.dataset.motionPreference = "reduced";
    else root.dataset.motionPreference = "full";
    if (reduceMotion || !visualOn) {
      return () => { window.removeEventListener("pointermove", onPointerMove); delete root.dataset.motionPreference; };
    }
    const selector = "main section, main article, main [data-visual-surface='card'], main .surface-card, [role='dialog']";
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.setAttribute("data-fx-visible", "true"); observer.unobserve(entry.target); }
    }), { threshold: 0.06, rootMargin: "0px 0px -28px 0px" });
    const seen = new WeakSet<Element>();
    const scan = (scope: ParentNode) => scope.querySelectorAll(selector).forEach((element) => {
      if (seen.has(element)) return; seen.add(element); element.setAttribute("data-fx-reveal", "true"); observer.observe(element);
    });
    scan(document);
    const mutations = new MutationObserver((records) => records.forEach((record) => record.addedNodes.forEach((node) => { if (node instanceof HTMLElement) scan(node); })));
    mutations.observe(document.body, { childList: true, subtree: true });
    return () => { window.removeEventListener("pointermove", onPointerMove); observer.disconnect(); mutations.disconnect(); delete root.dataset.motionPreference; };
  }, [pathname, reduceMotion, visualOn]);

  const videoUrl = useMemo(() => {
    const value = settings.videoUrl.trim();
    return /^https?:\/\//i.test(value) ? value : "";
  }, [settings.videoUrl]);

  return (
    <div className="toure-visual-root" data-visual-ready={ready ? "true" : "false"}>
      {visualOn && <div className="toure-atmosphere" aria-hidden="true" />}
      {visualOn && settings.video && videoUrl && (
        <div className="toure-video-backdrop" aria-hidden="true">
          <video autoPlay muted loop playsInline preload="metadata" src={videoUrl} />
          <div className="toure-video-overlay" />
        </div>
      )}
      <ParticleField active={visualOn && settings.particles} intensity={settings.intensity} />
      <WaveField active={visualOn && settings.waves} intensity={settings.intensity} />
      {visualOn && settings.grain && <div className="toure-grain-layer" aria-hidden="true" />}
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={pathname}
          className="visual-route-layer"
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
          transition={{ duration: reduceMotion ? 0 : 0.32, ease: [0.22, 1, 0.36, 1] }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
