import { bffClient } from "@/lib/bff-client";
import type {
  BackendNumberingSequence,
  NumberingSequence,
} from "@/features/numbering-sequences/types/numbering-sequence";
import { mapBackendNumberingSequence } from "@/features/numbering-sequences/types/numbering-sequence";

/**
 * Talks only to the Next.js BFF's own routes (`/api/numbering-sequences`) -
 * never the FastAPI backend directly, mirroring `company-profile-service.ts`'s
 * own rationale exactly (ARCHITECTURE.md §1.2, §8.1).
 */
export const numberingSequenceService = {
  async listNumberingSequences(): Promise<NumberingSequence[]> {
    const { data } = await bffClient.get<BackendNumberingSequence[]>("/numbering-sequences");
    return data.map(mapBackendNumberingSequence);
  },
};
