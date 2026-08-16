import { downloadUrl } from "@/utils/download-url";

/**
 * Triggers the browser's native download of a purchase bill's PDF via
 * `/api/purchase/{id}/document` - the same anchor-click mechanism
 * `triggerInvoiceDocumentDownload`/`triggerReportDownload` use for their
 * own PDFs (Sprint 12 Session 2 / Sprint 11), reused here rather than
 * duplicated.
 */
export function triggerPurchaseBillDocumentDownload(purchaseBillId: string): void {
  downloadUrl(`/api/purchase/${purchaseBillId}/document`);
}
