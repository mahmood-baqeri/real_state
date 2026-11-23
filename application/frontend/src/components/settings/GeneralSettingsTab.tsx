"use client";

import React, { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RotateCcw, Save, Search, Shield, SlidersHorizontal } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { SystemSettingItem } from "@/lib/types";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { LoadingState } from "@/components/ui/StateNotice";

interface Props {
  onNotice: (msg: string) => void;
  onError: (msg: string) => void;
}

const CATEGORY_TABS: { code: string; label: string }[] = [
  { code: "ALL", label: "همه تنظیمات" },
  { code: "GENERAL", label: "عمومی پلتفرم" },
  { code: "BRANDING", label: "هویت بصری و برندینگ" },
  { code: "LOCALIZATION", label: "بومی‌سازی و زبان" },
  { code: "PROPERTY", label: "املاک و انتشار" },
  { code: "FINANCE", label: "مالی و کمیسیون" },
  { code: "NOTIFICATIONS", label: "اعلان‌ها" },
  { code: "AI", label: "هوش مصنوعی" },
  { code: "SMS", label: "پیامک" },
  { code: "SECURITY", label: "امنیت" },
  { code: "LEGAL", label: "قوانین و انطباق" },
  { code: "VIRTUAL_TOUR", label: "تور مجازی و سه‌بعدی" },
];

