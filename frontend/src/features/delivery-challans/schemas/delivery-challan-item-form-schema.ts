import { z } from "zod";

import type {
  DeliveryChallanItem,
  DeliveryChallanItemCreateRequest,
  DeliveryChallanItemUpdateRequest,
} from "@/features/delivery-challans/types/delivery-challan-item";

// Mirrors the backend's exact check (app/modules/delivery_challans/schemas.py)
// so the form never rejects something the backend would accept, or vice
// versa. quantity: Decimal, max_digits=12, decimal_places=3, gt=0.
const QUANTITY_PATTERN = /^\d{1,9}(\.\d{1,3})?$/;

const quantityField = z
  .string()
  .trim()
  .min(1, "Quantity is required")
  .refine((value) => QUANTITY_PATTERN.test(value), "Enter a valid quantity (up to 3 decimal places)")
  .refine((value) => Number(value) > 0, "Must be greater than 0");

/**
 * Field names are snake_case, matching DeliveryChallanItemCreateRequest/
 * DeliveryChallanItemUpdateRequest exactly (app/modules/delivery_challans/
 * schemas.py) - so `mapServerErrorsToForm` can set a 422's `field_errors`
 * directly onto the right RHF field with no translation layer.
 *
 * There is no `description`/`unit`/`rate` field here, unlike
 * `purchaseOrderItemFormSchema` - a delivery challan item carries no
 * financial fields at all, and `unit` is always derived server-side from
 * the linked invoice item, never client-supplied. `invoice_item_id` is
 * immutable after creation (no field for it on the update side) - the Edit
 * form only ever changes `quantity`.
 */
export const deliveryChallanItemFormSchema = z.object({
  invoice_item_id: z.string().trim().min(1, "Invoice item is required"),
  quantity: quantityField,
});

export type DeliveryChallanItemFormValues = z.infer<typeof deliveryChallanItemFormSchema>;

export const DEFAULT_DELIVERY_CHALLAN_ITEM_FORM_VALUES: DeliveryChallanItemFormValues = {
  invoice_item_id: "",
  quantity: "",
};

/** Populates the form from a fetched `DeliveryChallanItem` for the Edit dialog. */
export function toDeliveryChallanItemFormValues(item: DeliveryChallanItem): DeliveryChallanItemFormValues {
  return {
    invoice_item_id: item.invoiceItemId,
    quantity: item.quantity,
  };
}

/** Maps form values onto the create request payload. */
export function toDeliveryChallanItemRequestPayload(
  values: DeliveryChallanItemFormValues
): DeliveryChallanItemCreateRequest {
  return {
    invoice_item_id: values.invoice_item_id,
    quantity: values.quantity,
  };
}

/**
 * Only `quantity` is ever sent for an update - `invoice_item_id` is
 * immutable after creation and `DeliveryChallanItemUpdateRequest` never
 * accepts it.
 */
export function toDeliveryChallanItemUpdatePayload(
  values: DeliveryChallanItemFormValues
): DeliveryChallanItemUpdateRequest {
  return {
    quantity: values.quantity,
  };
}
