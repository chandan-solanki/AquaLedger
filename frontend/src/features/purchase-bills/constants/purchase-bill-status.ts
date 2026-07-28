import type { StatusFilterOption } from "@/components/filters";
import type { PurchaseBillStatus } from "@/features/purchase-bills/types/purchase-bill";

export const PURCHASE_BILL_STATUS_VALUES = [
  "draft",
  "posted",
  "partially_paid",
  "paid",
  "cancelled",
] as const satisfies readonly PurchaseBillStatus[];

export const PURCHASE_BILL_STATUS_OPTIONS: StatusFilterOption<PurchaseBillStatus>[] = [
  { value: "draft", label: "Draft" },
  { value: "posted", label: "Posted" },
  { value: "partially_paid", label: "Partially Paid" },
  { value: "paid", label: "Paid" },
  { value: "cancelled", label: "Cancelled" },
];

export const PURCHASE_BILL_STATUS_LABELS: Record<PurchaseBillStatus, string> = {
  draft: "Draft",
  posted: "Posted",
  partially_paid: "Partially Paid",
  paid: "Paid",
  cancelled: "Cancelled",
};

/**
 * Badge variant per status, mirroring `INVOICE_STATUS_BADGE_VARIANT`'s
 * pattern exactly: `draft` reads as neutral/outline, `posted` (the active
 * working state, Purchase Bill's counterpart of Invoice's `issued`) as the
 * primary/active `default`, `partially_paid`/`paid` both share `secondary`
 * (no dedicated "success" variant, per `02_DESIGN_SYSTEM.md`'s Status
 * System), and `cancelled` as `destructive`.
 */
export const PURCHASE_BILL_STATUS_BADGE_VARIANT: Record<
  PurchaseBillStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "outline",
  posted: "default",
  partially_paid: "secondary",
  paid: "secondary",
  cancelled: "destructive",
};
