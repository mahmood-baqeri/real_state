"use client";

import React, { useMemo, useState } from "react";
import { Check, Layers, Search } from "lucide-react";
import type { AmenityCategoryItem, AmenityItem, AmenityValueInput } from "@/lib/types";

export function CategorizedAmenitySelector({
  categories = [],
  amenities = [],
  selectedCodes,
  amenityValues = [],
  onToggleCode,
  onChangeValues,
  showTypedInputs = true,
  compact = false,
}: {
  categories?: AmenityCategoryItem[];
  amenities: AmenityItem[];
  selectedCodes: string[];
  amenityValues?: AmenityValueInput[];
  onToggleCode: (code: string) => void;
  onChangeValues?: (next: AmenityValueInput[]) => void;
  showTypedInputs?: boolean;
  compact?: boolean;
}) {
  const [search, setSearch] = useState("");
  const [activeCat, setActiveCat] = useState<string>("ALL");

  const valueMap = useMemo(() => {
    const map = new Map<string, AmenityValueInput>();
    for (const v of amenityValues) {
      map.set(v.code, v);
    }
    return map;
  }, [amenityValues]);

  const grouped = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = amenities.filter((am) => {
      if (am.is_active === false) return false;
      if (activeCat !== "ALL" && (am.category_code || "OTHER") !== activeCat) return false;
      if (!q) return true;
      return (
        am.name_fa.toLowerCase().includes(q) ||
        (am.name_en || "").toLowerCase().includes(q) ||
        (am.category_name_fa || "").toLowerCase().includes(q)
      );
    });

    const catOrder = new Map<string, number>();
    const catNames = new Map<string, string>();
    categories.forEach((c, idx) => {
      catOrder.set(c.code, c.sort_order ?? idx);
      catNames.set(c.code, c.name_fa);
    });

    const buckets = new Map<string, { code: string; name_fa: string; items: AmenityItem[] }>();
    for (const am of filtered) {
      const cCode = am.category_code || "OTHER";
      const cName = am.category_name_fa || catNames.get(cCode) || "سایر امکانات";
      if (!buckets.has(cCode)) {
        buckets.set(cCode, { code: cCode, name_fa: cName, items: [] });
      }
      buckets.get(cCode)!.items.push(am);
    }

    return Array.from(buckets.values()).sort(
      (a, b) => (catOrder.get(a.code) ?? 999) - (catOrder.get(b.code) ?? 999)
    );
  }, [amenities, categories, search, activeCat]);

  const updateValue = (code: string, patch: Partial<AmenityValueInput>) => {
    if (!onChangeValues) return;
    const exists = amenityValues.find((v) => v.code === code);
    if (exists) {
      onChangeValues(amenityValues.map((v) => (v.code === code ? { ...v, ...patch } : v)));
    } else {
      onChangeValues([...amenityValues, { code, ...patch }]);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-xs flex-1">
          <Search className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="جستجو در امکانات (پارکینگ، روف‌گاردن، داکت...)"
            className="h-9 w-full rounded-lg border border-slate-300 bg-white pr-8 pl-3 text-xs text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setActiveCat("ALL")}
            className={`rounded-md border px-2.5 py-1 text-[11px] font-semibold transition-colors ${
              activeCat === "ALL"
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            }`}
          >
            همه گروه‌ها ({selectedCodes.length} انتخاب)
          </button>
          {categories
            .filter((c) => c.is_active !== false)
            .map((c) => (
              <button
                key={c.code}
                type="button"
                onClick={() => setActiveCat(c.code)}
                className={`rounded-md border px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                  activeCat === c.code
                    ? "border-teal-700 bg-teal-700 text-white"
                    : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                {c.name_fa}
              </button>
            ))}
        </div>
      </div>

      {grouped.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 p-4 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
          امکاناتی مطابق با جستجوی شما یافت نشد.
        </div>
      ) : (
        <div className={compact ? "space-y-3" : "grid grid-cols-1 gap-3 lg:grid-cols-2"}>
          {grouped.map((group) => (
            <div
              key={group.code}
              className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-900/50"
            >
              <div className="mb-2.5 flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                <Layers className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                {group.name_fa}
              </div>
              <div className="flex flex-wrap gap-2">
                {group.items.map((am) => {
                  const isSelected = selectedCodes.includes(am.code);
                  const valObj = valueMap.get(am.code);
                  const needsInput =
                    showTypedInputs &&
                    isSelected &&
                    am.value_type &&
                    am.value_type !== "BOOLEAN";

                  return (
                    <div key={am.code} className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => onToggleCode(am.code)}
                        className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                          isSelected
                            ? "border-teal-700 bg-teal-50 text-teal-800 dark:border-teal-500 dark:bg-teal-950/70 dark:text-teal-300"
                            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                        }`}
                      >
                        <span
                          className={`flex h-3.5 w-3.5 items-center justify-center rounded border ${
                            isSelected
                              ? "border-teal-700 bg-teal-700 text-white dark:border-teal-500 dark:bg-teal-500"
                              : "border-slate-300 dark:border-slate-600"
                          }`}
                        >
                          {isSelected && <Check className="h-2.5 w-2.5" />}
                        </span>
                        <span>{am.name_fa}</span>
                      </button>

                      {needsInput && (
                        <div className="flex items-center gap-1">
                          {am.value_type === "CHOICE" && (am.options_json || []).length > 0 ? (
                            <select
                              value={valObj?.value_text || ""}
                              onChange={(e) =>
                                updateValue(am.code, { value_text: e.target.value })
                              }
                              className="h-8 rounded-md border border-teal-300 bg-white px-2 text-xs text-slate-900 dark:border-teal-700 dark:bg-slate-950 dark:text-slate-100"
                            >
                              <option value="">انتخاب مقدار...</option>
                              {(am.options_json || []).map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                            </select>
                          ) : am.value_type === "INTEGER" || am.value_type === "DECIMAL" ? (
                            <input
                              type="number"
                              min={0}
                              step={am.value_type === "DECIMAL" ? "0.5" : "1"}
                              placeholder={am.unit_label || "تعداد"}
                              value={valObj?.value_number ?? ""}
                              onChange={(e) =>
                                updateValue(am.code, {
                                  value_number: e.target.value ? Number(e.target.value) : null,
                                  value_text: e.target.value,
                                })
                              }
                              className="h-8 w-20 rounded-md border border-teal-300 bg-white px-2 text-center font-mono text-xs text-slate-900 dark:border-teal-700 dark:bg-slate-950 dark:text-slate-100"
                            />
                          ) : (
                            <input
                              type="text"
                              placeholder="توضیح / مقدار"
                              value={valObj?.value_text || ""}
                              onChange={(e) =>
                                updateValue(am.code, { value_text: e.target.value })
                              }
                              className="h-8 w-28 rounded-md border border-teal-300 bg-white px-2 text-xs text-slate-900 dark:border-teal-700 dark:bg-slate-950 dark:text-slate-100"
                            />
                          )}
                          {am.unit_label && (
                            <span className="text-[11px] text-slate-500 dark:text-slate-400">
                              {am.unit_label}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
