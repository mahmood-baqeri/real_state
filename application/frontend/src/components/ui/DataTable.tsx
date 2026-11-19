// Path: frontend/src/components/ui/DataTable.tsx

"use client";

import React, { useMemo, useState } from "react";
import {
  ArrowDownUp,
  ChevronLeft,
  ChevronRight,
  Columns3,
  Download,
  FileSpreadsheet,
  Search,
} from "lucide-react";
import {
  buildExcelHtml,
  filterAndSortRows,
  serializeCsv,
  type ExportColumn,
} from "@/lib/table-utils";
import { EmptyState, ErrorState, LoadingState } from "./StateNotice";

export interface ColumnDef<T> {
  key: string;
  header: string;
  align?: "right" | "left" | "center";
  sortValue?: (row: T) => string | number;
  exportValue?: (row: T) => string | number | boolean | null | undefined;
  defaultHidden?: boolean;
  mobileHidden?: boolean;
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
  searchableText?: (row: T) => string;
  filterTabs?: FilterTab[];
  activeFilter?: string;
  onFilterChange?: (val: string) => void;
  pageSize?: number;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  toolbarExtra?: React.ReactNode;
  selectable?: boolean;
  selectedKeys?: string[];
  onSelectionChange?: (keys: string[]) => void;
  bulkActions?: (selectedRows: T[], clearSelection: () => void) => React.ReactNode;
  exportFileName?: string;
  allowColumnToggle?: boolean;
  serverPagination?: {
    page: number;
    totalCount: number;
    onPageChange: (page: number) => void;
  };
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
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
  searchableText,
  filterTabs,
  activeFilter,
  onFilterChange,
  pageSize = 10,
  emptyTitle,
  emptyDescription,
  emptyAction,
  toolbarExtra,
  selectable = false,
  selectedKeys,
  onSelectionChange,
  bulkActions,
  exportFileName,
  allowColumnToggle = true,
  serverPagination,
}: DataTableProps<T>) {
  const [internalSearch, setInternalSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [hiddenCols, setHiddenCols] = useState<string[]>(() =>
    columns.filter((c) => c.defaultHidden).map((c) => c.key)
  );
  const [colsMenuOpen, setColsMenuOpen] = useState(false);
  const [internalSelected, setInternalSelected] = useState<string[]>([]);

  const activeSelection = selectedKeys !== undefined ? selectedKeys : internalSelected;
  const setSelection = (next: string[]) => {
    if (onSelectionChange) onSelectionChange(next);
    else setInternalSelected(next);
  };

  const query = searchValue !== undefined ? searchValue : internalSearch;
  const setQuery = (val: string) => {
    setPage(1);
    if (onSearchChange) onSearchChange(val);
    else setInternalSearch(val);
  };

  const visibleColumns = useMemo(
    () => columns.filter((c) => !hiddenCols.includes(c.key)),
    [columns, hiddenCols]
  );

  const processed = useMemo(() => {
    const colDef = sortCol ? columns.find((c) => c.key === sortCol) : undefined;
    return filterAndSortRows(rows, {
      query: searchValue === undefined ? query : "",
      searchableText,
      sort: colDef?.sortValue
        ? { key: colDef.key, direction: sortDir, getSortValue: colDef.sortValue }
        : null,
    });
  }, [rows, query, searchValue, searchableText, sortCol, sortDir, columns]);

  const isServerPaged = !!serverPagination;
  const totalCount = isServerPaged ? serverPagination.totalCount : processed.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const currentPage = isServerPaged ? serverPagination.page : Math.min(page, totalPages);
  const pagedRows = isServerPaged
    ? processed
    : processed.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const goPage = (nextPage: number) => {
    const clamped = Math.max(1, Math.min(totalPages, nextPage));
    if (isServerPaged) {
      serverPagination.onPageChange(clamped);
    } else {
      setPage(clamped);
    }
  };

  const toggleSort = (key: string) => {
    if (sortCol === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(key);
      setSortDir("asc");
    }
  };

  const toggleColumn = (key: string) => {
    setHiddenCols((prev) => {
      if (prev.includes(key)) return prev.filter((k) => k !== key);
      if (columns.length - prev.length <= 1) return prev;
      return [...prev, key];
    });
  };

  const pagedKeys = pagedRows.map((r) => rowKey(r));
  const allPageSelected =
    selectable && pagedKeys.length > 0 && pagedKeys.every((k) => activeSelection.includes(k));

  const toggleSelectAllPage = () => {
    if (allPageSelected) {
      setSelection(activeSelection.filter((k) => !pagedKeys.includes(k)));
    } else {
      setSelection(Array.from(new Set([...activeSelection, ...pagedKeys])));
    }
  };

  const toggleRow = (key: string) => {
    if (activeSelection.includes(key)) {
      setSelection(activeSelection.filter((k) => k !== key));
    } else {
      setSelection([...activeSelection, key]);
    }
  };

  const selectedRows = useMemo(
    () => rows.filter((r) => activeSelection.includes(rowKey(r))),
    [rows, activeSelection, rowKey]
  );

  const exportCols: ExportColumn<T>[] = useMemo(
    () =>
      visibleColumns
        .filter((c) => c.key !== "actions")
        .map((c) => ({
          key: c.key,
          header: c.header,
          getExportValue: (row: T) => {
            if (c.exportValue) return c.exportValue(row);
            if (c.sortValue) return c.sortValue(row);
            const raw = (row as Record<string, unknown>)?.[c.key];
            return raw === undefined || raw === null ? "" : String(raw);
          },
        })),
    [visibleColumns]
  );

  const handleExportCsv = () => {
    const csv = serializeCsv(processed, exportCols);
    triggerDownload(
      new Blob([csv], { type: "text/csv;charset=utf-8;" }),
      `${exportFileName || "bonyan-report"}.csv`
    );
  };

  const handleExportExcel = () => {
    const html = buildExcelHtml(processed, exportCols, exportFileName || "گزارش بنیان ملک");
    triggerDownload(
      new Blob([html], { type: "application/vnd.ms-excel;charset=utf-8;" }),
      `${exportFileName || "bonyan-report"}.xls`
    );
  };

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  return (
    <div className="space-y-4">
      {(onSearchChange !== undefined ||
        searchPlaceholder ||
        filterTabs ||
        toolbarExtra ||
        exportFileName ||
        allowColumnToggle) && (
        <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-1 flex-wrap items-center gap-3">
            <div className="relative min-w-[200px] flex-1 max-w-sm">
              <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                aria-label={searchPlaceholder}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white pr-9 pl-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-teal-500"
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
                          ? "border-teal-700 bg-teal-700 text-white dark:border-teal-500 dark:bg-teal-600"
                          : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-300 dark:hover:bg-slate-800"
                      }`}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {toolbarExtra}

            {exportFileName && processed.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={handleExportExcel}
                  title="خروجی اکسل (.xls)"
                  className="inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-700 dark:text-emerald-400" />
                  <span>اکسل</span>
                </button>
                <button
                  type="button"
                  onClick={handleExportCsv}
                  title="خروجی CSV"
                  className="inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  <Download className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                  <span>CSV</span>
                </button>
              </>
            )}

            {allowColumnToggle && columns.length > 3 && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setColsMenuOpen((o) => !o)}
                  aria-expanded={colsMenuOpen}
                  aria-label="تنظیم ستون‌های جدول"
                  className="inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  <Columns3 className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">ستون‌ها</span>
                </button>
                {colsMenuOpen && (
                  <div className="absolute left-0 top-11 z-30 w-52 rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                    <div className="mb-1 px-2 py-1 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                      نمایش ستون‌ها
                    </div>
                    <div className="max-h-60 space-y-1 overflow-y-auto">
                      {columns.map((c) => {
                        const checked = !hiddenCols.includes(c.key);
                        return (
                          <label
                            key={c.key}
                            className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleColumn(c.key)}
                              className="h-3.5 w-3.5 accent-teal-700"
                            />
                            <span className="truncate">{c.header}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {selectable && selectedRows.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50/80 px-4 py-2.5 text-xs dark:border-teal-800/70 dark:bg-teal-950/40">
          <span className="font-semibold text-teal-900 dark:text-teal-200 tabular-nums">
            {selectedRows.length} ردیف انتخاب شده است
          </span>
          <div className="flex flex-wrap items-center gap-2">
            {bulkActions?.(selectedRows, () => setSelection([]))}
            <button
              type="button"
              onClick={() => setSelection([])}
              className="rounded-lg border border-teal-300 bg-white px-3 py-1.5 font-medium text-teal-800 hover:bg-teal-50 dark:border-teal-700 dark:bg-slate-900 dark:text-teal-300"
            >
              لغو انتخاب
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <LoadingState />
      ) : pagedRows.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          {/* Mobile Card Layout (< md) */}
          <div className="divide-y divide-slate-200 dark:divide-slate-800 md:hidden">
            {pagedRows.map((row) => {
              const key = rowKey(row);
              const isSelected = activeSelection.includes(key);
              return (
                <div
                  key={key}
                  className={`space-y-2.5 p-4 ${
                    isSelected ? "bg-teal-50/40 dark:bg-teal-950/20" : ""
                  }`}
                >
                  {selectable && (
                    <label className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleRow(key)}
                        className="h-4 w-4 accent-teal-700"
                      />
                      <span>انتخاب ردیف</span>
                    </label>
                  )}
                  {visibleColumns
                    .filter((c) => !c.mobileHidden)
                    .map((col) => (
                      <div key={col.key} className="flex items-start justify-between gap-3 text-xs">
                        <span className="shrink-0 font-medium text-slate-500 dark:text-slate-400">
                          {col.header}:
                        </span>
                        <div className="min-w-0 text-left text-slate-900 dark:text-slate-100">
                          {col.render(row)}
                        </div>
                      </div>
                    ))}
                </div>
              );
            })}
          </div>

          {/* Desktop / Tablet Table (>= md) */}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full border-collapse text-right text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600 dark:border-slate-800 dark:bg-slate-800/70 dark:text-slate-300">
                <tr>
                  {selectable && (
                    <th className="w-10 px-4 py-3 text-center">
                      <input
                        type="checkbox"
                        checked={allPageSelected}
                        onChange={toggleSelectAllPage}
                        aria-label="انتخاب همه ردیف‌های این صفحه"
                        className="h-4 w-4 accent-teal-700"
                      />
                    </th>
                  )}
                  {visibleColumns.map((col) => (
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
                          className="inline-flex items-center gap-1 font-semibold hover:text-slate-900 dark:hover:text-white"
                        >
                          <span>{col.header}</span>
                          <ArrowDownUp className="h-3.5 w-3.5 text-slate-400 dark:text-slate-500" />
                        </button>
                      ) : (
                        col.header
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {pagedRows.map((row) => {
                  const key = rowKey(row);
                  const isSelected = activeSelection.includes(key);
                  return (
                    <tr
                      key={key}
                      className={`transition-colors hover:bg-slate-50/70 dark:hover:bg-slate-800/50 ${
                        isSelected ? "bg-teal-50/40 dark:bg-teal-950/20" : ""
                      }`}
                    >
                      {selectable && (
                        <td className="px-4 py-3 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleRow(key)}
                            aria-label="انتخاب ردیف"
                            className="h-4 w-4 accent-teal-700"
                          />
                        </td>
                      )}
                      {visibleColumns.map((col) => (
                        <td
                          key={col.key}
                          className={`px-4 py-3 align-middle text-slate-800 dark:text-slate-200 ${
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
                  );
                })}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-400">
              <span className="tabular-nums">
                نمایش {(currentPage - 1) * pageSize + 1} تا{" "}
                {Math.min(currentPage * pageSize, totalCount)} از {totalCount} مورد
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={currentPage <= 1}
                  onClick={() => goPage(currentPage - 1)}
                  className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 font-medium text-slate-700 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                >
                  <ChevronRight className="h-4 w-4" />
                  قبلی
                </button>
                <span className="tabular-nums px-2 font-semibold text-slate-800 dark:text-slate-200">
                  {currentPage} / {totalPages}
                </span>
                <button
                  type="button"
                  disabled={currentPage >= totalPages}
                  onClick={() => goPage(currentPage + 1)}
                  className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 font-medium text-slate-700 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
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
