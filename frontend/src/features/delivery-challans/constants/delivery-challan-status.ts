import type { StatusFilterOption } from "@/components/filters";
import type { DeliveryChallanStatus } from "@/features/delivery-challans/types/delivery-challan";

export const DELIVERY_CHALLAN_STATUS_VALUES = [
  "draft",
  "dispatched",
  "delivered",
  "cancelled",
] as const satisfies readonly DeliveryChallanStatus[];

export const DELIVERY_CHALLAN_STATUS_OPTIONS: StatusFilterOption<DeliveryChallanStatus>[] = [
  { value: "draft", label: "Draft" },
  { value: "dispatched", label: "Dispatched" },
  { value: "delivered", label: "Delivered" },
  { value: "cancelled", label: "Cancelled" },
];

export const DELIVERY_CHALLAN_STATUS_LABELS: Record<DeliveryChallanStatus, string> = {
  draft: "Draft",
  dispatched: "Dispatched",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

/**
 * Badge variant per status, mirroring `PURCHASE_ORDER_STATUS_BADGE_VARIANT`'s
 * pattern exactly: `draft` reads as neutral/outline, `dispatched` (the
 * active in-transit state, this module's counterpart of Purchase Order's
 * `confirmed`) as the primary/active `default`, `delivered` (terminal, no
 * dedicated "success" variant per `02_DESIGN_SYSTEM.md`'s Status System) as
 * `secondary`, and `cancelled` as `destructive`.
 */
export const DELIVERY_CHALLAN_STATUS_BADGE_VARIANT: Record<
  DeliveryChallanStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "outline",
  dispatched: "default",
  delivered: "secondary",
  cancelled: "destructive",
};
