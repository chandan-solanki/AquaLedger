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
};
