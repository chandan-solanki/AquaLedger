"use client";

import { useQuery } from "@tanstack/react-query";

import { numberingSequenceKeys } from "@/features/numbering-sequences/constants/query-keys";
import { numberingSequenceService } from "@/features/numbering-sequences/services/numbering-sequence-service";

/** The caller's own tenant's numbering status - always exactly six rows, one per document type. */
export function useNumberingSequences() {
  return useQuery({
    queryKey: numberingSequenceKeys.list(),
    queryFn: () => numberingSequenceService.listNumberingSequences(),
  });
}
