import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const project = process.cwd();
const output = mkdtempSync(join(tmpdir(), "bonyan-frontend-tests-"));
const tsc = process.platform === "win32" ? "tsc.cmd" : "tsc";
const compile = spawnSync(
  tsc,
  [
    "--target", "ES2022",
    "--module", "commonjs",
    "--moduleResolution", "node",
    "--esModuleInterop",
    "--skipLibCheck",
    "--strict",
    "--outDir", output,
    "src/lib/formatters.test.ts",
    "src/lib/role-navigation.test.ts",
    "src/lib/theme-table.test.ts",
  ],
  { cwd: project, stdio: "inherit", shell: process.platform === "win32" }
);
if (compile.status !== 0) {
  rmSync(output, { recursive: true, force: true });
  process.exit(compile.status ?? 1);
}
const run = spawnSync(
  process.execPath,
  ["--test", join(output, "formatters.test.js"), join(output, "role-navigation.test.js"), join(output, "theme-table.test.js")],
  { cwd: project, stdio: "inherit" }
);
rmSync(output, { recursive: true, force: true });
process.exit(run.status ?? 1);
