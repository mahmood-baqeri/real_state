// تست‌های TypeScript را در یک پوشهٔ موقت کامپایل و اجرا می‌کند.
import { spawnSync } from "node:child_process";
import { mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const testDirectory = resolve("src/lib");
const tests = readdirSync(testDirectory).filter((name) => name.endsWith(".test.ts"));
if (!tests.length) throw new Error("هیچ فایل تستی پیدا نشد.");
const output = mkdtempSync(join(tmpdir(), "bonyan-unit-"));

/** فرایند Node را اجرا می‌کند و وضعیت خروج آن را به npm برمی‌گرداند. */
function runNode(args) {
  const result = spawnSync(process.execPath, args, { stdio: "inherit" });
  if (result.error) throw result.error;
  return result.status ?? 1;
}

try {
  process.exitCode = runNode([
    require.resolve("typescript/bin/tsc"),
    "--target", "ES2022", "--module", "commonjs", "--esModuleInterop",
    "--skipLibCheck", "--strict", "--rootDir", testDirectory, "--outDir", output,
    ...tests.map((name) => join(testDirectory, name)),
  ]);
  if (process.exitCode === 0) {
    process.exitCode = runNode(["--test", ...tests.map((name) => join(output, name.replace(/\.ts$/, ".js")))]);
  }
} finally {
  rmSync(output, { recursive: true, force: true });
}
