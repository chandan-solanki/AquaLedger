import { bffClient } from "@/lib/bff-client";
import type { LoginRequest, LoginResponse } from "@/features/auth/types/auth";

/**
 * Talks only to the Next.js BFF's own routes (`/api/auth/*`) — never the
 * FastAPI backend directly, since the browser never holds a bearer token.
 */
export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const { data } = await bffClient.post<LoginResponse>("/auth/login", credentials);
    return data;
  },

  async logout(): Promise<void> {
    await bffClient.post("/auth/logout");
  },

  async getSession(): Promise<LoginResponse> {
    const { data } = await bffClient.get<LoginResponse>("/auth/session");
    return data;
  },
};
