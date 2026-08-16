import type { StatusFilterOption } from "@/components/filters";
import type { PurchaseOrderBillingStatus, PurchaseOrderStatus } from "@/features/purchase-orders/types/purchase-order";

export const PURCHASE_ORDER_STATUS_VALUES = [
  "draft",
  "confirmed",
  "fulfilled",
  "cancelled",
] as const satisfies readonly PurchaseOrderStatus[];

export const PURCHASE_ORDER_STATUS_OPTIONS: StatusFilterOption<PurchaseOrderStatus>[] = [
  { value: "draft", label: "Draft" },
  { value: "confirmed", label: "Confirmed" },
  { value: "fulfilled", label: "Fulfilled" },
  { value: "cancelled", label: "Cancelled" },
];

export const PURCHASE_ORDER_STATUS_LABELS: Record<PurchaseOrderStatus, string> = {
  draft: "Draft",
  confirmed: "Confirmed",
  fulfilled: "Fulfilled",
  cancelled: "Cancelled",
};

/**
 * Badge variant per status, mirroring `PURCHASE_BILL_STATUS_BADGE_VARIANT`'s
 * pattern: `draft` reads as neutral/outline, `confirmed` (the active
 * working state, this module's counterpart of Purchase Bill's `posted`) as
 * the primary/active `default`, `fulfilled` (terminal, no dedicated
 * "success" variant per `02_DESIGN_SYSTEM.md`'s Status System) as
 * `secondary`, and `cancelled` as `destructive`.
 */
export const PURCHASE_ORDER_STATUS_BADGE_VARIANT: Record<
  PurchaseOrderStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "outline",
  confirmed: "default",
  fulfilled: "secondary",
  cancelled: "destructive",
};

/**
 * Labels for the derived billing status (Sprint 12 Session 12) - distinct
 * from `PurchaseOrderStatus`: this describes billing progress, not the
 * procurement lifecycle, and is never stored (`app/modules/purchase_orders/
 * domain/billing.py`).
 */
export const PURCHASE_ORDER_BILLING_STATUS_LABELS: Record<PurchaseOrderBillingStatus, string> = {
  not_billed: "Not Billed",
  partially_billed: "Partially Billed",
  fully_billed: "Fully Billed",
};
