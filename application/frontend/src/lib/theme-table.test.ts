// Path: frontend/src/lib/theme-table.test.ts

import test from "node:test";
import assert from "node:assert/strict";
import {
  isThemePreference,
  nextThemePreference,
  resolveTheme,
} from "./theme-utils";
import { buildExcelHtml, filterAndSortRows, serializeCsv } from "./table-utils";

test("resolveTheme handles light, dark, and system preferences accurately", () => {
  assert.equal(resolveTheme("light", true), "light");
  assert.equal(resolveTheme("dark", false), "dark");
  assert.equal(resolveTheme("system", true), "dark");
  assert.equal(resolveTheme("system", false), "light");
});

test("nextThemePreference cycles cleanly light -> dark -> system -> light", () => {
  assert.equal(nextThemePreference("light"), "dark");
  assert.equal(nextThemePreference("dark"), "system");
  assert.equal(nextThemePreference("system"), "light");
  assert.equal(isThemePreference("system"), true);
  assert.equal(isThemePreference("neon"), false);
});

test("filterAndSortRows filters by Persian/Latin query and sorts numerically", () => {
  const rows = [
    { id: "1", title: "برج باغ زعفرانیه", price: 320 },
    { id: "2", title: "واحد اداری جردن", price: 140 },
    { id: "3", title: "پنت‌هاوس فرشته", price: 480 },
  ];

  const filtered = filterAndSortRows(rows, { query: "زعفرانیه" });
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].id, "1");

  const sortedDesc = filterAndSortRows(rows, {
    sort: { key: "price", direction: "desc", getSortValue: (r) => r.price },
  });
  assert.deepEqual(
    sortedDesc.map((r) => r.id),
    ["3", "1", "2"]
  );
});

test("serializeCsv includes UTF-8 BOM and safely escapes quotes", () => {
  const csv = serializeCsv(
    [{ code: 'P-"101"', city: "تهران" }],
    [
      { key: "code", header: "کد", getExportValue: (r) => r.code },
      { key: "city", header: "شهر", getExportValue: (r) => r.city },
    ]
  );
  assert.ok(csv.startsWith("\uFEFF"));
  assert.ok(csv.includes('"P-""101"""'));
  assert.ok(csv.includes('"تهران"'));
});

test("buildExcelHtml generates RTL table HTML and escapes angle brackets", () => {
  const html = buildExcelHtml(
    [{ name: "<script>alert(1)</script>" }],
    [{ key: "name", header: "نام", getExportValue: (r) => r.name }],
    "خروجی"
  );
  assert.ok(html.includes('dir="rtl"'));
  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("&lt;script&gt;"));
});
