import { memo } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { DashboardOperations } from "@/features/dashboard/types/dashboard";

interface DashboardOperationsCardProps {
  operations: DashboardOperations;
  className?: string;
}

interface StatRowProps {
  label: string;
  value: number;
  variant: "default" | "secondary" | "outline";
}

function StatRow({ label, value, variant }: StatRowProps) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <Badge variant={variant} className="tabular-nums">
        {value}
      </Badge>
    </div>
  );
}

/**
 * The Dashboard's Operations Row card — Trips and Boats side by side, each
 * a small status-badged stat list, per TASKS.md Sprint 10 Session 2's
 * "OPERATIONS CARD" spec. Every number is read straight from the backend's
 * `operations` section; nothing here derives `boats_available` or any
 * other figure itself (the backend already computed
 * `boats_available = active - at_sea`).
 */
function DashboardOperationsCardImpl({ operations, className }: DashboardOperationsCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Operations</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="space-y-3">
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Trips</h3>
            <div className="space-y-2">
              <StatRow label="Today" value={operations.tripsToday} variant="outline" />
              <StatRow label="Active" value={operations.tripsActive} variant="default" />
              <StatRow label="Completed Today" value={operations.tripsCompletedToday} variant="secondary" />
            </div>
          </div>

          <Separator className="sm:hidden" />

          <div className="space-y-3">
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Boats</h3>
            <div className="space-y-2">
              <StatRow label="Available" value={operations.boatsAvailable} variant="outline" />
              <StatRow label="At Sea" value={operations.boatsAtSea} variant="default" />
              <StatRow label="Maintenance" value={operations.boatsMaintenance} variant="secondary" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export const DashboardOperationsCard = memo(DashboardOperationsCardImpl);
