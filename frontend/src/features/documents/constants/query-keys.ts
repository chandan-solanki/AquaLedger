import type { DocumentListParams } from "@/features/documents/types/document";

/**
 * The Document Center is read-only (list + download only, per the backend's
 * documents module) so unlike `paymentKeys` there is no `details`/`detail` —
 * there is no `GET /documents/{id}` endpoint to key a cache entry for.
 */
export const documentKeys = {
  all: () => ["documents"] as const,
  lists: () => [...documentKeys.all(), "list"] as const,
  list: (params: DocumentListParams) => [...documentKeys.lists(), params] as const,
};
