import { describe, expect, it } from "vitest";

import { NAVIGATION } from "@/config/navigation";
import { filterNavigation } from "@/utils/filter-navigation";

/**
 * Sprint 17 Session 5 - confirms the real NAVIGATION config (not a test
 * fixture) gives a platform admin both the new landing Dashboard and the
 * existing Tenants page, and that neither ever appears for anyone else.
 * `filter-navigation.test.ts` already covers the generic `platformOnly`
 * gating mechanism against a fixture tree - this is the "did we actually
 * wire the real config correctly" check.
 */
describe("NAVIGATION - Platform Administration group", () => {
  it("gives a platform admin both Dashboard and Tenants, in that order", () => {
    const result = filterNavigation(NAVIGATION, [], false, true);
    const platformGroup = result.find((item) => item.id === "platform");

    expect(platformGroup?.children?.map((child) => child.href)).toEqual([
      "/platform/dashboard",
      "/platform/tenants",
    ]);
  });

  it("never shows the Platform Administration group to an ordinary tenant user, even a superuser", () => {
    const asOrdinaryUser = filterNavigation(NAVIGATION, [], false, false);
    const asSuperuser = filterNavigation(NAVIGATION, [], true, false);

    expect(asOrdinaryUser.find((item) => item.id === "platform")).toBeUndefined();
    expect(asSuperuser.find((item) => item.id === "platform")).toBeUndefined();
  });

  it("hides the redundant, redirect-only tenant Dashboard item for a platform admin", () => {
    const asPlatformAdmin = filterNavigation(NAVIGATION, [], false, true);
    expect(asPlatformAdmin.find((item) => item.id === "dashboard")).toBeUndefined();
  });

  it("keeps the tenant Dashboard item visible for every ordinary tenant user", () => {
    const asOrdinaryUser = filterNavigation(NAVIGATION, [], false, false);
    const asSuperuser = filterNavigation(NAVIGATION, [], true, false);

    expect(asOrdinaryUser.find((item) => item.id === "dashboard")).toBeDefined();
    expect(asSuperuser.find((item) => item.id === "dashboard")).toBeDefined();
  });
});
