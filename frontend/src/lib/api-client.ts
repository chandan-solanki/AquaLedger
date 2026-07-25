import { env } from "@/config/env";
import { API_CONFIG } from "@/constants/app";
import { createHttpClient } from "@/lib/create-http-client";

/**
 * Direct client for the FastAPI backend. Reserved for future business-data
 * fetching (Sprint 3+) — authentication does NOT use this client, since the
 * browser never holds a bearer token to attach here (07_FRONTEND_ARCHITECTURE.md
 * §8, §20). How this client authenticates its requests once business
 * features start using it is a follow-up decision for those sprints.
 */
export const apiClient = createHttpClient({
  baseURL: env.NEXT_PUBLIC_API_URL,
  timeout: API_CONFIG.timeoutMs,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  // Placeholder attachment point: once business features wire this client
  // to the backend, this resolves the current auth context here. No-op for
  // now — auth calls go through lib/bff-client.ts instead.
  return config;
});
