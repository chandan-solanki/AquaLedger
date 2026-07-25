import { API_CONFIG } from "@/constants/app";
import { createHttpClient } from "@/lib/create-http-client";

/**
 * Client for the Next.js BFF's own route handlers (`/api/auth/*`) — the
 * only thing the browser talks to for authentication. No baseURL: requests
 * are same-origin, so the browser's session cookies are sent automatically
 * and no CORS configuration is needed.
 */
export const bffClient = createHttpClient({
  baseURL: "/api",
  timeout: API_CONFIG.timeoutMs,
  headers: {
    "Content-Type": "application/json",
  },
});
