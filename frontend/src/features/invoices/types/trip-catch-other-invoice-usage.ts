/**
 * Sprint 15 Session 8: raw backend shape (snake_case), matching
 * TripCatchOtherInvoiceUsage (app/modules/invoices/schemas.py) exactly.
 * `other_draft_quantity`/`other_consumed_quantity` are strings - the backend
 * serializes `Decimal` as a JSON string, never a float (ARCHITECTURE.md
 * §5.1). Deliberately a distinct type from `TripCatchInvoiceUsage` (Session
 * 7) even though the shapes are similar: that one is an absolute count with
 * no exclusion (Fish Stock page, `fish:view`); this one is always relative
 * to "other than the invoice I'm viewing" (Invoice Detail page,
 * `invoice:view`).
 */
export interface BackendTripCatchOtherInvoiceUsage {
  trip_catch_id: string;
  other_invoice_count: number;
  other_draft_quantity: string;
  other_consumed_quantity: string;
}

export interface TripCatchOtherInvoiceUsage {
  tripCatchId: string;
  otherInvoiceCount: number;
  otherDraftQuantity: string;
  otherConsumedQuantity: string;
}

export function mapBackendTripCatchOtherInvoiceUsage(
  usage: BackendTripCatchOtherInvoiceUsage
): TripCatchOtherInvoiceUsage {
  return {
    tripCatchId: usage.trip_catch_id,
    otherInvoiceCount: usage.other_invoice_count,
    otherDraftQuantity: usage.other_draft_quantity,
    otherConsumedQuantity: usage.other_consumed_quantity,
  };
}
