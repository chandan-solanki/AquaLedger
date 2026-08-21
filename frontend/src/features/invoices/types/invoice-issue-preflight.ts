/**
 * Sprint 15 Session 10: raw backend shape (snake_case), matching
 * InvoiceIssuePreflightConflict/InvoiceIssuePreflightResponse
 * (app/modules/invoices/schemas.py) exactly. Every quantity is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1). `conflicts` lists only trip catches that are NOT
 * currently sufficient - a sufficient one never appears, so `can_issue_now`
 * is exactly `conflicts.length === 0`.
 */
export interface BackendInvoiceIssuePreflightConflict {
  trip_catch_id: string;
  requested_quantity: string;
  available_quantity: string;
  is_sufficient: boolean;
  shortfall_quantity: string;
  other_draft_quantity: string;
}

export interface BackendInvoiceIssuePreflightResponse {
  invoice_id: string;
  can_issue_now: boolean;
  conflicts: BackendInvoiceIssuePreflightConflict[];
}

export interface InvoiceIssuePreflightConflict {
  tripCatchId: string;
  requestedQuantity: string;
  availableQuantity: string;
  isSufficient: boolean;
  shortfallQuantity: string;
  otherDraftQuantity: string;
}

export interface InvoiceIssuePreflightResponse {
  invoiceId: string;
  canIssueNow: boolean;
  conflicts: InvoiceIssuePreflightConflict[];
}

export function mapBackendInvoiceIssuePreflightConflict(
  conflict: BackendInvoiceIssuePreflightConflict
): InvoiceIssuePreflightConflict {
  return {
    tripCatchId: conflict.trip_catch_id,
    requestedQuantity: conflict.requested_quantity,
    availableQuantity: conflict.available_quantity,
    isSufficient: conflict.is_sufficient,
    shortfallQuantity: conflict.shortfall_quantity,
    otherDraftQuantity: conflict.other_draft_quantity,
  };
}

export function mapBackendInvoiceIssuePreflightResponse(
  response: BackendInvoiceIssuePreflightResponse
): InvoiceIssuePreflightResponse {
  return {
    invoiceId: response.invoice_id,
    canIssueNow: response.can_issue_now,
    conflicts: response.conflicts.map(mapBackendInvoiceIssuePreflightConflict),
  };
}
