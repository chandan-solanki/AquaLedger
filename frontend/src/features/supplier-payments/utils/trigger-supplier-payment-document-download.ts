import { downloadUrl } from "@/utils/download-url";

/**
 * Triggers the browser's native download of a supplier payment's
 * receipt PDF via `/api/supplier-payments/{id}/document` - the same
 * anchor-click mechanism `triggerPaymentDocumentDownload`/
 * `triggerInvoiceDocumentDownload` use for their own PDFs (Sprint 12
 * Sessions 2-4), reused here rather than duplicated.
 */
export function triggerSupplierPaymentDocumentDownload(supplierPaymentId: string): void {
  downloadUrl(`/api/supplier-payments/${supplierPaymentId}/document`);
}
