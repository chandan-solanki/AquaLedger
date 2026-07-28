import { bffClient } from "@/lib/bff-client";
import type { BackendDashboardResponse, DashboardData } from "@/features/dashboard/types/dashboard";
import { mapBackendDashboard } from "@/features/dashboard/types/dashboard";

/**
 * Talks only to the Next.js BFF's own route (`/api/dashboard`) — never the
 * FastAPI backend directly, the same reason every other `*-service.ts` in
 * this app does (the browser never holds a bearer token to attach itself,
 * ARCHITECTURE.md §1.2, §8.1). The BFF route handler attaches the caller's
 * HttpOnly access token server-side and forwards the request.
 */
export const dashboardService = {
  async getDashboard(): Promise<DashboardData> {
    const { data } = await bffClient.get<BackendDashboardResponse>("/dashboard");
    return mapBackendDashboard(data);
  },
};
