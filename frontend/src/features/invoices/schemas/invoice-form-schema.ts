import { z } from "zod";

import type { Invoice, InvoiceCreateRequest, InvoiceUpdateRequest } from "@/features/invoices/types/invoice";

// transport_charge/other_charge: Decimal, max_digits=14, decimal_places=2, ge=0 (app/modules/invoices/schemas.py).
const CHARGE_PATTERN = /^\d{1,12}(\.\d{1,2})?$/;

const chargeField = z
  .string()
  .trim()
  .refine((value) => value === "" || CHARGE_PATTERN.test(value), "Enter a valid amount (up to 2 decimal places)");

/**
 * Field names are snake_case, matching InvoiceCreateRequest/InvoiceUpdateRequest
 * exactly (app/modules/invoices/schemas.py) - so `mapServerErrorsToForm` can
 * set a 422's `field_errors` directly onto the right RHF field with no
 * translation layer, mirroring `tripFormSchema`.
 *
 * This is the header-only form for Sprint 7 Session 2 (TASKS.md) - there is
 * no `invoice_number` field (server-assigned only at issue, never
 * client-supplied) and no `status` field (always DRAFT at creation, and
 * `InvoiceUpdateRequest` never accepts it either - only the Issue action, a
 * separate later-session workflow, changes it). There are also no line
 * items or totals here - items are a separate sub-resource and every
 * calculated financial field is server-owned (Session 3+ scope).
 *
 * `invoice_date`/`due_date` are kept as ISO date strings (`yyyy-MM-dd`) here
 * rather than `Date` objects - `InvoiceForm` converts to/from `Date` at the
 * `DatePicker` boundary, mirroring `boatFormSchema`.
 */
export const invoiceFormSchema = z.object({
  company_id: z.string().trim().min(1, "Company is required"),
  invoice_date: z.string().trim().min(1, "Invoice date is required"),
  due_date: z.string().trim(),
  transport_charge: chargeField,
  other_charge: chargeField,
  remarks: z.string().trim(),
});

export type InvoiceFormValues = z.infer<typeof invoiceFormSchema>;

export const DEFAULT_INVOICE_FORM_VALUES: InvoiceFormValues = {
  company_id: "",
  invoice_date: "",
  due_date: "",
  transport_charge: "",
  other_charge: "",
  remarks: "",
};

/** Populates the form from a fetched `Invoice` for the Edit page - null fields become empty strings. */
export function toInvoiceFormValues(invoice: Invoice): InvoiceFormValues {
  return {
    company_id: invoice.companyId,
    invoice_date: invoice.invoiceDate,
    due_date: invoice.dueDate ?? "",
    transport_charge: invoice.transportCharge,
    other_charge: invoice.otherCharge,
    remarks: invoice.remarks ?? "",
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toInvoiceRequestPayload(values: InvoiceFormValues): InvoiceCreateRequest {
  return {
    company_id: values.company_id,
    invoice_date: values.invoice_date,
    due_date: values.due_date || undefined,
    transport_charge: values.transport_charge || undefined,
    other_charge: values.other_charge || undefined,
    remarks: values.remarks || undefined,
  };
}

/** Same shape as `toInvoiceRequestPayload` - a fully-populated `InvoiceCreateRequest` is always a valid partial `InvoiceUpdateRequest`. */
export function toInvoiceUpdatePayload(values: InvoiceFormValues): InvoiceUpdateRequest {
  return toInvoiceRequestPayload(values);
}
