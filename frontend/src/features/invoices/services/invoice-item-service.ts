import { bffClient } from "@/lib/bff-client";
import type {
  BackendInvoiceItem,
  InvoiceItem,
  InvoiceItemCreateRequest,
  InvoiceItemListParams,
  InvoiceItemUpdateRequest,
} from "@/features/invoices/types/invoice-item";
import { mapBackendInvoiceItem } from "@/features/invoices/types/invoice-item";

function buildQueryString(params: InvoiceItemListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/invoices/{id}/items*`)
 * — never the FastAPI backend directly, mirroring `invoice-service.ts`. The
 * BFF route handlers attach the caller's HttpOnly access token server-side
 * and forward the request. Unlike `invoice-service.ts`'s list endpoint,
 * `listInvoiceItems` returns a plain array, not a paginated envelope - the
 * backend itself returns `list[InvoiceItemResponse]`, not
 * `PaginatedResponse[...]` (app/modules/invoices/router.py: "no pagination -
 * an invoice's line count is small and bounded").
 */
export const invoiceItemService = {
  async listInvoiceItems(invoiceId: string, params: InvoiceItemListParams = {}): Promise<InvoiceItem[]> {
    const qs = buildQueryString(params);
    const { data } = await bffClient.get<BackendInvoiceItem[]>(
      `/invoices/${invoiceId}/items${qs ? `?${qs}` : ""}`
    );
    return data.map(mapBackendInvoiceItem);
  },

  async createInvoiceItem(invoiceId: string, payload: InvoiceItemCreateRequest): Promise<InvoiceItem> {
    const { data } = await bffClient.post<BackendInvoiceItem>(`/invoices/${invoiceId}/items`, payload);
    return mapBackendInvoiceItem(data);
  },

  async updateInvoiceItem(
    invoiceId: string,
    itemId: string,
    payload: InvoiceItemUpdateRequest
  ): Promise<InvoiceItem> {
    const { data } = await bffClient.put<BackendInvoiceItem>(
      `/invoices/${invoiceId}/items/${itemId}`,
      payload
    );
    return mapBackendInvoiceItem(data);
  },

  async deleteInvoiceItem(invoiceId: string, itemId: string): Promise<void> {
    await bffClient.delete(`/invoices/${invoiceId}/items/${itemId}`);
  },
};
