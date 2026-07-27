import type { StatusFilterOption } from "@/components/filters";
import type { InvoiceStatus } from "@/features/invoices/types/invoice";

export const INVOICE_STATUS_VALUES = [
  "draft",
  "issued",
  "partially_paid",
  "paid",
  "cancelled",
] as const satisfies readonly InvoiceStatus[];

export const INVOICE_STATUS_OPTIONS: StatusFilterOption<InvoiceStatus>[] = [
  { value: "draft", label: "Draft" },
  { value: "issued", label: "Issued" },
  { value: "partially_paid", label: "Partially Paid" },
  { value: "paid", label: "Paid" },
  { value: "cancelled", label: "Cancelled" },
];

export const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: "Draft",
  issued: "Issued",
  partially_paid: "Partially Paid",
  paid: "Paid",
  cancelled: "Cancelled",
};

/**
 * Badge variant per status, mirroring `TRIP_STATUS_BADGE_VARIANT`'s pattern:
 * `draft` (not yet committed) reads as neutral/outline, `issued` (the active
 * working state) as the primary/active `default`, and `cancelled` as
 * `destructive`. `partially_paid`/`paid` both share `secondary` - the Badge
 * primitive has no dedicated "success" variant (`02_DESIGN_SYSTEM.md`'s
 * Status System), so both read as a resolving/resolved state, distinguished
 * by their label text rather than color. "overdue" is deliberately absent -
 * the backend defines it as derived (due_date < today AND balance_amount >
 * 0), never a stored status value (app/modules/invoices/constants.py).
 */
export const INVOICE_STATUS_BADGE_VARIANT: Record<
  InvoiceStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  draft: "outline",
  issued: "default",
  partially_paid: "secondary",
  paid: "secondary",
  cancelled: "destructive",
};
