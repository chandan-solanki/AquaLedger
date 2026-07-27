import { z } from "zod";

import { EXPENSE_TYPE_VALUES } from "@/features/trips/constants/expense-type";
import type {
  TripExpense,
  TripExpenseCreateRequest,
  TripExpenseUpdateRequest,
} from "@/features/trips/types/trip-expense";

// amount: Decimal, max_digits=14, decimal_places=2, gt=0 (app/modules/trip_expenses/schemas.py).
const AMOUNT_PATTERN = /^\d{1,12}(\.\d{1,2})?$/;

const amountField = z
  .string()
  .trim()
  .min(1, "Amount is required")
  .refine((value) => AMOUNT_PATTERN.test(value), "Enter a valid amount (up to 2 decimal places)")
  .refine((value) => Number(value) > 0, "Must be greater than 0");

/**
 * Field names are snake_case, matching TripExpenseCreateRequest/
 * TripExpenseUpdateRequest exactly, mirroring `tripCatchFormSchema`. There
 * is no `trip_id` field here - the owning trip is always the current Trip
 * Detail page's trip, supplied by the page
 * (`toTripExpenseRequestPayload(tripId, ...)`), never chosen by the user
 * (Sprint 6 Session 6's Navigation rule: "Users should never manually
 * choose the trip").
 *
 * The backend's cross-entity date-window rule (`expense_date` must fall
 * within the owning trip's departure/return window, and the trip must not
 * be CANCELLED) is intentionally left server-validated only, mirroring how
 * `TripForm` leaves "boat already has an active trip" server-validated -
 * both depend on live state (another record's current status/dates) this
 * form doesn't otherwise need to fetch, surfaced via the existing generic
 * 422 toast path.
 */
export const tripExpenseFormSchema = z.object({
  expense_type: z.enum(EXPENSE_TYPE_VALUES),
  amount: amountField,
  expense_date: z.string().trim().min(1, "Expense date is required"),
  description: z.string().trim(),
  vendor_name: z.string().trim().max(255, "Must be 255 characters or fewer"),
  receipt_number: z.string().trim().max(100, "Must be 100 characters or fewer"),
});

export type TripExpenseFormValues = z.infer<typeof tripExpenseFormSchema>;

export const DEFAULT_TRIP_EXPENSE_FORM_VALUES: TripExpenseFormValues = {
  expense_type: "diesel",
  amount: "",
  expense_date: "",
  description: "",
  vendor_name: "",
  receipt_number: "",
};

/** Populates the form from a fetched `TripExpense` for the Edit page - null fields become empty strings. */
export function toTripExpenseFormValues(tripExpense: TripExpense): TripExpenseFormValues {
  return {
    expense_type: tripExpense.expenseType,
    amount: tripExpense.amount,
    expense_date: tripExpense.expenseDate,
    description: tripExpense.description ?? "",
    vendor_name: tripExpense.vendorName ?? "",
    receipt_number: tripExpense.receiptNumber ?? "",
  };
}

/** Maps form values onto the Create payload - `tripId` comes from the Trip Detail page's route, never the form. */
export function toTripExpenseRequestPayload(
  tripId: string,
  values: TripExpenseFormValues
): TripExpenseCreateRequest {
  return {
    trip_id: tripId,
    expense_type: values.expense_type,
    amount: values.amount,
    expense_date: values.expense_date,
    description: values.description || undefined,
    vendor_name: values.vendor_name || undefined,
    receipt_number: values.receipt_number || undefined,
  };
}

/** Same fields as create minus `trip_id` - this form has no trip selector, so reassignment is never offered. */
export function toTripExpenseUpdatePayload(values: TripExpenseFormValues): TripExpenseUpdateRequest {
  return {
    expense_type: values.expense_type,
    amount: values.amount,
    expense_date: values.expense_date,
    description: values.description || undefined,
    vendor_name: values.vendor_name || undefined,
    receipt_number: values.receipt_number || undefined,
  };
}
