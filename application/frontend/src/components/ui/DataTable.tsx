"use client";

import React, { useMemo, useState } from "react";
import { ArrowDownUp, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { EmptyState, ErrorState, LoadingState } from "./StateNotice";

export interface ColumnDef<T> {
  key: string;
  header: string;
  align?: "right" | "left" | "center";
  sortValue?: (row: T) => string | number;
  render: (row: T) => React.ReactNode;
}

export interface FilterTab {
  value: string;
  label: string;
}

interface DataTableProps<T> {
  rows: T[];
  columns: ColumnDef<T>[];
  rowKey: (row: T) => string;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (q: string) => void;
  filterTabs?: FilterTab[];
  activeFilter?: string;
  onFilterChange?: (val: string) => void;
  pageSize?: number;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  toolbarExtra?: React.ReactNode;
}

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  isLoading = false,
  error = null,
  onRetry,
  searchPlaceholder = "جستجو...",
  searchValue,
  onSearchChange,
  filterTabs,
  activeFilter,
  onFilterChange,
  pageSize = 10,
  emptyTitle,
  emptyDescription,
  emptyAction,
  toolbarExtra,
}: DataTableProps<T>) {
  const [internalSearch, setInternalSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);

  const query = searchValue !== undefined ? searchValue : internalSearch;
  const setQuery = (val: string) => {
    setPage(1);
    if (onSearchChange) onSearchChange(val);
    else setInternalSearch(val);
  };

  const processed = useMemo(() => {
    let list = [...rows];
    if (searchValue === undefined && query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter((item) => JSON.stringify(item).toLowerCase().includes(q));
    }
    if (sortCol) {
      const colDef = columns.find((c) => c.key === sortCol);
      if (colDef?.sortValue) {
        const fn = colDef.sortValue;
        list.sort((a, b) => {
          const va = fn(a);
          const vb = fn(b);
          if (typeof va === "number" && typeof vb === "number") {
            return sortDir === "asc" ? va - vb : vb - va;
          }
          const cmp = String(va).localeCompare(String(vb), "fa");
          return sortDir === "asc" ? cmp : -cmp;
        });
      }
    }
    return list;
  }, [rows, query, searchValue, sortCol, sortDir, columns]);

  const totalPages = Math.max(1, Math.ceil(processed.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pagedRows = processed.slice((safePage - 1) * pageSize, safePage * pageSize);

  const toggleSort = (key: string) => {
    if (sortCol === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(key);
      setSortDir("asc");
    }
  };

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  return (
    <div className="space-y-4">
      {(onSearchChange !== undefined || searchPlaceholder || filterTabs || toolbarExtra) && (
        <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-1 flex-wrap items-center gap-3">
            <div className="relative min-w-[220px] flex-1 max-w-sm">
              <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white pr-9 pl-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none"
              />
            </div>

            {filterTabs && filterTabs.length > 0 && onFilterChange && (
              <div className="flex flex-wrap items-center gap-1.5">
                {filterTabs.map((tab) => {
                  const active = activeFilter === tab.value;
                  return (
                    <button
                      key={tab.value}
                      type="button"
                      onClick={() => {
                        setPage(1);
                        onFilterChange(tab.value);
                      }}
                      className={`h-9 whitespace-nowrap rounded-lg border px-3 text-xs font-medium transition-colors ${
                        active
                          ? "border-teal-700 bg-teal-700 text-white"
                          : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          {toolbarExtra && <div className="flex flex-wrap items-center gap-2">{toolbarExtra}</div>}
        </div>
      )}

      {isLoading ? (
        <LoadingState />
      ) : pagedRows.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-right text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600">
                <tr>
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      className={`whitespace-nowrap px-4 py-3 ${
                        col.align === "left"
                          ? "text-left"
                          : col.align === "center"
                          ? "text-center"
                          : "text-right"
                      }`}
                    >
                      {col.sortValue ? (
                        <button
                          type="button"
                          onClick={() => toggleSort(col.key)}
                          className="inline-flex items-center gap-1 font-semibold hover:text-slate-900"
                        >
                          <span>{col.header}</span>
                          <ArrowDownUp className="h-3.5 w-3.5 text-slate-400" />
                        </button>
                      ) : (
                        col.header
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {pagedRows.map((row) => (
                  <tr key={rowKey(row)} className="hover:bg-slate-50/70 transition-colors">
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={`px-4 py-3 align-middle text-slate-800 ${
                          col.align === "left"
                            ? "text-left"
                            : col.align === "center"
                            ? "text-center"
                            : "text-right"
                        }`}
                      >
                        {col.render(row)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-600">
              <span className="tabular-nums">
                نمایش {(safePage - 1) * pageSize + 1} تا{" "}
                {Math.min(safePage * pageSize, processed.length)} از {processed.length} مورد
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={safePage <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 font-medium text-slate-700 disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4" />
                  قبلی
                </button>
                <span className="tabular-nums px-2 font-semibold text-slate-800">
                  {safePage} / {totalPages}
                </span>
                <button
                  type="button"
                  disabled={safePage >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 font-medium text-slate-700 disabled:opacity-40"
                >
                  بعدی
                  <ChevronLeft className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
