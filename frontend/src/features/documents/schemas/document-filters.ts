import type { DocumentTypeFilter } from "@/features/documents/constants/document-type";
import type { DocumentListParams, DocumentPartyType } from "@/features/documents/types/document";

/** Matches the backend's sortable field set (app/modules/documents/schemas.py) exactly. */
export const DOCUMENT_SORT_FIELDS = ["generated_at", "document_number"] as const;
export type DocumentSortField = (typeof DOCUMENT_SORT_FIELDS)[number];

export const DOCUMENT_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type DocumentSortDirection = (typeof DOCUMENT_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `PaymentFilters` — `toDocumentListParams` recombines them into
 * the wire format the backend actually expects. `partyId` has no filter
 * control this session (no unified cross-module party picker exists yet)
 * so it isn't part of this shape at all — only `DocumentListParams` keeps
 * the `party_id` param name available for later.
 */
export interface DocumentFilters {
  search: string;
  documentType: DocumentTypeFilter | null;
  partyType: DocumentPartyType | null;
  fromDate: string | null;
  toDate: string | null;
  page: number;
  pageSize: number;
  sort: DocumentSortField;
  direction: DocumentSortDirection;
}

export const DEFAULT_DOCUMENT_FILTERS: DocumentFilters = {
  search: "",
  documentType: null,
  partyType: null,
  fromDate: null,
  toDate: null,
  page: 1,
  pageSize: 20,
  sort: "generated_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's DocumentListParams query shape. */
export function toDocumentListParams(filters: DocumentFilters): DocumentListParams {
  return {
    q: filters.search.trim() || undefined,
    document_type: filters.documentType ?? undefined,
    party_type: filters.partyType ?? undefined,
    from_date: filters.fromDate ?? undefined,
    to_date: filters.toDate ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
