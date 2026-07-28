"use client";

import { useQuery } from "@tanstack/react-query";

import { purchaseBillItemKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillItemService } from "@/features/purchase-bills/services/purchase-bill-item-service";

/**
 * Every line item on one purchase bill - disabled until a purchase bill id
 * is available. No pagination (`GET /purchase/{id}/items` returns a plain
 * array - see `purchase-bill-item-service.ts`), so the Detail page's Items
 * section fetches and renders the whole set at once, mirroring
 * `useInvoiceItems`.
 */
export function usePurchaseBillItems(purchaseBillId: string | undefined) {
  return useQuery({
    queryKey: purchaseBillItemKeys.byBill(purchaseBillId ?? ""),
    queryFn: () => purchaseBillItemService.listPurchaseBillItems(purchaseBillId as string),
    enabled: Boolean(purchaseBillId),
  });
}
