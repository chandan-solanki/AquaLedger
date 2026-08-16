import { downloadUrl } from "@/utils/download-url";

/**
 * Triggers the browser's native download of a generated document's file via
 * `/api/documents/{id}/download` — the same anchor-click mechanism
 * `triggerPaymentDocumentDownload`/`triggerInvoiceDocumentDownload` use for
 * their own PDFs, reused here rather than duplicated.
 */
export function triggerDocumentDownload(documentId: string): void {
  downloadUrl(`/api/documents/${documentId}/download`);
}
