import type { PurchaseBillListParams } from "@/features/purchase-bills/types/purchase-bill";

export const purchaseBillKeys = {
  all: () => ["purchase-bills"] as const,
  lists: () => [...purchaseBillKeys.all(), "list"] as const,
  list: (params: PurchaseBillListParams) => [...purchaseBillKeys.lists(), params] as const,
  details: () => [...purchaseBillKeys.all(), "detail"] as const,
  detail: (id: string) => [...purchaseBillKeys.details(), id] as const,
};

/**
 * Purchase bill items are only ever listed one way - every item on one
 * purchase bill (`GET /purchase/{id}/items`, no pagination) - so this has a
 * single `byBill` entry rather than the fuller `list(params)` shape
 * `purchaseBillKeys` needs for its filterable List page, mirroring
 * `invoiceItemKeys`'s `byInvoice` shape.
 */
export const purchaseBillItemKeys = {
  all: () => ["purchase-bill-items"] as const,
  byBill: (purchaseBillId: string) => [...purchaseBillItemKeys.all(), "bill", purchaseBillId] as const,
};
