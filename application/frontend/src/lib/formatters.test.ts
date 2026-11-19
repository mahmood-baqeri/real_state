// Path: frontend/src/lib/formatters.test.ts

import test from "node:test";
import assert from "node:assert/strict";
import {
  convertTomanRial,
  formatArea,
  formatLocalizedDate,
  formatMoney,
  translateStatus,
} from "./formatters";

test("convertTomanRial converts explicitly between IRT and IRR", () => {
  assert.equal(convertTomanRial(1000, "IRT", "IRR"), 10000);
  assert.equal(convertTomanRial(10000, "IRR", "IRT"), 1000);
  assert.equal(convertTomanRial("5000000", "IRT", "IRT"), 5000000);
});

test("formatMoney displays Persian formatted Toman and Rial labels", () => {
  const toman = formatMoney(2500000, "IRT", "IRT");
  assert.ok(toman.includes("تومان"));
  const rial = formatMoney(2500000, "IRT", "IRR");
  assert.ok(rial.includes("ریال"));
});

test("formatArea supports SQM and SQFT conversion", () => {
  assert.ok(formatArea(100, "SQM").includes("مترمربع"));
  assert.ok(formatArea(100, "SQFT").includes("فوت مربع"));
});

test("formatLocalizedDate formats Jalali and Gregorian calendars deterministically", () => {
  const iso = "2025-03-21T10:00:00Z";
  assert.equal(formatLocalizedDate(iso, "gregorian"), "2025-03-21");
  const jalali = formatLocalizedDate(iso, "jalali");
  assert.ok(jalali.length >= 8 && jalali !== "—");
});

test("translateStatus resolves Persian domain labels", () => {
  assert.equal(translateStatus("PUBLISHED"), "منتشرشده");
  assert.equal(translateStatus("CLOSED_WON"), "موفق / مختومه");
});
