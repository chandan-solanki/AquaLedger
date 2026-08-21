import type { InvoiceStatus } from "@/features/invoices/types/invoice";

/**
 * Sprint 15 Session 6: raw backend shape (snake_case), matching
 * ConflictingInvoiceSummary (app/modules/invoices/schemas.py) exactly.
 * `quantity` is a string - the backend serializes `Decimal` as a JSON
 * string, never a float (ARCHITECTURE.md §5.1). Only what the conflict UI
 * needs - never the full invoice (no totals, no remarks, no tenant_id).
 */
export interface BackendConflictingInvoice {
  invoice_id: string;
  invoice_number: string | null;
  status: InvoiceStatus;
  invoice_date: string;
  company_name: string;
  quantity: string;
}

export interface ConflictingInvoice {
  invoiceId: string;
  invoiceNumber: string | null;
  status: InvoiceStatus;
  invoiceDate: string;
  companyName: string;
  quantity: string;
}

export function mapBackendConflictingInvoice(invoice: BackendConflictingInvoice): ConflictingInvoice {
  return {
    invoiceId: invoice.invoice_id,
    invoiceNumber: invoice.invoice_number,
    status: invoice.status,
    invoiceDate: invoice.invoice_date,
    companyName: invoice.company_name,
    quantity: invoice.quantity,
  };
}

/** Raw backend shape for GET /invoices/trip-catches/{id}/conflicts (TripCatchConflictResponse). */
export interface BackendTripCatchConflict {
  trip_catch_id: string;
  required_quantity: string | null;
  available_quantity: string;
  shortfall_quantity: string | null;
  conflicting_invoices: BackendConflictingInvoice[];
}

export interface TripCatchConflict {
  tripCatchId: string;
  requiredQuantity: string | null;
  availableQuantity: string;
  shortfallQuantity: string | null;
  conflictingInvoices: ConflictingInvoice[];
}

export function mapBackendTripCatchConflict(conflict: BackendTripCatchConflict): TripCatchConflict {
  return {
    tripCatchId: conflict.trip_catch_id,
    requiredQuantity: conflict.required_quantity,
    availableQuantity: conflict.available_quantity,
    shortfallQuantity: conflict.shortfall_quantity,
    conflictingInvoices: conflict.conflicting_invoices.map(mapBackendConflictingInvoice),
  };
}
