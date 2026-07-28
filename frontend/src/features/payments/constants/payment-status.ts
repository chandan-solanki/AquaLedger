import type { StatusFilterOption } from "@/components/filters";
import type { PaymentStatus } from "@/features/payments/types/payment";

export const PAYMENT_STATUS_VALUES = [
  "draft",
  "posted",
  "cancelled",
] as const satisfies readonly PaymentStatus[];

export const PAYMENT_STATUS_OPTIONS: StatusFilterOption<PaymentStatus>[] = [
  { value: "draft", label: "Draft" },
  { value: "posted", label: "Posted" },
  { value: "cancelled", label: "Cancelled" },
];

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  draft: "Draft",
  posted: "Posted",
  cancelled: "Cancelled",
};

/**
 * Badge variant per status, mirroring `INVOICE_STATUS_BADGE_VARIANT`'s
 * pattern: `draft` (not yet committed - editable/deletable, see
 * app/modules/payments/service.py's `_ensure_draft`) reads as neutral/outline,
 * `posted` (the immutable, numbered financial record - the payments-module
 * counterpart of Invoice's `issued`) as the primary/active `default`, and
 * `cancelled` as `destructive`. There is no cancel endpoint yet
 * (app/modules/payments/router.py exposes no `/cancel` route this sprint),
 * so `cancelled` is unreachable through normal use today - the value still
 * exists in the backend's `PaymentStatus` enum and must be handled here.
 */
export const PAYMENT_STATUS_BADGE_VARIANT: Record<
  PaymentStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "outline",
  posted: "default",
  cancelled: "destructive",
};
