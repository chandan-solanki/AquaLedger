"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DOCUMENT_PARTY_TYPE_VALUES,
  DOCUMENT_TYPE_FILTER_VALUES,
} from "@/features/documents/constants/document-type";
import {
  DEFAULT_DOCUMENT_FILTERS,
  DOCUMENT_SORT_DIRECTIONS,
  DOCUMENT_SORT_FIELDS,
} from "@/features/documents/schemas/document-filters";

const documentFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_DOCUMENT_FILTERS.search),
  documentType: parseAsStringEnum([...DOCUMENT_TYPE_FILTER_VALUES]),
  partyType: parseAsStringEnum([...DOCUMENT_PARTY_TYPE_VALUES]),
  fromDate: parseAsString,
  toDate: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_DOCUMENT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_DOCUMENT_FILTERS.pageSize),
  sort: parseAsStringEnum([...DOCUMENT_SORT_FIELDS]).withDefault(DEFAULT_DOCUMENT_FILTERS.sort),
  direction: parseAsStringEnum([...DOCUMENT_SORT_DIRECTIONS]).withDefault(DEFAULT_DOCUMENT_FILTERS.direction),
};

/**
 * Document Center filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"), mirroring `usePaymentFilters` exactly.
 */
export function useDocumentFilters() {
  return useQueryStates(documentFilterParsers, { history: "push" });
}
