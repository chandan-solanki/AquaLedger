"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { documentKeys } from "@/features/documents/constants/query-keys";
import type { DocumentFilters } from "@/features/documents/schemas/document-filters";
import { toDocumentListParams } from "@/features/documents/schemas/document-filters";
import { documentService } from "@/features/documents/services/document-service";

/**
 * Server-side, paginated document list — every filter/sort/page change
 * refetches from the backend rather than filtering an already-loaded page
 * client-side, mirroring `usePayments`. `keepPreviousData` keeps the current
 * rows on screen (instead of flashing to a loading state) while a
 * filter/page change is in flight.
 */
export function useDocuments(filters: DocumentFilters) {
  const params = toDocumentListParams(filters);

  return useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () => documentService.listDocuments(params),
    placeholderData: keepPreviousData,
  });
}
