/**
 * Mirrors the backend's DocumentType enum (app/modules/documents/constants.py)
 * exactly — all six values it defines. `purchase_order`/`delivery_challan`
 * exist in the enum but have no renderer registered yet, so no document
 * record of either type can exist today; they're still modeled here (rather
 * than narrowed away) so a record's `document_type` is never typed as
 * `string`, and `DOCUMENT_TYPE_LABELS` (constants/document-type.ts) still has
 * a real label ready for the day a renderer is added. `DocumentTypeFilter`
 * (constants/document-type.ts) is the separate, narrower type actually used
 * for the query param / filter UI — only the four types a renderer exists
 * for today.
 */
export type DocumentType =
  | "invoice"
  | "purchase_bill"
  | "customer_payment_receipt"
  | "supplier_payment_receipt"
  | "purchase_order"
  | "delivery_challan";

/** Mirrors the backend's PartyType enum as used by the documents module. */
export type DocumentPartyType = "customer" | "supplier";

/**
 * Mirrors the backend's SourceType enum (app/modules/documents/constants.py,
 * Sprint 12 Session 8) — the business module/table `source_id` resolves
 * against. Deliberately a different vocabulary from `DocumentType`: a
 * `customer_payment_receipt` document's source row lives in `payments`, so
 * its `source_type` is `"payment"`, not `"customer_payment_receipt"`. See
 * `constants/source-navigation.ts` for the source_type -> route mapping.
 */
export type SourceType = "invoice" | "purchase_bill" | "payment" | "supplier_payment";

/**
 * Raw backend shape (snake_case), matching `DocumentResponse`
 * (app/modules/documents/schemas.py) exactly. `party_type`/`party_id`/
 * `party_name` are all nullable — some document types (e.g. a future
 * internal-only document) may have no associated party. `source_type`/
 * `source_id` are also nullable — every DocumentRecord created before
 * Session 8 has neither, and any document type without a mapped source
 * simply has no navigation available. There is deliberately no
 * `storage_key` field — the backend never exposes the physical file path
 * to the client.
 */
export interface BackendDocument {
  id: string;
  document_type: DocumentType;
  document_number: string;
  party_type: DocumentPartyType | null;
  party_id: string | null;
  party_name: string | null;
  source_type: SourceType | null;
  source_id: string | null;
  generated_at: string;
  generated_by: string;
  generated_by_name: string;
  file_name: string;
  file_extension: string;
  content_type: string;
  file_size: number;
}

/** The client-facing, camelCase shape every document-service.ts function returns. */
export interface Document {
  id: string;
  documentType: DocumentType;
  documentNumber: string;
  partyType: DocumentPartyType | null;
  partyId: string | null;
  partyName: string | null;
  sourceType: SourceType | null;
  sourceId: string | null;
  generatedAt: string;
  generatedBy: string;
  generatedByName: string;
  fileName: string;
  fileExtension: string;
  contentType: string;
  fileSize: number;
}

export function mapBackendDocument(document: BackendDocument): Document {
  return {
    id: document.id,
    documentType: document.document_type,
    documentNumber: document.document_number,
    partyType: document.party_type,
    partyId: document.party_id,
    partyName: document.party_name,
    sourceType: document.source_type,
    sourceId: document.source_id,
    generatedAt: document.generated_at,
    generatedBy: document.generated_by,
    generatedByName: document.generated_by_name,
    fileName: document.file_name,
    fileExtension: document.file_extension,
    contentType: document.content_type,
    fileSize: document.file_size,
  };
}

/**
 * Query params for GET /documents (app/modules/documents/schemas.py's
 * DocumentListParams) — snake_case to match the wire format exactly, since
 * `document-service.ts` forwards these straight through as a query string.
 * `party_id` is kept here (rather than omitted) for a future session — no
 * unified cross-module party picker exists yet, so it's never set by
 * `toDocumentListParams`, but the param name stays available on the type.
 */
export interface DocumentListParams {
  q?: string;
  document_type?: DocumentType;
  party_type?: DocumentPartyType;
  party_id?: string;
  from_date?: string;
  to_date?: string;
  sort: string;
  page: number;
  page_size: number;
}
