import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type { BackendDocument, Document, DocumentListParams } from "@/features/documents/types/document";
import { mapBackendDocument } from "@/features/documents/types/document";

export interface DocumentListResult {
  data: Document[];
  meta: ApiListEnvelope<BackendDocument>["meta"];
}

function buildQueryString(params: DocumentListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.document_type) query.set("document_type", params.document_type);
  if (params.party_type) query.set("party_type", params.party_type);
  if (params.party_id) query.set("party_id", params.party_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/documents/*`) — never
 * the FastAPI backend directly, mirroring `payment-service.ts`: the browser
 * never holds a bearer token to attach here (ARCHITECTURE.md §1.2, §8.1).
 * This is the Document Center's entire surface — read-only discovery of
 * already-generated files (list + download), no create/update/delete: a
 * document record is only ever produced by its own module's PDF-render
 * pipeline (Invoice issue, Payment post, etc.), never authored here.
 */
export const documentService = {
  async listDocuments(params: DocumentListParams): Promise<DocumentListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendDocument>>(
      `/documents?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendDocument), meta: data.meta };
  },
};
