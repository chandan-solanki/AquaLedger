import { downloadUrl } from "@/utils/download-url";

/**
 * Triggers the browser's native download of an invoice's PDF via
 * `/api/invoices/{id}/document` - the same anchor-click mechanism
 * `triggerReportDownload`/`triggerStatementDownload` use for report/
 * statement PDFs (Sprint 11), reused here rather than duplicated
 * (Sprint 12 Session 2).
 */
export function triggerInvoiceDocumentDownload(invoiceId: string): void {
  downloadUrl(`/api/invoices/${invoiceId}/document`);
}
