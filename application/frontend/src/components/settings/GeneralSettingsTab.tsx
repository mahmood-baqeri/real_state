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
                <div className="lg:col-span-6 space-y-1">
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

                <div className="lg:col-span-4">{renderInput(s)}</div>

                <div className="lg:col-span-2 flex items-center justify-end gap-2">
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
