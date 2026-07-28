import type { SupplierPaymentListParams } from "@/features/supplier-payments/types/supplier-payment";

export const supplierPaymentKeys = {
  all: () => ["supplier-payments"] as const,
  lists: () => [...supplierPaymentKeys.all(), "list"] as const,
  list: (params: SupplierPaymentListParams) => [...supplierPaymentKeys.lists(), params] as const,
  details: () => [...supplierPaymentKeys.all(), "detail"] as const,
  detail: (id: string) => [...supplierPaymentKeys.details(), id] as const,
};

/**
 * Supplier payment allocations are only ever listed one way - every
 * allocation on one supplier payment (`GET /supplier-payments/{id}/
 * allocations`, no pagination) - so this has a single `byPayment` entry
 * rather than the fuller `list(params)` shape `supplierPaymentKeys` needs
 * for its filterable List page, mirroring `paymentAllocationKeys`.
 */
export const supplierPaymentAllocationKeys = {
  all: () => ["supplier-payment-allocations"] as const,
  byPayment: (supplierPaymentId: string) =>
    [...supplierPaymentAllocationKeys.all(), "payment", supplierPaymentId] as const,
};
