import { downloadUrl } from "@/utils/download-url";

export function triggerPurchaseOrderDocumentDownload(purchaseOrderId: string): void {
  downloadUrl(`/api/purchase-orders/${purchaseOrderId}/document`);
}
