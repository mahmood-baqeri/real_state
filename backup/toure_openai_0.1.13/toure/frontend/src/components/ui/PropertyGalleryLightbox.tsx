"use client";

import React, { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Expand, X } from "lucide-react";
import type { PropertyMediaItem } from "@/lib/types";

const FALLBACK_IMAGES = [
  "/images/prop-zafaranieh.jpg",
  "/images/prop-fereshteh.jpg",
  "/images/prop-office.jpg",
  "/images/prop-villa.jpg",
];

function normalizeMediaUrl(url: string): string {
  if (url.startsWith("/images/prop-") && url.endsWith(".svg")) {
    return url.replace(/\.svg$/, ".jpg");
  }
  return url;
}

export function PropertyGalleryLightbox({
  title,
  mediaItems,
}: {
  title: string;
  mediaItems: PropertyMediaItem[];
}) {
  const gallery =
    mediaItems.length > 0
      ? mediaItems.map((m, idx) => ({
          id: m.id,
          url: normalizeMediaUrl(m.url),
          title: m.title || `${title} — تصویر ${idx + 1}`,
        }))
      : [
          {
            id: "fallback-0",
            url: FALLBACK_IMAGES[0],
            title,
          },
        ];

  const [activeIndex, setActiveIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const safeIndex = Math.min(activeIndex, gallery.length - 1);
  const current = gallery[safeIndex];

  useEffect(() => {
    if (!lightboxOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightboxOpen(false);
      if (e.key === "ArrowLeft") setActiveIndex((i) => (i + 1) % gallery.length);
      if (e.key === "ArrowRight")
        setActiveIndex((i) => (i - 1 + gallery.length) % gallery.length);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [lightboxOpen, gallery.length]);

  return (
    <>
      <div className="space-y-3">
        <div className="group relative aspect-[16/9] overflow-hidden rounded-xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-800">
          <img
            src={current.url}
            alt={current.title}
            referrerPolicy="no-referrer"
            onError={(e) => {
              const target = e.currentTarget;
              if (!target.dataset.fallbackApplied) {
                target.dataset.fallbackApplied = "1";
                target.src = FALLBACK_IMAGES[safeIndex % FALLBACK_IMAGES.length];
              }
            }}
            className="h-full w-full object-cover"
          />
          <button
            type="button"
            onClick={() => setLightboxOpen(true)}
            className="absolute bottom-3 left-3 inline-flex items-center gap-1.5 rounded-lg bg-slate-950/80 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-900"
          >
            <Expand className="h-3.5 w-3.5" />
            بزرگ‌نمایی ({gallery.length} تصویر)
          </button>
        </div>

        {gallery.length > 1 && (
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
            {gallery.map((item, idx) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveIndex(idx)}
                className={`aspect-[4/3] overflow-hidden rounded-lg border-2 transition-colors ${
                  idx === safeIndex
                    ? "border-teal-700 dark:border-teal-400"
                    : "border-transparent opacity-80 hover:opacity-100"
                }`}
              >
                <img
                  src={item.url}
                  alt={item.title}
                  referrerPolicy="no-referrer"
                  onError={(e) => {
                    const target = e.currentTarget;
                    if (!target.dataset.fallbackApplied) {
                      target.dataset.fallbackApplied = "1";
                      target.src = FALLBACK_IMAGES[idx % FALLBACK_IMAGES.length];
                    }
                  }}
                  className="h-full w-full object-cover"
                />
              </button>
            ))}
          </div>
        )}
      </div>

      {lightboxOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/90 p-4"
          onClick={() => setLightboxOpen(false)}
        >
          <div
            className="relative w-full max-w-4xl space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between text-white">
              <span className="text-sm font-semibold">{current.title}</span>
              <button
                type="button"
                onClick={() => setLightboxOpen(false)}
                className="rounded-lg bg-white/10 p-2 hover:bg-white/20"
                aria-label="بستن گالری"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="relative flex aspect-[16/10] items-center justify-center overflow-hidden rounded-xl bg-black">
              <img
                src={current.url}
                alt={current.title}
                referrerPolicy="no-referrer"
                onError={(e) => {
                  const target = e.currentTarget;
                  if (!target.dataset.fallbackApplied) {
                    target.dataset.fallbackApplied = "1";
                    target.src = FALLBACK_IMAGES[safeIndex % FALLBACK_IMAGES.length];
                  }
                }}
                className="max-h-full max-w-full object-contain"
              />
              {gallery.length > 1 && (
                <>
                  <button
                    type="button"
                    onClick={() =>
                      setActiveIndex((i) => (i - 1 + gallery.length) % gallery.length)
                    }
                    className="absolute right-3 rounded-lg bg-slate-950/75 p-2 text-white hover:bg-slate-900"
                    aria-label="تصویر قبلی"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveIndex((i) => (i + 1) % gallery.length)}
                    className="absolute left-3 rounded-lg bg-slate-950/75 p-2 text-white hover:bg-slate-900"
                    aria-label="تصویر بعدی"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
