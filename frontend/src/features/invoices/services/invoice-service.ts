import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendInvoice,
  Invoice,
  InvoiceCreateRequest,
  InvoiceListParams,
  InvoiceUpdateRequest,
} from "@/features/invoices/types/invoice";
import { mapBackendInvoice } from "@/features/invoices/types/invoice";
import type { BackendTripCatchDraftDemand, TripCatchDraftDemand } from "@/features/invoices/types/trip-catch-draft-demand";
import { mapBackendTripCatchDraftDemand } from "@/features/invoices/types/trip-catch-draft-demand";
import type { BackendTripCatchConflict, TripCatchConflict } from "@/features/invoices/types/trip-catch-conflict";
import { mapBackendTripCatchConflict } from "@/features/invoices/types/trip-catch-conflict";
import type {
  BackendTripCatchInvoiceUsage,
  TripCatchInvoiceUsage,
} from "@/features/invoices/types/trip-catch-invoice-usage";
import { mapBackendTripCatchInvoiceUsage } from "@/features/invoices/types/trip-catch-invoice-usage";
import type {
  BackendTripCatchOtherInvoiceUsage,
  TripCatchOtherInvoiceUsage,
} from "@/features/invoices/types/trip-catch-other-invoice-usage";
import { mapBackendTripCatchOtherInvoiceUsage } from "@/features/invoices/types/trip-catch-other-invoice-usage";
import type {
  BackendInvoiceIssuePreflightResponse,
  InvoiceIssuePreflightResponse,
} from "@/features/invoices/types/invoice-issue-preflight";
import { mapBackendInvoiceIssuePreflightResponse } from "@/features/invoices/types/invoice-issue-preflight";

export interface InvoiceListResult {
  data: Invoice[];
  meta: ApiListEnvelope<BackendInvoice>["meta"];
}

function buildQueryString(params: InvoiceListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.status) query.set("status", params.status);
  if (params.company_id) query.set("company_id", params.company_id);
  if (params.invoice_date_from) query.set("invoice_date_from", params.invoice_date_from);
  if (params.invoice_date_to) query.set("invoice_date_to", params.invoice_date_to);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/invoices/*`) — never the
 * FastAPI backend directly, mirroring `boat-service.ts`/`trip-service.ts`:
 * the browser never holds a bearer token to attach here (ARCHITECTURE.md
 * §1.2, §8.1). The BFF route handlers (`app/api/invoices/**`) attach the
 * caller's HttpOnly access token server-side and forward the request.
 * `issueInvoice`/`deleteInvoice` are the two lifecycle actions the backend
 * actually exposes (app/modules/invoices/router.py) - there is no cancel
 * endpoint yet ("invoice:cancel" is only a seeded permission code reserved
 * for a future cancel/credit-note workflow, per invoices/permissions.py's
 * own comment), so no `cancelInvoice` method exists here.
 */
