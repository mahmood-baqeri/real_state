/** Minimal declarations for the Node test APIs used by these small TS test files.
 * The production application still uses @types/node from the normal dependency set.
 * This keeps the standalone test runner usable in stripped/offline environments.
 */
declare module "node:test" {
  export default function test(name: string, fn: () => void | Promise<void>): void;
}
declare module "node:assert/strict" {
  const assert: {
    equal(actual: unknown, expected: unknown, message?: string): void;
    ok(value: unknown, message?: string): asserts value;
    deepEqual(actual: unknown, expected: unknown, message?: string): void;
  };
  export default assert;
}
