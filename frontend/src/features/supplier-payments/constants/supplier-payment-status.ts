import type { StatusFilterOption } from "@/components/filters";
import type { SupplierPaymentStatus } from "@/features/supplier-payments/types/supplier-payment";

export const SUPPLIER_PAYMENT_STATUS_VALUES = [
  "draft",
  "posted",
  "cancelled",
] as const satisfies readonly SupplierPaymentStatus[];

export const SUPPLIER_PAYMENT_STATUS_OPTIONS: StatusFilterOption<SupplierPaymentStatus>[] = [
  { value: "draft", label: "Draft" },
  { value: "posted", label: "Posted" },
  { value: "cancelled", label: "Cancelled" },
];

export const SUPPLIER_PAYMENT_STATUS_LABELS: Record<SupplierPaymentStatus, string> = {
  draft: "Draft",
  posted: "Posted",
  cancelled: "Cancelled",
};

/**
 * Badge variant per status, mirroring `PAYMENT_STATUS_BADGE_VARIANT`'s
 * pattern: `draft` (not yet committed, see
 * app/modules/supplier_payments/service.py's `_ensure_draft`) reads as
 * neutral/outline, `posted` (the immutable, numbered financial record) as
 * the primary/active `default`, and `cancelled` as `destructive`. There is
 * no cancel endpoint yet (app/modules/supplier_payments/router.py exposes no
 * `/cancel` route), so `cancelled` is unreachable through normal use today -
 * the value still exists in the backend's `SupplierPaymentStatus` enum and
 * must be handled here.
 */
export const SUPPLIER_PAYMENT_STATUS_BADGE_VARIANT: Record<
  SupplierPaymentStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "outline",
  posted: "default",
  cancelled: "destructive",
};
