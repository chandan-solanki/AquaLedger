import { z } from "zod";

import type {
  DeliveryChallan,
  DeliveryChallanCreateRequest,
  DeliveryChallanUpdateRequest,
} from "@/features/delivery-challans/types/delivery-challan";

/**
 * Field names are snake_case, matching DeliveryChallanCreateRequest/
 * DeliveryChallanUpdateRequest exactly (app/modules/delivery_challans/
 * schemas.py) - so `mapServerErrorsToForm` can set a 422's `field_errors`
 * directly onto the right RHF field with no translation layer, mirroring
 * `purchaseOrderFormSchema`.
 *
 * `invoice_id` is required for Create and set-once - there is no equivalent
 * field on `DeliveryChallanUpdateRequest`, so `DeliveryChallanForm` disables
 * (never hides) the Invoice picker for Edit rather than omitting it, so the
 * originating invoice stays visible even though it can no longer change.
 * There are no financial fields, line items, or totals here either - items
 * are a separate sub-resource and this document carries no money at all.
 */
export const deliveryChallanFormSchema = z.object({
  invoice_id: z.string().trim().min(1, "Invoice is required"),
  challan_date: z.string().trim().min(1, "Challan date is required"),
  remarks: z.string().trim(),
});

export type DeliveryChallanFormValues = z.infer<typeof deliveryChallanFormSchema>;

export const DEFAULT_DELIVERY_CHALLAN_FORM_VALUES: DeliveryChallanFormValues = {
  invoice_id: "",
  challan_date: "",
  remarks: "",
};

/** Populates the form from a fetched `DeliveryChallan` for the Edit page - null fields become empty strings. */
export function toDeliveryChallanFormValues(challan: DeliveryChallan): DeliveryChallanFormValues {
  return {
    invoice_id: challan.invoiceId,
    challan_date: challan.challanDate,
    remarks: challan.remarks ?? "",
  };
}

/** Maps form values onto the create request payload - empty remarks becomes `undefined` rather than an empty string. */
export function toDeliveryChallanRequestPayload(
  values: DeliveryChallanFormValues
): DeliveryChallanCreateRequest {
  return {
    invoice_id: values.invoice_id,
    challan_date: values.challan_date,
    remarks: values.remarks || undefined,
  };
}

/**
 * `invoice_id` is deliberately dropped here (unlike
 * `toPurchaseOrderUpdatePayload`'s straight reuse of its create-payload
 * mapper) - `DeliveryChallanUpdateRequest` never accepts it, since the
 * originating invoice is immutable after creation.
 */
export function toDeliveryChallanUpdatePayload(
  values: DeliveryChallanFormValues
): DeliveryChallanUpdateRequest {
  return {
    challan_date: values.challan_date,
    remarks: values.remarks || undefined,
  };
}
