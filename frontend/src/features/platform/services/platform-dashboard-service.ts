import { bffClient } from "@/lib/bff-client";
import type { BackendPlatformDashboard, PlatformDashboardData } from "@/features/platform/types/platform-dashboard";
import { mapBackendPlatformDashboard } from "@/features/platform/types/platform-dashboard";

/**
 * Talks only to the Next.js BFF's own route (`/api/platform/dashboard`) —
 * never the FastAPI backend directly, same rationale as `tenant-service.ts`.
 */
export const platformDashboardService = {
  async getDashboard(): Promise<PlatformDashboardData> {
    const { data } = await bffClient.get<BackendPlatformDashboard>("/platform/dashboard");
    return mapBackendPlatformDashboard(data);
  },
};
