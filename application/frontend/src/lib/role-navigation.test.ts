import test from "node:test";
import assert from "node:assert/strict";
import { getNavigationForUser, getRoleNavigationKeys, resolveEffectiveRole } from "./role-navigation";

test("resolveEffectiveRole maps platform and agency roles accurately", () => {
  assert.equal(resolveEffectiveRole("SUPER_ADMIN", null), "SUPER_ADMIN");
  assert.equal(resolveEffectiveRole("AGENCY_USER", "AGENCY_MANAGER"), "AGENCY_MANAGER");
  assert.equal(resolveEffectiveRole("AGENCY_USER", "AGENCY_ACCOUNTANT"), "AGENCY_ACCOUNTANT");
  assert.equal(resolveEffectiveRole("AGENCY_USER", "REAL_ESTATE_AGENT"), "AGENT");
  assert.equal(resolveEffectiveRole("CUSTOMER", null), "CUSTOMER");
});

test("RBAC navigation hides accounting and admin from agents and customers", () => {
  const agentKeys = getRoleNavigationKeys("AGENCY_USER", "REAL_ESTATE_AGENT");
  assert.ok(agentKeys.includes("properties"));
  assert.ok(agentKeys.includes("crm"));
  assert.ok(!agentKeys.includes("accounting"));
  assert.ok(!agentKeys.includes("admin"));

  const customerKeys = getRoleNavigationKeys("CUSTOMER", null);
  assert.deepEqual(customerKeys, ["overview", "appointments", "notifications", "profile"]);

  const mgrNav = getNavigationForUser("AGENCY_USER", "AGENCY_MANAGER", ["accounting.view"]);
  assert.ok(mgrNav.some((n) => n.key === "accounting"));
  assert.ok(mgrNav.some((n) => n.key === "roles"));
});
