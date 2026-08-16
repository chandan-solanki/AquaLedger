import { z } from "zod";

import type {
  PurchaseOrderItem,
  PurchaseOrderItemCreateRequest,
  PurchaseOrderItemUpdateRequest,
} from "@/features/purchase-orders/types/purchase-order-item";

// Mirrors the backend's exact checks (app/modules/purchase_orders/schemas.py)
// so the form never rejects something the backend would accept, or vice
// versa - byte-identical to `purchaseBillItemFormSchema`'s own constraints.
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
 * Field names are snake_case, matching PurchaseOrderItemCreateRequest/
 * PurchaseOrderItemUpdateRequest exactly (app/modules/purchase_orders/
 * schemas.py) - so `mapServerErrorsToForm` can set a 422's `field_errors`
 * directly onto the right RHF field with no translation layer, mirroring
 * `purchaseBillItemFormSchema`.
 *
 * There is no `fish_id`/`trip_catch_id` - a purchase order line has no
 * link to a sold-fish master or a trip catch, so this form is a plain set
 * of fields with no selector. **`description` is required** here - the
 * backend's own `PurchaseOrderItemCreateRequest` requires it
 * (`min_length=1`), even though the underlying column stays nullable.
 *
 * No `discount_amount`/`taxable_amount`/`tax_amount`/`line_total` fields
 * here - every one of those is server-computed and never accepted on
 * create/update; they are read-only, rendered only in
 * `PurchaseOrderItemTable`'s columns from the server's own response.
 */
export const purchaseOrderItemFormSchema = z.object({
  description: z.string().trim().min(1, "Description is required"),
  quantity: quantityField,
  unit: z.string().trim().min(1, "Unit is required").max(20, "Must be 20 characters or fewer"),
  rate: rateField,
  discount_percent: percentField,
  tax_rate: percentField,
});

export type PurchaseOrderItemFormValues = z.infer<typeof purchaseOrderItemFormSchema>;

export const DEFAULT_PURCHASE_ORDER_ITEM_FORM_VALUES: PurchaseOrderItemFormValues = {
  description: "",
  quantity: "",
  unit: "",
  rate: "",
  discount_percent: "",
  tax_rate: "",
};

/** Populates the form from a fetched `PurchaseOrderItem` for the Edit dialog - null fields become empty strings. */
export function toPurchaseOrderItemFormValues(item: PurchaseOrderItem): PurchaseOrderItemFormValues {
  return {
    description: item.description ?? "",
    quantity: item.quantity,
    unit: item.unit,
    rate: item.rate,
    discount_percent: item.discountPercent,
    tax_rate: item.taxRate,
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults rather than writing empty strings. */
export function toPurchaseOrderItemRequestPayload(
  values: PurchaseOrderItemFormValues
): PurchaseOrderItemCreateRequest {
  return {
    description: values.description,
    quantity: values.quantity,
    unit: values.unit,
    rate: values.rate,
    discount_percent: values.discount_percent || undefined,
    tax_rate: values.tax_rate || undefined,
  };
}

/** Same shape as `toPurchaseOrderItemRequestPayload` - a fully-populated `PurchaseOrderItemCreateRequest` is always a valid partial `PurchaseOrderItemUpdateRequest`. */
export function toPurchaseOrderItemUpdatePayload(
  values: PurchaseOrderItemFormValues
): PurchaseOrderItemUpdateRequest {
  return toPurchaseOrderItemRequestPayload(values);
}
