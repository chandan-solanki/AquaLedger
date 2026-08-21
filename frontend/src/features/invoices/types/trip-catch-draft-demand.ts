/**
 * Sprint 15 Session 5: raw backend shape (snake_case), matching
 * TripCatchDraftDemandResponse (app/modules/invoices/schemas.py) exactly.
 * `other_draft_quantity` is a string - the backend serializes `Decimal` as a
 * JSON string, never a float (ARCHITECTURE.md §5.1). This is purely
 * informational - it is never used to reject a quantity client-side; the
 * issue-time, lock-protected backend check remains the sole authority.
 */
export interface BackendTripCatchDraftDemand {
  trip_catch_id: string;
  other_draft_quantity: string;
}

/** The client-facing, camelCase shape the invoice item form consumes. */
export interface TripCatchDraftDemand {
  tripCatchId: string;
  otherDraftQuantity: string;
}

export function mapBackendTripCatchDraftDemand(
  demand: BackendTripCatchDraftDemand
): TripCatchDraftDemand {
  return {
    tripCatchId: demand.trip_catch_id,
    otherDraftQuantity: demand.other_draft_quantity,
  };
}
