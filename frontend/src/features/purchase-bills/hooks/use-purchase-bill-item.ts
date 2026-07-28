"use client";

import { useQuery } from "@tanstack/react-query";

import { purchaseBillItemKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillItemService } from "@/features/purchase-bills/services/purchase-bill-item-service";

/**
 * A single line item, derived from the same list query `usePurchaseBillItems`
 * reads (`GET /purchase/{purchase_bill_id}/items`) - the backend exposes no
 * single-item GET endpoint (only list/create/update/delete, see
 * app/modules/purchase/router.py), so this shares that hook's exact
 * queryKey/queryFn (TanStack Query dedupes the request rather than issuing
 * a second one) and selects one row by id, mirroring `useInvoiceItem`. Used
 * by `PurchaseBillItemTable` to populate the Edit dialog from the freshest
 * cached list data for the row the user clicked.
 */
export function usePurchaseBillItem(purchaseBillId: string | undefined, itemId: string | undefined) {
  return useQuery({
    queryKey: purchaseBillItemKeys.byBill(purchaseBillId ?? ""),
    queryFn: () => purchaseBillItemService.listPurchaseBillItems(purchaseBillId as string),
    enabled: Boolean(purchaseBillId),
    select: (items) => items.find((item) => item.id === itemId),
  });
}
