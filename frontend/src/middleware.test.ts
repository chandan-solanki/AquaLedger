import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { middleware } from "@/middleware";

function makeRequest(path: string, { authenticated = false }: { authenticated?: boolean } = {}) {
  const headers: HeadersInit = authenticated ? { cookie: "al_access_token=test-token" } : {};
  return new NextRequest(new URL(path, "https://aqualedger.zenmediahouse.com"), { headers });
}

describe("middleware", () => {
  it("lets an unauthenticated visitor reach the public homepage", () => {
    const response = middleware(makeRequest("/"));
    expect(response.headers.get("location")).toBeNull();
  });

  it("lets an unauthenticated visitor reach the privacy policy", () => {
    const response = middleware(makeRequest("/privacy"));
    expect(response.headers.get("location")).toBeNull();
  });

  it("lets an authenticated visitor stay on the homepage instead of bouncing to /dashboard", () => {
    const response = middleware(makeRequest("/", { authenticated: true }));
    expect(response.headers.get("location")).toBeNull();
  });

  it("redirects an unauthenticated visitor away from a protected route to /login", () => {
    const response = middleware(makeRequest("/dashboard"));
    const location = response.headers.get("location");
    expect(location).not.toBeNull();
    expect(new URL(location!).pathname).toBe("/login");
  });

  it("still redirects an already-authenticated visitor away from /login to /dashboard", () => {
    const response = middleware(makeRequest("/login", { authenticated: true }));
    const location = response.headers.get("location");
    expect(location).not.toBeNull();
    expect(new URL(location!).pathname).toBe("/dashboard");
  });

  it("lets an unauthenticated visitor reach /login itself", () => {
    const response = middleware(makeRequest("/login"));
    expect(response.headers.get("location")).toBeNull();
  });
});
