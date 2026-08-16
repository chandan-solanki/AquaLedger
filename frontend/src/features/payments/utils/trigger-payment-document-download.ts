import { downloadUrl } from "@/utils/download-url";

/**
 * Triggers the browser's native download of a customer payment's
 * receipt PDF via `/api/payments/{id}/document` - the same anchor-click
 * mechanism `triggerInvoiceDocumentDownload`/`triggerPurchaseBillDocumentDownload`
 * use for their own PDFs (Sprint 12 Sessions 2-3), reused here rather
 * than duplicated.
 */
export function triggerPaymentDocumentDownload(paymentId: string): void {
  downloadUrl(`/api/payments/${paymentId}/document`);
}
