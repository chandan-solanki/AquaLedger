/**
 * Sprint 15 Session 7: raw backend shape (snake_case), matching
 * TripCatchInvoiceUsage (app/modules/invoices/schemas.py) exactly.
 * `draft_quantity`/`consumed_quantity` are strings - the backend serializes
 * `Decimal` as a JSON string, never a float (ARCHITECTURE.md §5.1).
 */
export interface BackendTripCatchInvoiceUsage {
  trip_catch_id: string;
  invoice_count: number;
  draft_quantity: string;
  consumed_quantity: string;
}

export interface TripCatchInvoiceUsage {
  tripCatchId: string;
  invoiceCount: number;
  draftQuantity: string;
  consumedQuantity: string;
}

export function mapBackendTripCatchInvoiceUsage(
  usage: BackendTripCatchInvoiceUsage
): TripCatchInvoiceUsage {
  return {
    tripCatchId: usage.trip_catch_id,
    invoiceCount: usage.invoice_count,
    draftQuantity: usage.draft_quantity,
    consumedQuantity: usage.consumed_quantity,
  };
}
