import { describe, expect, it } from "vitest";

import type { NavItem } from "@/config/navigation";
import { filterNavigation } from "@/utils/filter-navigation";
import { LayoutDashboard } from "lucide-react";

const NAV: NavItem[] = [
  {
    id: "dashboard",
    title: "Dashboard",
    icon: LayoutDashboard,
    href: "/dashboard",
    hiddenForPlatformAdmin: true,
  },
  {
    id: "masters",
    title: "Masters",
    icon: LayoutDashboard,
    children: [
      {
        id: "companies",
        title: "Companies",
        icon: LayoutDashboard,
        href: "/companies",
        permission: "company:view",
      },
    ],
  },
  {
    id: "platform",
    title: "Platform Administration",
    icon: LayoutDashboard,
    children: [
      {
        id: "platform-tenants",
        title: "Tenants",
        icon: LayoutDashboard,
        href: "/platform/tenants",
        platformOnly: true,
      },
    ],
  },
];

function findGroup(items: NavItem[], id: string) {
  return items.find((item) => item.id === id);
}

describe("filterNavigation - Platform Administration gating", () => {
  it("hides the Platform Administration group for an ordinary user with no permissions", () => {
    const result = filterNavigation(NAV, [], false, false);
    expect(findGroup(result, "platform")).toBeUndefined();
  });

  it("hides the Platform Administration group for a tenant superuser", () => {
    // isSuperuser=true, isPlatformAdmin=false - the superuser bypass must
    // NOT substitute for platform-admin identity (Sprint 17's explicit boundary).
    const result = filterNavigation(NAV, [], true, false);
    expect(findGroup(result, "platform")).toBeUndefined();
  });

  it("hides the Platform Administration group even when the user holds every ordinary permission", () => {
    const result = filterNavigation(NAV, ["company:view", "user:manage", "audit_log:view"], false, false);
    expect(findGroup(result, "platform")).toBeUndefined();
  });

  it("shows the Platform Administration group only when isPlatformAdmin is true", () => {
    const result = filterNavigation(NAV, [], false, true);
    const group = findGroup(result, "platform");
    expect(group).toBeDefined();
    expect(group?.children?.map((c) => c.id)).toEqual(["platform-tenants"]);
  });

  it("keeps ordinary permission-gated groups working unaffected by isPlatformAdmin", () => {
    const asPlatformAdminOnly = filterNavigation(NAV, [], false, true);
    expect(findGroup(asPlatformAdminOnly, "masters")).toBeUndefined();

    const withCompanyPermission = filterNavigation(NAV, ["company:view"], false, true);
    expect(findGroup(withCompanyPermission, "masters")).toBeDefined();
  });

  it("defaults isPlatformAdmin to false when omitted", () => {
    const result = filterNavigation(NAV, [], false);
    expect(findGroup(result, "platform")).toBeUndefined();
  });
});

describe("filterNavigation - hiddenForPlatformAdmin", () => {
  it("hides the ordinary tenant Dashboard item for a platform admin", () => {
    const result = filterNavigation(NAV, [], false, true);
    expect(findGroup(result, "dashboard")).toBeUndefined();
  });

  it("keeps showing the ordinary tenant Dashboard item to every non-platform-admin user", () => {
    const asOrdinaryUser = filterNavigation(NAV, [], false, false);
    const asSuperuser = filterNavigation(NAV, [], true, false);
    expect(findGroup(asOrdinaryUser, "dashboard")).toBeDefined();
    expect(findGroup(asSuperuser, "dashboard")).toBeDefined();
  });
});
