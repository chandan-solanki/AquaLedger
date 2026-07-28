import { z } from "zod";

import { PAYMENT_METHOD_VALUES } from "@/features/payments/constants/payment-method";
import type {
  Payment,
  PaymentCreateRequest,
  PaymentUpdateRequest,
} from "@/features/payments/types/payment";

// amount: Decimal, max_digits=14, decimal_places=2, gt=0 (app/modules/payments/schemas.py).
const AMOUNT_PATTERN = /^\d{1,12}(\.\d{1,2})?$/;

const amountField = z
  .string()
  .trim()
  .min(1, "Amount is required")
  .refine((value) => AMOUNT_PATTERN.test(value), "Enter a valid amount (up to 2 decimal places)")
  .refine((value) => Number(value) > 0, "Must be greater than 0");

/**
 * Field names are snake_case, matching PaymentCreateRequest/
 * PaymentUpdateRequest exactly (app/modules/payments/schemas.py) - so
 * `mapServerErrorsToForm` can set a 422's `field_errors` directly onto the
 * right RHF field with no translation layer, mirroring `invoiceFormSchema`.
 *
 * This is the header-only Create/Edit form for Sprint 8 Session 2 (TASKS.md)
 * - there is no `payment_number` field (server-assigned only at posting,
 * never client-supplied) and no `status`/`allocated_amount`/
 * `unallocated_amount` fields either (always DRAFT/0/`amount` at creation,
 * and none of the three is ever accepted by `PaymentUpdateRequest`). There is
 * also no allocation UI here - allocations are a separate sub-resource, out
 * of this session's scope.
 *
 * `payment_date` is kept as an ISO date string (`yyyy-MM-dd`) here rather
 * than a `Date` object - `PaymentForm` converts to/from `Date` at the
 * `DatePicker` boundary, mirroring `invoiceFormSchema`.
 */
export const paymentFormSchema = z.object({
  company_id: z.string().trim().min(1, "Customer is required"),
  payment_date: z.string().trim().min(1, "Payment date is required"),
  payment_method: z.enum(PAYMENT_METHOD_VALUES),
  amount: amountField,
  reference_number: z.string().trim().max(100, "Must be 100 characters or fewer"),
  bank_name: z.string().trim().max(255, "Must be 255 characters or fewer"),
  remarks: z.string().trim(),
});

export type PaymentFormValues = z.infer<typeof paymentFormSchema>;

export const DEFAULT_PAYMENT_FORM_VALUES: PaymentFormValues = {
  company_id: "",
  payment_date: "",
  payment_method: "cash",
  amount: "",
  reference_number: "",
  bank_name: "",
  remarks: "",
};

/** Populates the form from a fetched `Payment` for the Edit page - null fields become empty strings. */
export function toPaymentFormValues(payment: Payment): PaymentFormValues {
  return {
    company_id: payment.companyId,
    payment_date: payment.paymentDate,
    payment_method: payment.paymentMethod,
    amount: payment.amount,
    reference_number: payment.referenceNumber ?? "",
    bank_name: payment.bankName ?? "",
    remarks: payment.remarks ?? "",
  };
}

/** Maps form values onto the request payload - empty strings become `undefined` so the backend applies its own defaults/null rather than writing empty strings. */
export function toPaymentRequestPayload(values: PaymentFormValues): PaymentCreateRequest {
  return {
    company_id: values.company_id,
    payment_date: values.payment_date,
    payment_method: values.payment_method,
    amount: values.amount,
    reference_number: values.reference_number || undefined,
    bank_name: values.bank_name || undefined,
    remarks: values.remarks || undefined,
  };
}

/** Same shape as `toPaymentRequestPayload` - a fully-populated `PaymentCreateRequest` is always a valid partial `PaymentUpdateRequest`. */
export function toPaymentUpdatePayload(values: PaymentFormValues): PaymentUpdateRequest {
  return toPaymentRequestPayload(values);
}
