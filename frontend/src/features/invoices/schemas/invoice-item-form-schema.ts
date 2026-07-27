import { z } from "zod";

import type {
  InvoiceItem,
  InvoiceItemCreateRequest,
  InvoiceItemUpdateRequest,
} from "@/features/invoices/types/invoice-item";

// Mirrors the backend's exact checks (app/modules/invoices/schemas.py) so
// the form never rejects something the backend would accept, or vice versa.
// quantity: Decimal, max_digits=12, decimal_places=3, gt=0.
const QUANTITY_PATTERN = /^\d{1,9}(\.\d{1,3})?$/;
// rate: Decimal, max_digits=12, decimal_places=4, ge=0.
const RATE_PATTERN = /^\d{1,8}(\.\d{1,4})?$/;
// discount_percent/tax_rate: Decimal, max_digits=5, decimal_places=2, 0-100.
const PERCENT_PATTERN = /^\d{1,3}(\.\d{1,2})?$/;

const quantityField = z
  .string()
  .trim()
  .min(1, "Quantity is required")
  .refine((value) => QUANTITY_PATTERN.test(value), "Enter a valid quantity (up to 3 decimal places)")
  .refine((value) => Number(value) > 0, "Must be greater than 0");

const rateField = z
  .string()
  .trim()
  .min(1, "Rate is required")
  .refine((value) => RATE_PATTERN.test(value), "Enter a valid rate (up to 4 decimal places)")
  .refine((value) => Number(value) >= 0, "Must be 0 or more");

const percentField = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || PERCENT_PATTERN.test(value),
    "Enter a valid percentage (up to 2 decimal places)"
  )
  .refine((value) => value === "" || Number(value) <= 100, "Must be 100 or less");

/**
 * Field names are snake_case, matching InvoiceItemCreateRequest/
 * InvoiceItemUpdateRequest exactly (app/modules/invoices/schemas.py) - so
 * `mapServerErrorsToForm` can set a 422's `field_errors` directly onto the
 * right RHF field with no translation layer, mirroring `tripCatchFormSchema`.
 *
 * `fish_id` is in this schema (the backend requires it) but is never its
 * own visible field in `InvoiceItemForm` - it is always set together with
 * `trip_catch_id` by the Trip Catch selector, since the backend requires
 * the two to match (422 `INVOICE_ITEM_FISH_MISMATCH` otherwise) - "Trip
 * Catch is the business source" (TASKS.md).
 *
 * No `discount_amount`/`taxable_amount`/`tax_amount`/`line_total` fields
 * here - every one of those is server-computed and never accepted on
 * create/update; they are read-only, rendered only in
 * `InvoiceItemTable`'s columns from the server's own response.
 */
export const invoiceItemFormSchema = z.object({
  trip_catch_id: z.string().trim().min(1, "Trip catch is required"),
  fish_id: z.string().trim().min(1, "Fish is required"),
  description: z.string().trim(),
  quantity: quantityField,
  unit: z.string().trim().min(1, "Unit is required").max(20, "Must be 20 characters or fewer"),
  rate: rateField,
  discount_percent: percentField,
  tax_rate: percentField,
});

export type InvoiceItemFormValues = z.infer<typeof invoiceItemFormSchema>;

export const DEFAULT_INVOICE_ITEM_FORM_VALUES: InvoiceItemFormValues = {
  trip_catch_id: "",
  fish_id: "",
  description: "",
  quantity: "",
  unit: "",
  rate: "",
  discount_percent: "",
  tax_rate: "",
};

/** Populates the form from a fetched `InvoiceItem` for the Edit dialog - null fields become empty strings. */
export function toInvoiceItemFormValues(item: InvoiceItem): InvoiceItemFormValues {
  return {
    trip_catch_id: item.tripCatchId ?? "",
    fish_id: item.fishId,
    description: item.description ?? "",
    quantity: item.quantity,
    unit: item.unit,
    rate: item.rate,
    discount_percent: item.discountPercent,
    tax_rate: item.taxRate,
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults rather than writing empty strings. */
export function toInvoiceItemRequestPayload(values: InvoiceItemFormValues): InvoiceItemCreateRequest {
  return {
    trip_catch_id: values.trip_catch_id,
    fish_id: values.fish_id,
    description: values.description || undefined,
    quantity: values.quantity,
    unit: values.unit,
    rate: values.rate,
    discount_percent: values.discount_percent || undefined,
    tax_rate: values.tax_rate || undefined,
  };
}

/** Same shape as `toInvoiceItemRequestPayload` - a fully-populated `InvoiceItemCreateRequest` is always a valid partial `InvoiceItemUpdateRequest`. */
export function toInvoiceItemUpdatePayload(values: InvoiceItemFormValues): InvoiceItemUpdateRequest {
  return toInvoiceItemRequestPayload(values);
}
