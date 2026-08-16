import { z } from "zod";

import type {
  PurchaseBill,
  PurchaseBillCreateRequest,
  PurchaseBillUpdateRequest,
} from "@/features/purchase-bills/types/purchase-bill";

/**
 * Field names are snake_case, matching PurchaseBillCreateRequest/
 * PurchaseBillUpdateRequest exactly (app/modules/purchase/schemas.py) - so
 * `mapServerErrorsToForm` can set a 422's `field_errors` directly onto the
 * right RHF field with no translation layer, mirroring `invoiceFormSchema`.
 *
 * This is the header-only form - there is no `bill_number` field (server-
 * assigned only at posting, never client-supplied) and no `status` field
 * (always DRAFT at creation, and `PurchaseBillUpdateRequest` never accepts
 * it either). Unlike `invoiceFormSchema`, there is also no Transport
 * Charge/Other Charge field - the backend does not accept either on this
 * resource at all (`PurchaseBillCreateRequest`'s own docstring: "Unlike
 * InvoiceCreateRequest, transport_charge/other_charge are NOT client-
 * settable"); every financial field starts at 0 and is computed once line
 * items exist. There are also no line items or totals here - items are a
 * separate sub-resource.
 *
 * `bill_date`/`due_date` are kept as ISO date strings (`yyyy-MM-dd`) here
 * rather than `Date` objects - `PurchaseBillForm` converts to/from `Date`
 * at the `DatePicker` boundary, mirroring `invoiceFormSchema`.
 *
 * `purchase_order_id` (Sprint 12 Session 12) is an empty-string sentinel
 * for "no linked purchase order", the same optional-field pattern
 * `due_date` already uses - `PurchaseBillForm` only ever shows this field
 * in Create mode (it is set-once/immutable, so Edit never renders it),
 * and `toPurchaseBillUpdatePayload` deliberately never includes it.
 */
export const purchaseBillFormSchema = z.object({
  supplier_id: z.string().trim().min(1, "Supplier is required"),
  purchase_order_id: z.string().trim(),
  bill_date: z.string().trim().min(1, "Bill date is required"),
  due_date: z.string().trim(),
  remarks: z.string().trim(),
});

export type PurchaseBillFormValues = z.infer<typeof purchaseBillFormSchema>;

export const DEFAULT_PURCHASE_BILL_FORM_VALUES: PurchaseBillFormValues = {
  supplier_id: "",
  purchase_order_id: "",
  bill_date: "",
  due_date: "",
  remarks: "",
};

/** Populates the form from a fetched `PurchaseBill` for the Edit page - null fields become empty strings. */
export function toPurchaseBillFormValues(bill: PurchaseBill): PurchaseBillFormValues {
  return {
    supplier_id: bill.supplierId,
    purchase_order_id: bill.purchaseOrderId ?? "",
    bill_date: bill.billDate,
    due_date: bill.dueDate ?? "",
    remarks: bill.remarks ?? "",
  };
}

/** Maps form values onto the create payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toPurchaseBillRequestPayload(values: PurchaseBillFormValues): PurchaseBillCreateRequest {
  return {
    supplier_id: values.supplier_id,
    purchase_order_id: values.purchase_order_id || undefined,
    bill_date: values.bill_date,
    due_date: values.due_date || undefined,
    remarks: values.remarks || undefined,
  };
}

/**
 * Unlike `toPurchaseBillRequestPayload`, deliberately omits
 * `purchase_order_id` - it is immutable after creation, and
 * `PurchaseBillUpdateRequest` has no field for it at all.
 */
export function toPurchaseBillUpdatePayload(values: PurchaseBillFormValues): PurchaseBillUpdateRequest {
  return {
    supplier_id: values.supplier_id,
    bill_date: values.bill_date,
    due_date: values.due_date || undefined,
    remarks: values.remarks || undefined,
  };
}
