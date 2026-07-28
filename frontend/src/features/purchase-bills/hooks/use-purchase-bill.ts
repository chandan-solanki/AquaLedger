"use client";

import { useQuery } from "@tanstack/react-query";

import { purchaseBillKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillService } from "@/features/purchase-bills/services/purchase-bill-service";

/** A single purchase bill by id - disabled until an id is available. */
export function usePurchaseBill(id: string | undefined) {
  return useQuery({
    queryKey: purchaseBillKeys.detail(id ?? ""),
    queryFn: () => purchaseBillService.getPurchaseBill(id as string),
    enabled: Boolean(id),
  });
}
