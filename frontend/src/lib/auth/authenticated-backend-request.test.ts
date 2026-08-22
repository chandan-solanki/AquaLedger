import { beforeEach, describe, expect, it, vi } from "vitest";

// Next.js aliases this to a no-op in a Server Component bundle; outside
// that bundler it throws unconditionally, so every test of a server-only
// module needs this stub (none of this module's siblings had a unit test
// before Sprint 16 Session 3).
vi.mock("server-only", () => ({}));

// `env.ts` validates process.env at import time and throws if the
// NEXT_PUBLIC_* vars aren't set - fine for the app (Next.js always
// provides them) but not for a unit test process, so it's mocked outright
// rather than relying on a particular .env file being loaded.
vi.mock("@/config/env", () => ({
  env: { NEXT_PUBLIC_API_URL: "http://backend.test/api/v1" },
}));

const {
  getAccessTokenMock,
  getRefreshTokenMock,
  getRememberMeMock,
  setSessionCookiesMock,
  clearSessionCookiesMock,
  backendRefreshMock,
} = vi.hoisted(() => ({
  getAccessTokenMock: vi.fn(),
  getRefreshTokenMock: vi.fn(),
  getRememberMeMock: vi.fn(),
  setSessionCookiesMock: vi.fn(),
  clearSessionCookiesMock: vi.fn(),
  backendRefreshMock: vi.fn(),
}));

vi.mock("@/lib/auth/session-cookies", () => ({
  getAccessToken: getAccessTokenMock,
  getRefreshToken: getRefreshTokenMock,
  getRememberMe: getRememberMeMock,
  setSessionCookies: setSessionCookiesMock,
  clearSessionCookies: clearSessionCookiesMock,
}));

vi.mock("@/lib/auth/backend-auth-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth/backend-auth-client")>(
    "@/lib/auth/backend-auth-client"
  );
  return { ...actual, backendRefresh: backendRefreshMock };
});

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => {
  vi.clearAllMocks();
  getAccessTokenMock.mockResolvedValue("initial-access-token");
  getRefreshTokenMock.mockResolvedValue("some-refresh-token");
  getRememberMeMock.mockResolvedValue(false);
});

describe("authenticatedBackendRequest - 401 handling", () => {
  it("throws immediately on INVALID_CREDENTIALS without refreshing or clearing the session", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(401, { error: { code: "INVALID_CREDENTIALS", message: "Current password is incorrect" } })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      authenticatedBackendRequest("/auth/change-password", {
        method: "POST",
        body: { current_password: "wrong", new_password: "NewStrong@1" },
      })
    ).rejects.toMatchObject({ apiError: { code: "INVALID_CREDENTIALS" } });

    // Exactly one call - the original request. No refresh attempted, no
    // cookies touched: a wrong current_password says nothing about whether
    // this session's tokens are still valid.
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(backendRefreshMock).not.toHaveBeenCalled();
    expect(clearSessionCookiesMock).not.toHaveBeenCalled();

    vi.unstubAllGlobals();
  });

  it("still refreshes and retries on a genuinely expired/invalid access token", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: "EXPIRED_TOKEN", message: "Access token has expired" } }))
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    backendRefreshMock.mockResolvedValue({
      access_token: "new-access-token",
      refresh_token: "new-refresh-token",
      expires_in: 900,
      must_change_password: false,
      user: {},
    });

    const result = await authenticatedBackendRequest("/profile", { method: "PUT", body: { full_name: "Jane" } });

    expect(result).toEqual({ ok: true });
    expect(backendRefreshMock).toHaveBeenCalledWith("some-refresh-token");
    expect(setSessionCookiesMock).toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    vi.unstubAllGlobals();
  });

  it("clears the session when the retried request also fails after a real token refresh", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: "INVALID_TOKEN", message: "Access token is invalid" } }))
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: "ACCOUNT_DISABLED", message: "This account has been disabled" } }));
    vi.stubGlobal("fetch", fetchMock);
    backendRefreshMock.mockResolvedValue({
      access_token: "new-access-token",
      refresh_token: "new-refresh-token",
      expires_in: 900,
      must_change_password: false,
      user: {},
    });

    await expect(authenticatedBackendRequest("/profile", { method: "PUT", body: {} })).rejects.toMatchObject({
      apiError: { code: "ACCOUNT_DISABLED" },
    });

    expect(clearSessionCookiesMock).toHaveBeenCalled();

    vi.unstubAllGlobals();
  });
});