export const invoiceService = {
  async listInvoices(params: InvoiceListParams): Promise<InvoiceListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendInvoice>>(
      `/invoices?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendInvoice), meta: data.meta };
  },

  async getInvoice(id: string): Promise<Invoice> {
    const { data } = await bffClient.get<BackendInvoice>(`/invoices/${id}`);
    return mapBackendInvoice(data);
  },

  async createInvoice(payload: InvoiceCreateRequest): Promise<Invoice> {
    const { data } = await bffClient.post<BackendInvoice>("/invoices", payload);
    return mapBackendInvoice(data);
  },

  async updateInvoice(id: string, payload: InvoiceUpdateRequest): Promise<Invoice> {
    const { data } = await bffClient.put<BackendInvoice>(`/invoices/${id}`, payload);
    return mapBackendInvoice(data);
  },

  async deleteInvoice(id: string): Promise<void> {
    await bffClient.delete(`/invoices/${id}`);
  },

  /**
   * `draft` -> `issued` (app/modules/invoices/service.py's `InvoiceService.issue`)
   * - assigns `invoice_number`, deducts every referenced trip catch's
   * `available_quantity` (crediting `sold_quantity`), and increases the
   * billed company's `outstanding_amount`, all server-side in one
   * transaction. Takes no request body - the backend computes everything
   * from the invoice's own current items.
   */
  async issueInvoice(id: string): Promise<Invoice> {
    const { data } = await bffClient.post<BackendInvoice>(`/invoices/${id}/issue`);
    return mapBackendInvoice(data);
  },

  /**
   * Sprint 15 Session 5: "how much of this trip catch do OTHER draft
   * invoices currently want" - a UX-only number (app/modules/invoices/
   * service.py's `get_trip_catch_draft_demand`), never a stock reservation.
   * `excludeInvoiceId` should always be the invoice currently being
   * created/edited, so its own items are never counted as "other" demand.
   */
  async getTripCatchDraftDemand(
    tripCatchId: string,
    options?: { excludeInvoiceId?: string }
  ): Promise<TripCatchDraftDemand> {
    const query = options?.excludeInvoiceId
      ? `?exclude_invoice_id=${options.excludeInvoiceId}`
      : "";
    const { data } = await bffClient.get<BackendTripCatchDraftDemand>(
      `/invoices/trip-catches/${tripCatchId}/draft-demand${query}`
    );
    return mapBackendTripCatchDraftDemand(data);
  },

  /**
   * Sprint 15 Session 6: "which other invoices may explain why issuing this
   * failed" - called after a 422 INVOICE_INSUFFICIENT_INVENTORY, using the
   * `trip_catch_id`/`requested_quantity` the error's `details` already
   * carried. Read-only and resolved fresh - never a stock reservation, and
   * never proof of which invoice(s) actually caused the shortage.
   */
  async getTripCatchConflicts(
    tripCatchId: string,
    options?: { excludeInvoiceId?: string; requiredQuantity?: string }
  ): Promise<TripCatchConflict> {
    const query = new URLSearchParams();
    if (options?.excludeInvoiceId) query.set("exclude_invoice_id", options.excludeInvoiceId);
    if (options?.requiredQuantity) query.set("required_quantity", options.requiredQuantity);
    const queryString = query.toString();
    const { data } = await bffClient.get<BackendTripCatchConflict>(
      `/invoices/trip-catches/${tripCatchId}/conflicts${queryString ? `?${queryString}` : ""}`
    );
    return mapBackendTripCatchConflict(data);
  },

  /**
   * Sprint 15 Session 7: batched "how many invoices reference this catch"
   * for the Fish Stock detail page's Contributing Catches table - one call
   * for every trip catch shown on that page, never one request per row.
   * A trip catch with no qualifying invoice is simply absent from the
   * result - callers should treat a missing id as zero usage, not an error.
   */
  async getTripCatchInvoiceUsageSummary(tripCatchIds: string[]): Promise<TripCatchInvoiceUsage[]> {
    if (tripCatchIds.length === 0) return [];
    const query = new URLSearchParams();
    tripCatchIds.forEach((id) => query.append("trip_catch_ids", id));
    const { data } = await bffClient.get<BackendTripCatchInvoiceUsage[]>(
      `/invoices/trip-catches/usage-summary?${query.toString()}`
    );
    return data.map(mapBackendTripCatchInvoiceUsage);
  },

  /**
   * Sprint 15 Session 8: proactive "Other Invoice Usage" for the Invoice
   * Detail page's item table - for each trip catch THIS invoice's own items
   * reference, how much OTHER invoices also reference it. One call for the
   * whole page regardless of item count, never one request per row. The
   * invoice being viewed is always excluded server-side - its own items
   * never count as their own conflict, even when several of them reference
   * the same trip catch.
   */
  async getInvoiceTripCatchConflicts(invoiceId: string): Promise<TripCatchOtherInvoiceUsage[]> {
    const { data } = await bffClient.get<BackendTripCatchOtherInvoiceUsage[]>(
      `/invoices/${invoiceId}/trip-catch-conflicts`
    );
    return data.map(mapBackendTripCatchOtherInvoiceUsage);
  },

  /**
   * Sprint 15 Session 10: "is this draft invoice likely issuable right now" -
   * a snapshot check run just before the user confirms Issue Invoice, never
   * a substitute for the backend's own lock-protected validation at actual
   * issue time. `conflicts` lists only currently-insufficient trip catches;
   * an empty list means `canIssueNow` is true.
   */
  async getInvoiceIssuePreflight(invoiceId: string): Promise<InvoiceIssuePreflightResponse> {
    const { data } = await bffClient.get<BackendInvoiceIssuePreflightResponse>(
      `/invoices/${invoiceId}/issue-preflight`
    );
    return mapBackendInvoiceIssuePreflightResponse(data);
  },
};
