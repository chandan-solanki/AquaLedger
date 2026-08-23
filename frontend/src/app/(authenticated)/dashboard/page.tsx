import { TenantDashboardGuard } from "@/features/dashboard/components/tenant-dashboard-guard";
import { DashboardPage } from "@/features/dashboard/pages/dashboard-page";

export default function Page() {
  return (
    <TenantDashboardGuard>
      <DashboardPage />
    </TenantDashboardGuard>
  );
}