export function GeneralSettingsTab({ onNotice, onError }: Props) {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [category, setCategory] = useState("ALL");
  const [searchText, setSearchText] = useState("");
  const [draftValues, setDraftValues] = useState<Record<string, unknown>>({});
  const [changeReason, setChangeReason] = useState("به‌روزرسانی تنظیمات از مرکز کنترل");
  const [createOpen, setCreateOpen] = useState(false);
  const [newForm, setNewForm] = useState({
    key: "",
    title_fa: "",
    description: "",
    category: "GENERAL",
    value_type: "STRING",
    value: "",
    sensitivity_level: "ADMIN",
  });

  const registryQ = useQuery({
    queryKey: ["settings-registry", category, activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () => {
      const qs = category !== "ALL" ? `?category=${encodeURIComponent(category)}` : "";
      return (
        await apiFetch<SystemSettingItem[]>(`/api/v1/settings/registry${qs}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const filteredItems = useMemo(() => {
    const list = registryQ.data || [];
    const term = searchText.trim().toLowerCase();
    if (!term) return list;
    return list.filter(
      (s) =>
        s.key.toLowerCase().includes(term) ||
        s.title_fa.toLowerCase().includes(term) ||
        (s.description || "").toLowerCase().includes(term)
    );
  }, [registryQ.data, searchText]);

  const dirtyKeys = useMemo(() => Object.keys(draftValues), [draftValues]);

  const bulkSaveMut = useMutation({
    mutationFn: async () => {
      const updates = Object.entries(draftValues).map(([key, val]) => {
        const orig = (registryQ.data || []).find((x) => x.key === key);
        let parsedVal: unknown = val;
        if (orig?.value_type === "INTEGER") parsedVal = Number(val);
        else if (orig?.value_type === "DECIMAL") parsedVal = String(val);
        else if (orig?.value_type === "JSON" && typeof val === "string") {
          try {
            parsedVal = JSON.parse(val);
          } catch {
            throw new Error(`مقدار JSON برای کلید ${key} نامعتبر است.`);
          }
        }
        return { key, value: parsedVal, country_code: orig?.country_code || "" };
      });
      return apiFetch<SystemSettingItem[]>("/api/v1/settings/registry", {
        method: "PUT",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ updates, change_reason: changeReason }),
      });
    },
    onSuccess: () => {
      setDraftValues({});
      onNotice("تنظیمات ویرایش‌شده در PostgreSQL ذخیره و کش زنده سیستم به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["settings-registry"] });
      qc.invalidateQueries({ queryKey: ["settings-history"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const resetMut = useMutation({
    mutationFn: async (settingId: string) =>
      apiFetch<SystemSettingItem>(`/api/v1/settings/registry/${settingId}/reset`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ change_reason: "بازنشانی به مقدار پیش‌فرض از پنل مدیریت" }),
      }),
    onSuccess: (res) => {
      setDraftValues((prev) => {
        const copy = { ...prev };
        delete copy[res.data.key];
        return copy;
      });
      onNotice(`تنظیم «${res.data.title_fa}» به مقدار پیش‌فرض بازگشت.`);
      qc.invalidateQueries({ queryKey: ["settings-registry"] });
      qc.invalidateQueries({ queryKey: ["settings-history"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const createCustomMut = useMutation({
    mutationFn: async () =>
      apiFetch<SystemSettingItem[]>("/api/v1/settings/registry", {
        method: "PUT",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          updates: [
            {
              key: newForm.key.trim(),
              value:
                newForm.value_type === "BOOLEAN"
                  ? newForm.value === "true"
                  : newForm.value_type === "INTEGER"
                  ? Number(newForm.value || 0)
                  : newForm.value,
              create_if_missing: true,
              title_fa: newForm.title_fa.trim(),
              description: newForm.description.trim(),
              category: newForm.category,
              value_type: newForm.value_type,
              sensitivity_level: newForm.sensitivity_level,
            },
          ],
          change_reason: "ایجاد کلید تنظیم سفارشی جدید",
        }),
      }),
    onSuccess: () => {
      setCreateOpen(false);
      setNewForm({
        key: "",
        title_fa: "",
        description: "",
        category: "GENERAL",
        value_type: "STRING",
        value: "",
        sensitivity_level: "ADMIN",
      });
      onNotice("کلید تنظیم جدید در رجیستری مرکزی ثبت شد.");
      qc.invalidateQueries({ queryKey: ["settings-registry"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const renderInput = (s: SystemSettingItem) => {
    const hasDraft = s.key in draftValues;
    const rawVal = hasDraft ? draftValues[s.key] : s.value;

    if (!s.is_editable) {
      return (
        <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
          {String(rawVal ?? "—")} (فقط خواندنی)
        </span>
      );
    }

    if (s.value_type === "BOOLEAN") {
      const checked = Boolean(rawVal);
      return (
        <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setDraftValues((p) => ({ ...p, [s.key]: e.target.checked }))}
            className="h-4 w-4 accent-teal-700"
          />
          {checked ? "فعال" : "غیرفعال"}
        </label>
      );
    }

    const selectOpts = Array.isArray(s.validation_schema?.options)
      ? s.validation_schema.options
      : Array.isArray((s.validation_schema as { choices?: unknown[] })?.choices)
      ? ((s.validation_schema as { choices?: string[] }).choices ?? [])
      : null;

    if (s.key === "branding.default_theme_preset") {
      const presets = [
        { value: "glass", name: "گلس لوکس", en: "LUXURY GLASS", desc: "لایه‌های شیشه‌ای، محوشدگی عمیق، نورهای شناور و سطوح نیمه‌شفاف", accent: "#5266c8", accent2: "#54c8c0", canvas: "#e9efff", surface: "#f9fbff", line: "#cbd7f4", shape: "glass" },
        { value: "neo", name: "نئوفیوچر", en: "NEO FUTURE", desc: "فضای سینمایی تیره، هاله‌های نوری، کنتراست بالا و عمق سه‌بعدی", accent: "#7c5cff", accent2: "#22d3ee", canvas: "#101426", surface: "#1a2038", line: "#343b61", shape: "neo" },
        { value: "organic", name: "ارگانیک پریمیوم", en: "ORGANIC PREMIUM", desc: "فرم‌های نرم، رنگ‌های طبیعی، گرادیان‌های گرم و حس لوکس آرام", accent: "#68734d", accent2: "#c18b65", canvas: "#f1ebdf", surface: "#fffaf1", line: "#ded2bd", shape: "organic" },
      ];
      return (
        <>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {presets.map((preset) => {
            const active = String(rawVal) === preset.value;
            return (
              <button
                key={preset.value}
                type="button"
                aria-pressed={active}
                onClick={() => setDraftValues((p) => ({ ...p, [s.key]: preset.value }))}
                data-theme-option={preset.value}
                className={`group overflow-hidden rounded-2xl border text-right transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 ${active ? "border-teal-600 ring-2 ring-teal-600/20 shadow-xl -translate-y-0.5" : "border-slate-200 hover:-translate-y-1 hover:border-slate-300 hover:shadow-lg dark:border-slate-700"}`}
              >
                <div className="theme-preset-preview p-3" data-preview-style={preset.shape} style={{ background: preset.canvas }}>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-[9px] font-bold tracking-[0.18em]" style={{ color: preset.accent }}>{preset.en}</span>
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: preset.accent2 }} />
                  </div>
                  <div className="theme-preset-mini flex h-[82px] gap-2 overflow-hidden rounded-lg border p-2" data-preview-style={preset.shape} style={{ background: preset.surface, borderColor: preset.line }}>
                    <div className="theme-preset-mini-nav w-1/4 rounded-md p-1.5" style={{ background: preset.accent }}>
                      <div className="mb-2 h-1.5 w-3/4 rounded-full bg-white/80" />
                      <div className="mb-1 h-1 w-full rounded-full bg-white/35" />
                      <div className="mb-1 h-1 w-4/5 rounded-full bg-white/35" />
                      <div className="mt-3 h-3 rounded" style={{ background: preset.accent2 }} />
                    </div>
                    <div className="flex-1 space-y-1.5 py-0.5">
                      <div className="h-2 w-2/5 rounded-full" style={{ background: preset.accent }} />
                      <div className="grid grid-cols-3 gap-1">
                        {[0, 1, 2].map((n) => <div key={n} className="h-8 rounded border" style={{ borderColor: preset.line, background: preset.canvas }} />)}
                      </div>
                      <div className="h-1 w-3/5 rounded-full" style={{ background: preset.line }} />
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-1.5">
                    {[preset.accent, preset.accent2, preset.canvas, preset.line].map((color) => <span key={color} className="h-3 w-3 rounded-full border border-black/5" style={{ background: color }} />)}
                    <span className="mr-auto text-[9px] font-medium" style={{ color: preset.accent }}>پیش‌نمایش رابط کاربری</span>
                  </div>
                </div>
                <div className="flex min-h-[76px] items-start justify-between gap-2 bg-white p-3 dark:bg-slate-900">
                  <div>
                    <div className="text-xs font-bold text-slate-900 dark:text-slate-100">{preset.name}</div>
                    <p className="mt-1 text-[10px] leading-5 text-slate-500 dark:text-slate-400">{preset.desc}</p>
                  </div>
                  <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] ${active ? "border-teal-600 bg-teal-600 text-white" : "border-slate-300 text-transparent dark:border-slate-600"}`}>✓</span>
                </div>
              </button>
            );
          })}
          <div className={`overflow-hidden rounded-2xl border text-right transition-all ${String(rawVal) === "custom" ? "border-violet-500 ring-2 ring-violet-500/20 shadow-xl" : "border-slate-200 hover:-translate-y-1 hover:shadow-lg dark:border-slate-700"}`}>
            <button type="button" aria-pressed={String(rawVal) === "custom"} onClick={() => setDraftValues((p) => ({ ...p, [s.key]: "custom" }))} className="block w-full p-3 text-right">
              <div className="flex h-[82px] items-center justify-center gap-3 rounded-xl border border-white/20" style={{background:"linear-gradient(135deg,#15172b,#3d2b68 48%,#0e8e91)"}}>
                <span className="h-10 w-10 rounded-full border-2 border-white/70 shadow-lg" style={{background:"#9b7cff"}}/><span className="h-7 w-7 rounded-full border-2 border-white/70" style={{background:"#31d6c5"}}/><span className="h-5 w-5 rounded-full border-2 border-white/70" style={{background:"#f3b86b"}}/>
              </div>
              <div className="mt-3 flex items-center justify-between"><div><div className="text-xs font-bold text-slate-900 dark:text-slate-100">طراحی رنگ اختصاصی</div><p className="mt-1 text-[10px] text-slate-500 dark:text-slate-400">پالت رنگی خودت را بساز و ذخیره کن</p></div><span className="text-lg text-violet-500">✦</span></div>
            </button>
            <div className="grid grid-cols-2 gap-2 border-t border-slate-200 p-3 dark:border-slate-700">
              {[{key:"--custom-accent",label:"رنگ اصلی",fallback:"#7657e8"},{key:"--custom-secondary",label:"رنگ مکمل",fallback:"#20b9ad"},{key:"--custom-canvas",label:"پس‌زمینه",fallback:"#f1f2f8"},{key:"--custom-surface",label:"سطح کارت",fallback:"#ffffff"}].map((c) => <label key={c.key} className="flex items-center gap-2 text-[10px] text-slate-600 dark:text-slate-300"><input aria-label={c.label} type="color" defaultValue={typeof window !== "undefined" ? localStorage.getItem(`toure-theme-${c.key}`) || c.fallback : c.fallback} onChange={(e) => { localStorage.setItem(`toure-theme-${c.key}`, e.target.value); document.documentElement.style.setProperty(c.key, e.target.value); document.documentElement.dataset.visualStyle = "custom"; setDraftValues((p) => ({ ...p, [s.key]: "custom" })); }} className="h-8 w-9 cursor-pointer rounded-lg border-0 bg-transparent"/><span>{c.label}</span></label>)}
            </div>
          </div>
        </div>
        <VisualEffectsPanel />
        </>
      );
    }

    if (s.value_type === "SELECT" && selectOpts) {
      return (
        <select
          value={String(rawVal ?? "")}
          onChange={(e) => setDraftValues((p) => ({ ...p, [s.key]: e.target.value }))}
          className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
        >
          {selectOpts.map((opt) => (
            <option key={String(opt)} value={String(opt)}>
              {String(opt)}
            </option>
          ))}
        </select>
      );
    }

    if (s.value_type === "SECRET") {
      return (
        <input
          type="password"
          value={hasDraft ? String(rawVal ?? "") : ""}
          placeholder={s.has_secret_value ? "**** (برای تغییر مقدار جدید وارد کنید)" : "مقدار محرمانه وارد نشده"}
          onChange={(e) => setDraftValues((p) => ({ ...p, [s.key]: e.target.value }))}
          className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 font-mono text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
        />
      );
    }

    if (s.value_type === "COLOR") {
      const hex = String(rawVal || "#0F766E");
      return (
        <div className="flex items-center gap-2">
          <input
            type="color"
            value={/^#[0-9A-Fa-f]{6}$/.test(hex) ? hex : "#0F766E"}
            onChange={(e) => setDraftValues((p) => ({ ...p, [s.key]: e.target.value }))}
            className="h-9 w-11 cursor-pointer rounded border border-slate-300 bg-white p-0.5 dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            type="text"
            dir="ltr"
            value={hex}
            onChange={(e) => setDraftValues((p) => ({ ...p, [s.key]: e.target.value }))}
            className="h-9 flex-1 rounded-lg border border-slate-300 bg-white px-3 font-mono text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          />
        </div>
      );
    }

    if (s.value_type === "JSON") {
      const strVal =
        typeof rawVal === "string" ? rawVal : JSON.stringify(rawVal ?? {}, null, 2);
      return (
        <textarea
          rows={3}
          dir="ltr"
          value={strVal}
          onChange={(e) => setDraftValues((p) => ({ ...p, [s.key]: e.target.value }))}
          className="w-full rounded-lg border border-slate-300 bg-white p-2 font-mono text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
        />
      );
    }

    if (s.value_type === "INTEGER" || s.value_type === "DECIMAL") {
      return (
        <input
          type="number"
          step={s.value_type === "DECIMAL" ? "any" : "1"}
          min={s.validation_schema?.min}
          max={s.validation_schema?.max}
          value={String(rawVal ?? "")}
          onChange={(e) => setDraftValues((p) => ({ ...p, [s.key]: e.target.value }))}
          className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 font-mono text-xs tabular-nums text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
        />
      );
    }

    return (
      <input
        type="text"
        value={String(rawVal ?? "")}
        onChange={(e) => setDraftValues((p) => ({ ...p, [s.key]: e.target.value }))}
        className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
      />
    );
  };

  return (
    <div className="space-y-5">
      {/* Category Pills & Search Toolbar */}
      <div className="surface-card rounded-xl p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1.5">
            {CATEGORY_TABS.map((t) => (
              <button
                key={t.code}
                type="button"
                onClick={() => setCategory(t.code)}
                className={`h-8 shrink-0 whitespace-nowrap rounded-lg border px-3 text-xs font-semibold transition-colors ${
                  category === t.code
                    ? "border-teal-700 bg-teal-700 text-white dark:border-teal-500 dark:bg-teal-600"
                    : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {effectiveRole === "SUPER_ADMIN" && (
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              <Plus className="h-3.5 w-3.5 text-teal-600" />
              تعریف کلید تنظیم جدید
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="pointer-events-none absolute right-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="جستجو بر اساس کلید یا عنوان تنظیم..."
              className="h-9 w-full rounded-lg border border-slate-300 bg-white pr-9 pl-3 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
          </div>

          {dirtyKeys.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={changeReason}
                onChange={(e) => setChangeReason(e.target.value)}
                placeholder="علت تغییر (برای گزارش ممیزی)..."
                className="h-9 w-56 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
              />
              <button
                type="button"
                disabled={bulkSaveMut.isPending}
                onClick={() => bulkSaveMut.mutate()}
                className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                <Save className="h-3.5 w-3.5" />
                ذخیره {dirtyKeys.length} تغییر
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Registry List */}
      {registryQ.isLoading ? (
        <LoadingState />
      ) : (
        <div className="surface-card overflow-hidden rounded-xl divide-y divide-slate-200 dark:divide-slate-800">
          {filteredItems.map((s) => {
            const isDirty = s.key in draftValues;
            return (
              <div
                key={s.id}
                className={`grid grid-cols-1 gap-3 p-4 lg:grid-cols-12 lg:items-center ${
                  isDirty ? "bg-teal-50/40 dark:bg-teal-950/20" : ""
                }`}
              >
                <div className={`${s.key === "branding.default_theme_preset" ? "lg:col-span-12" : "lg:col-span-6"} space-y-1`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {s.title_fa}
                    </span>
                    <span className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                      {s.key}
                    </span>
                    {s.sensitivity_level === "SECRET" && (
                      <span className="inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                        <Shield className="h-3 w-3" />
                        محرمانه
                      </span>
                    )}
                    {s.requires_restart && (
                      <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-800 dark:bg-rose-950/60 dark:text-rose-300">
                        نیازمند Restart
                      </span>
                    )}
                  </div>
                  {s.description && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">{s.description}</p>
                  )}
                </div>

                <div className={s.key === "branding.default_theme_preset" ? "lg:col-span-12" : "lg:col-span-4"}>{renderInput(s)}</div>

                <div className={`${s.key === "branding.default_theme_preset" ? "lg:col-span-12" : "lg:col-span-2"} flex items-center justify-end gap-2`}>
                  <span className="font-mono text-[10px] text-slate-400">{s.category}</span>
                  {s.is_editable && effectiveRole === "SUPER_ADMIN" && (
                    <button
                      type="button"
                      title="بازنشانی به پیش‌فرض"
                      disabled={resetMut.isPending}
                      onClick={() => resetMut.mutate(s.id)}
                      className="inline-flex h-8 shrink-0 items-center gap-1 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-2.5 text-[11px] font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                    >
                      <RotateCcw className="h-3 w-3" />
                      پیش‌فرض
                    </button>
                  )}
                </div>
              </div>
            );
          })}
          {filteredItems.length === 0 && (
            <div className="p-8 text-center text-xs text-slate-500 dark:text-slate-400">
              <SlidersHorizontal className="mx-auto mb-2 h-5 w-5 opacity-50" />
              تنظیمی مطابق فیلتر شما یافت نشد.
            </div>
          )}
        </div>
      )}

      {/* Custom Setting Modal */}
      <ModalDrawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="تعریف کلید تنظیم جدید در رجیستری"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createCustomMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            dir="ltr"
            placeholder="کلید یکتا (مثال: general.support_hours)"
            value={newForm.key}
            onChange={(e) => setNewForm({ ...newForm, key: e.target.value })}
            className="h-9 w-full rounded-lg border border-slate-300 px-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            required
            placeholder="عنوان فارسی"
            value={newForm.title_fa}
            onChange={(e) => setNewForm({ ...newForm, title_fa: e.target.value })}
            className="h-9 w-full rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <input
            placeholder="توضیحات راهنما"
            value={newForm.description}
            onChange={(e) => setNewForm({ ...newForm, description: e.target.value })}
            className="h-9 w-full rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <div className="grid grid-cols-3 gap-2">
            <select
              value={newForm.category}
              onChange={(e) => setNewForm({ ...newForm, category: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
            >
              {CATEGORY_TABS.filter((c) => c.code !== "ALL").map((c) => (
                <option key={c.code} value={c.code}>
                  {c.label}
                </option>
              ))}
            </select>
            <select
              value={newForm.value_type}
              onChange={(e) => setNewForm({ ...newForm, value_type: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
            >
              <option value="STRING">متنی (STRING)</option>
              <option value="INTEGER">عددی (INTEGER)</option>
              <option value="DECIMAL">اعشاری (DECIMAL)</option>
              <option value="BOOLEAN">بولین (BOOLEAN)</option>
              <option value="COLOR">رنگ (COLOR)</option>
              <option value="SECRET">محرمانه (SECRET)</option>
            </select>
            <select
              value={newForm.sensitivity_level}
              onChange={(e) => setNewForm({ ...newForm, sensitivity_level: e.target.value })}
              className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
            >
              <option value="PUBLIC">عمومی</option>
              <option value="ADMIN">مدیریتی</option>
              <option value="SECRET">محرمانه</option>
            </select>
          </div>
          <input
            placeholder="مقدار اولیه"
            value={newForm.value}
            onChange={(e) => setNewForm({ ...newForm, value: e.target.value })}
            className="h-9 w-full rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
          />
          <button
            type="submit"
            disabled={createCustomMut.isPending}
            className="h-9 w-full rounded-lg bg-teal-700 text-xs font-semibold text-white hover:bg-teal-800"
          >
            ثبت کلید در دیتابیس
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}


const VISUAL_EFFECTS = [
  { id: "aurora", title: "Aurora Immersive", subtitle: "نورهای چندلایه، ذرات متصل، موج و هاله‌های زنده", swatch: "radial-gradient(circle at 20% 20%,#67e8f9,transparent 35%),linear-gradient(120deg,#071b3a,#5526a8,#087e83)" },
  { id: "obsidian", title: "Obsidian Luxury", subtitle: "عمق سینمایی، بازتاب متالیک و نورپردازی لوکس", swatch: "radial-gradient(circle at 70% 20%,#b99b63,transparent 28%),linear-gradient(120deg,#030712,#1f2937,#5b4a35)" },
  { id: "crystal", title: "Crystal Infinity", subtitle: "شیشه کریستالی، شفافیت چندلایه و بازتاب نور", swatch: "radial-gradient(circle at 25% 20%,#fff,transparent 30%),linear-gradient(120deg,#dbeafe,#7dd3fc,#818cf8)" },
  { id: "holographic", title: "Holographic Vision", subtitle: "هاله‌های هولوگرافیک، رنگین‌تابی و نور تعاملی", swatch: "linear-gradient(120deg,#312e81,#0e7490,#be185d,#7c3aed)" },
  { id: "off", title: "بدون پروفایل", subtitle: "حفظ تنظیمات مستقل افکت‌ها بدون ظاهر پروفایلی", swatch: "linear-gradient(120deg,#64748b,#94a3b8)" },
] as const;

type VisualFxPrefs = { enabled: boolean; particles: boolean; waves: boolean; grain: boolean; video: boolean; videoUrl: string; intensity: number };
const VISUAL_FX_KEY = "toure-visual-experience-settings";
const DEFAULT_VISUAL_FX: VisualFxPrefs = { enabled: true, particles: true, waves: true, grain: true, video: false, videoUrl: "", intensity: 68 };

function VisualEffectsPanel() {
  const [selected, setSelected] = useState<(typeof VISUAL_EFFECTS)[number]["id"]>("aurora");
  const [prefs, setPrefs] = useState<VisualFxPrefs>(DEFAULT_VISUAL_FX);

  React.useEffect(() => {
    try {
      const savedProfile = localStorage.getItem("toure-visual-effects");
      if (VISUAL_EFFECTS.some((item) => item.id === savedProfile)) setSelected(savedProfile as typeof selected);
      const savedPrefs = JSON.parse(localStorage.getItem(VISUAL_FX_KEY) || "{}") as Partial<VisualFxPrefs>;
      setPrefs({ ...DEFAULT_VISUAL_FX, ...savedPrefs, intensity: Math.max(0, Math.min(100, Number(savedPrefs.intensity ?? 68))) });
    } catch { /* use defaults */ }
  }, []);

  const apply = (nextPrefs: VisualFxPrefs, profile = selected) => {
    setPrefs(nextPrefs);
    setSelected(profile);
    try {
      localStorage.setItem(VISUAL_FX_KEY, JSON.stringify(nextPrefs));
      localStorage.setItem("toure-visual-effects", profile);
    } catch { /* storage may be unavailable */ }
    document.documentElement.dataset.visualEffects = nextPrefs.enabled ? profile : "off";
    window.dispatchEvent(new Event("toure:visual-settings"));
  };

  const choose = (id: typeof selected) => apply(prefs, id);
  const toggle = (key: "enabled" | "particles" | "waves" | "grain" | "video", checked: boolean) => apply({ ...prefs, [key]: checked });

  const switches: { key: "enabled" | "particles" | "waves" | "grain" | "video"; title: string; detail: string }[] = [
    { key: "enabled", title: "فعال‌سازی کلی جلوه‌ها", detail: "خاموش‌کردن این گزینه تمام لایه‌های بصری را در همه صفحات غیرفعال می‌کند." },
    { key: "particles", title: "ذرات متصل (Particles)", detail: "ذرات شناور با خطوط اتصال و حرکت آرام؛ واکنش سبک به محیط." },
    { key: "waves", title: "امواج SVG متحرک", detail: "امواج چندلایه در پس‌زمینه با حرکت نرم و پیوسته." },
    { key: "grain", title: "نویز و Grain سینمایی", detail: "بافت ظریف برای عمق بصری؛ بدون پوشاندن متن و محتوا." },
    { key: "video", title: "ویدیو پس‌زمینه", detail: "ویدیوی Loop با Overlay تیره برای حفظ خوانایی رابط." },
  ];

  return (
    <section className="visual-effects-panel mt-5 overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-700">
      <div className="border-b border-slate-200 bg-gradient-to-l from-violet-500/15 via-cyan-500/10 to-transparent p-4 dark:border-slate-700">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-black text-slate-900 dark:text-white">Visual Experience · موتور سراسری جلوه‌های بصری</div>
            <p className="mt-1 text-[11px] leading-5 text-slate-500 dark:text-slate-400">این موتور در تمام صفحات عمومی، ورود، ثبت‌نام، پنل کاربری و مدیریت فعال است و از تم رنگی و حالت روشن/تاریک مستقل می‌ماند.</p>
          </div>
          <span className="rounded-full border border-violet-300/60 bg-violet-500/10 px-3 py-1 text-[10px] font-bold text-violet-700 dark:text-violet-300">GLOBAL LIVE FX</span>
        </div>
      </div>
      <div className="grid gap-3 p-3 sm:grid-cols-2">
        {VISUAL_EFFECTS.map((effect) => {
          const active = selected === effect.id;
          return (
            <button key={effect.id} type="button" aria-pressed={active} onClick={() => choose(effect.id)} className={`group overflow-hidden rounded-xl border text-right transition-all duration-300 ${active ? "border-violet-500 ring-2 ring-violet-500/20 shadow-lg" : "border-slate-200 hover:-translate-y-0.5 hover:shadow-md dark:border-slate-700"}`}>
              <div className={`visual-profile-preview visual-profile-preview--${effect.id}`} data-preview-profile={effect.id} aria-hidden="true">
                <div className="visual-preview-orb visual-preview-orb--one" />
                <div className="visual-preview-orb visual-preview-orb--two" />
                <div className="visual-preview-shell">
                  <div className="visual-preview-rail"><i /><i /><i /><i /></div>
                  <div className="visual-preview-content">
                    <div className="visual-preview-topline"><i /><i /><i /></div>
                    <div className="visual-preview-chart"><svg viewBox="0 0 180 52" preserveAspectRatio="none"><path d="M0 40 C25 35 26 12 52 24 S88 43 112 18 S151 12 180 5" /></svg></div>
                    <div className="visual-preview-widgets"><i /><i /><i /></div>
                  </div>
                </div>
                {active && <span className="visual-preview-active">فعال</span>}
              </div>
              <div className="p-3">
                <div className="text-xs font-bold text-slate-900 dark:text-slate-100">{effect.title}</div>
                <p className="mt-1 text-[10px] leading-5 text-slate-500 dark:text-slate-400">{effect.subtitle}</p>
              </div>
            </button>
          );
        })}
      </div>
      <div className="border-t border-slate-200 p-4 dark:border-slate-700">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="text-xs font-black text-slate-900 dark:text-white">کنترل مستقل افکت‌ها</div>
          <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${prefs.enabled ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{prefs.enabled ? "موتور فعال" : "موتور خاموش"}</span>
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          {switches.map((item) => (
            <label key={item.key} className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-white/60 p-3 dark:border-slate-700 dark:bg-slate-900/40">
              <input type="checkbox" checked={prefs[item.key]} onChange={(event) => toggle(item.key, event.target.checked)} className="mt-1 h-4 w-4 accent-violet-600" />
              <span className="min-w-0"><span className="block text-xs font-bold text-slate-800 dark:text-slate-100">{item.title}</span><span className="mt-1 block text-[10px] leading-5 text-slate-500 dark:text-slate-400">{item.detail}</span></span>
            </label>
          ))}
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="block"><span className="mb-2 flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200"><span>شدت جلوه‌ها</span><span>{prefs.intensity}%</span></span><input type="range" min="0" max="100" value={prefs.intensity} onChange={(event) => apply({ ...prefs, intensity: Number(event.target.value) })} className="w-full accent-violet-600" /></label>
          <label className="block"><span className="mb-2 block text-xs font-bold text-slate-700 dark:text-slate-200">آدرس ویدیوی پس‌زمینه (MP4/WebM)</span><input type="url" dir="ltr" value={prefs.videoUrl} onChange={(event) => apply({ ...prefs, videoUrl: event.target.value })} placeholder="https://example.com/ambient-loop.mp4" className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" /></label>
        </div>
        <p className="mt-3 text-[10px] leading-5 text-slate-500 dark:text-slate-400">برای ویدیو، ابتدا آدرس مستقیم فایل MP4 یا WebM را وارد و سپس گزینه ویدیو پس‌زمینه را فعال کن. در صورت خالی‌بودن آدرس، ویدیویی بارگذاری نمی‌شود. تمام انتخاب‌ها در همین مرورگر ذخیره می‌شوند. کاهش حرکت سیستم‌عامل نیز رعایت می‌شود.</p>
      </div>
    </section>
  );
}
