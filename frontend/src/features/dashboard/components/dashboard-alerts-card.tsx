import { memo, useMemo } from "react";

import { AlertsCard } from "@/components/dashboard/AlertsCard";
import type { AlertsCardItem } from "@/components/dashboard/AlertsCard";
import { ALERT_TYPE_ICONS, ALERT_TYPE_SEVERITY } from "@/features/dashboard/constants/alert-type";
import type { DashboardAlert } from "@/features/dashboard/types/dashboard";

interface DashboardAlertsCardProps {
  alerts: DashboardAlert[];
  className?: string;
}

/**
 * Adapts the backend's `alerts` array (already backend-computed counts and
 * messages — never invented client-side, per TASKS.md Sprint 10 Session 1's
 * "Only include real backend-supported alerts") into the shared
 * `AlertsCard` primitive's item shape, attaching a per-type icon and
 * severity tier for the "priority colors" spec requirement.
 */
function DashboardAlertsCardImpl({ alerts, className }: DashboardAlertsCardProps) {
  const items = useMemo<AlertsCardItem[]>(
    () =>
      alerts.map((alert) => ({
        id: alert.type,
        message: alert.message,
        count: alert.count,
        icon: ALERT_TYPE_ICONS[alert.type],
        severity: ALERT_TYPE_SEVERITY[alert.type],
      })),
    [alerts]
  );

  return (
    <AlertsCard title="Alerts" items={items} className={className} />
  );
}

export const DashboardAlertsCard = memo(DashboardAlertsCardImpl);
