import { z } from "zod";

import type {
  PurchaseOrder,
  PurchaseOrderCreateRequest,
  PurchaseOrderUpdateRequest,
} from "@/features/purchase-orders/types/purchase-order";

/**
 * Field names are snake_case, matching PurchaseOrderCreateRequest/
 * PurchaseOrderUpdateRequest exactly (app/modules/purchase_orders/
 * schemas.py) - so `mapServerErrorsToForm` can set a 422's `field_errors`
 * directly onto the right RHF field with no translation layer, mirroring
 * `purchaseBillFormSchema`.
 *
 * This is the header-only form - there is no `po_number` field (server-
 * assigned only at confirm, never client-supplied) and no `status` field
 * (always DRAFT at creation, and `PurchaseOrderUpdateRequest` never accepts
 * it either). There are no financial fields, transport/other charge
 * fields, line items, or totals here either - every financial field starts
 * at 0 and is computed once line items exist; items are a separate
 * sub-resource.
 *
 * `order_date`/`expected_delivery_date` are kept as ISO date strings
 * (`yyyy-MM-dd`) here rather than `Date` objects - `PurchaseOrderForm`
 * converts to/from `Date` at the `DatePicker` boundary, mirroring
 * `purchaseBillFormSchema`.
 */
export const purchaseOrderFormSchema = z.object({
  supplier_id: z.string().trim().min(1, "Supplier is required"),
  order_date: z.string().trim().min(1, "PO date is required"),
  expected_delivery_date: z.string().trim(),
  remarks: z.string().trim(),
});

export type PurchaseOrderFormValues = z.infer<typeof purchaseOrderFormSchema>;

export const DEFAULT_PURCHASE_ORDER_FORM_VALUES: PurchaseOrderFormValues = {
  supplier_id: "",
  order_date: "",
  expected_delivery_date: "",
  remarks: "",
};

/** Populates the form from a fetched `PurchaseOrder` for the Edit page - null fields become empty strings. */
export function toPurchaseOrderFormValues(order: PurchaseOrder): PurchaseOrderFormValues {
  return {
    supplier_id: order.supplierId,
    order_date: order.orderDate,
    expected_delivery_date: order.expectedDeliveryDate ?? "",
    remarks: order.remarks ?? "",
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toPurchaseOrderRequestPayload(
  values: PurchaseOrderFormValues
): PurchaseOrderCreateRequest {
  return {
    supplier_id: values.supplier_id,
    order_date: values.order_date,
    expected_delivery_date: values.expected_delivery_date || undefined,
    remarks: values.remarks || undefined,
  };
}

/** Same shape as `toPurchaseOrderRequestPayload` - a fully-populated `PurchaseOrderCreateRequest` is always a valid partial `PurchaseOrderUpdateRequest`. */
export function toPurchaseOrderUpdatePayload(
  values: PurchaseOrderFormValues
): PurchaseOrderUpdateRequest {
  return toPurchaseOrderRequestPayload(values);
}
