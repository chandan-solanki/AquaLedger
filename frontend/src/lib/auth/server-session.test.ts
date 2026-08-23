import { describe, expect, it, vi } from "vitest";

// Next.js aliases this to a no-op in a Server Component bundle; outside
// that bundler it throws unconditionally (see authenticated-backend-request.test.ts).
vi.mock("server-only", () => ({}));

// backend-auth-client.ts imports config/env.ts, which validates process.env
// at import time - not set in the test process, so it's mocked outright
// rather than relying on a particular .env file being loaded.
vi.mock("@/config/env", () => ({
  env: { NEXT_PUBLIC_API_URL: "http://backend.test/api/v1" },
}));

// session-cookies.ts imports next/headers - only `cookies()` itself needs a
// request scope, but the import must still resolve in a plain Vitest run.
vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

import { mapUserProfile } from "@/lib/auth/server-session";
import type { BackendUserProfile } from "@/lib/auth/backend-auth-client";

const BASE_PROFILE: BackendUserProfile = {
  id: "user-1",
  tenant_id: "tenant-1",
  email: "admin@fisherp.local",
  username: "admin",
  full_name: "Super Admin",
  phone: null,
  status: "active",
  is_superuser: true,
  is_platform_admin: false,
  last_login_at: null,
  roles: ["admin"],
  permissions: ["user:manage"],
  avatar_url: null,
};

describe("mapUserProfile - is_platform_admin propagation", () => {
  it("maps is_platform_admin: false onto isPlatformAdmin", () => {
    const user = mapUserProfile(BASE_PROFILE);
    expect(user.isPlatformAdmin).toBe(false);
  });

  it("maps is_platform_admin: true onto isPlatformAdmin", () => {
    const user = mapUserProfile({ ...BASE_PROFILE, is_platform_admin: true });
    expect(user.isPlatformAdmin).toBe(true);
  });

  it("keeps isPlatformAdmin independent of isSuperuser", () => {
    const user = mapUserProfile({ ...BASE_PROFILE, is_superuser: true, is_platform_admin: false });
    expect(user.isSuperuser).toBe(true);
    expect(user.isPlatformAdmin).toBe(false);
  });
});
