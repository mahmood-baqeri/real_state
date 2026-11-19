// Path: frontend/src/lib/table-utils.ts

export interface TableSortSpec<T> {
  key: string;
  direction: "asc" | "desc";
  getSortValue?: (row: T) => string | number | null | undefined;
}

export interface ExportColumn<T> {
  key: string;
  header: string;
  getExportValue: (row: T) => string | number | boolean | null | undefined;
}

export function filterAndSortRows<T>(
  rows: T[],
  options: {
    query?: string;
    searchableText?: (row: T) => string;
    sort?: TableSortSpec<T> | null;
  }
): T[] {
  let list = [...rows];
  const q = (options.query || "").trim().toLowerCase();
  if (q) {
    list = list.filter((item) => {
      const haystack = options.searchableText
        ? options.searchableText(item)
        : JSON.stringify(item);
      return haystack.toLowerCase().includes(q);
    });
  }

  if (options.sort?.getSortValue) {
    const fn = options.sort.getSortValue;
    const dir = options.sort.direction;
    list.sort((a, b) => {
      const va = fn(a) ?? "";
      const vb = fn(b) ?? "";
      if (typeof va === "number" && typeof vb === "number") {
        return dir === "asc" ? va - vb : vb - va;
      }
      const cmp = String(va).localeCompare(String(vb), "fa");
      return dir === "asc" ? cmp : -cmp;
    });
  }

  return list;
}

function escapeCsvCell(value: unknown): string {
  const raw = value === null || value === undefined ? "" : String(value);
  const escaped = raw.replace(/"/g, '""');
  return `"${escaped}"`;
}

export function serializeCsv<T>(rows: T[], columns: ExportColumn<T>[]): string {
  const headerLine = columns.map((c) => escapeCsvCell(c.header)).join(",");
  const bodyLines = rows.map((row) =>
    columns.map((c) => escapeCsvCell(c.getExportValue(row))).join(",")
  );
  // Prepend UTF-8 BOM for clean Persian rendering in Microsoft Excel
  return "\uFEFF" + [headerLine, ...bodyLines].join("\r\n");
}

function escapeHtml(value: unknown): string {
  const raw = value === null || value === undefined ? "" : String(value);
  return raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function buildExcelHtml<T>(
  rows: T[],
  columns: ExportColumn<T>[],
  sheetTitle = "گزارش"
): string {
  const ths = columns
    .map(
      (c) =>
        `<th style="background:#0f766e;color:#ffffff;font-weight:bold;padding:8px;border:1px solid #cbd5e1;">${escapeHtml(
          c.header
        )}</th>`
    )
    .join("");
  const trs = rows
    .map(
      (row) =>
        `<tr>${columns
          .map(
            (c) =>
              `<td style="padding:6px;border:1px solid #cbd5e1;">${escapeHtml(
                c.getExportValue(row)
              )}</td>`
          )
          .join("")}</tr>`
    )
    .join("");

  return `<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(sheetTitle)}</title>
</head>
<body>
<table dir="rtl" border="1" style="border-collapse:collapse;font-family:Tahoma,Arial,sans-serif;">
<thead><tr>${ths}</tr></thead>
<tbody>${trs}</tbody>
</table>
</body>
</html>`;
}
