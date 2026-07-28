import { ArrowDownToLine, ArrowUpFromLine, Receipt, Route as RouteIcon, ShoppingCart } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { DashboardActivityType } from "@/features/dashboard/types/dashboard";

export const ACTIVITY_TYPE_LABELS: Record<DashboardActivityType, string> = {
  invoice: "Invoice",
  payment: "Payment",
  trip: "Trip",
  purchase_bill: "Purchase Bill",
  supplier_payment: "Supplier Payment",
};

export const ACTIVITY_TYPE_ICONS: Record<DashboardActivityType, LucideIcon> = {
  invoice: Receipt,
  payment: ArrowDownToLine,
  trip: RouteIcon,
  purchase_bill: ShoppingCart,
  supplier_payment: ArrowUpFromLine,
};

/**
 * Badge variant per activity type, grouped by money direction rather than
 * one color per type (`02_DESIGN_SYSTEM.md` §13's Status System spirit,
 * mirroring `TRIP_STATUS_BADGE_VARIANT`'s reasoning): revenue events
 * (invoice, payment) read as `default`, operational events (trip) as
 * `outline`, spend events (purchase bill, supplier payment) as `secondary`.
 */
export const ACTIVITY_TYPE_BADGE_VARIANT: Record<
  DashboardActivityType,
  "default" | "secondary" | "outline" | "destructive"
> = {
  invoice: "default",
  payment: "default",
  trip: "outline",
  purchase_bill: "secondary",
  supplier_payment: "secondary",
};
