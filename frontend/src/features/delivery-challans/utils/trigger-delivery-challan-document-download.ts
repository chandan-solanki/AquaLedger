import { downloadUrl } from "@/utils/download-url";

export function triggerDeliveryChallanDocumentDownload(deliveryChallanId: string): void {
  downloadUrl(`/api/delivery-challans/${deliveryChallanId}/document`);
}
