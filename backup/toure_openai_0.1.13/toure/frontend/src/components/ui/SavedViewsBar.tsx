"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Plus, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { SavedViewItem } from "@/lib/types";

export function SavedViewsBar({
  module,
  currentFilters,
  onApply,
}: {
  module: string;
  currentFilters: Record<string, string>;
  onApply: (filters: Record<string, string>) => void;
}) {
  const { accessToken, activeAgencyId } = useAuth();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);

  const { data: views = [] } = useQuery({
    queryKey: ["saved-views", module, activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () => {
      const env = await apiFetch<SavedViewItem[]>(
        `/api/v1/search/views?module=${encodeURIComponent(module)}`,
        { token: accessToken, agencyId: activeAgencyId }
      );
      return env.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiFetch<SavedViewItem>("/api/v1/search/views", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          module,
          title: title.trim(),
          filters_json: currentFilters,
        }),
      }),
    onSuccess: () => {
      setTitle("");
      setCreating(false);
      queryClient.invalidateQueries({ queryKey: ["saved-views", module] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/search/views/${id}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saved-views", module] });
    },
  });

  if (!accessToken) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
          <Bookmark className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
          نماهای ذخیره‌شده:
        </span>
        {views.length === 0 ? (
          <span className="text-xs text-slate-400 dark:text-slate-500">
            هنوز نمایی ذخیره نشده است
          </span>
        ) : (
          views.map((v) => (
            <div
              key={v.id}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs dark:border-slate-700 dark:bg-slate-800"
            >
              <button
                type="button"
                onClick={() => onApply(v.filters_json || {})}
                className="font-medium text-slate-800 hover:text-teal-700 dark:text-slate-200 dark:hover:text-teal-300"
              >
                {v.title}
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(v.id)}
                className="text-slate-400 hover:text-rose-600 dark:hover:text-rose-400"
                aria-label={`حذف ${v.title}`}
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))
        )}
      </div>

      {creating ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (title.trim()) createMutation.mutate();
          }}
          className="flex items-center gap-1.5"
        >
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="نام نمای فیلتر..."
            className="h-8 rounded-lg border border-slate-300 bg-white px-2.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          />
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="h-8 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            ذخیره
          </button>
          <button
            type="button"
            onClick={() => setCreating(false)}
            className="h-8 rounded-lg border border-slate-300 px-2.5 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300"
          >
            لغو
          </button>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <Plus className="h-3.5 w-3.5" />
          ذخیره فیلتر فعلی
        </button>
      )}
    </div>
  );
}
