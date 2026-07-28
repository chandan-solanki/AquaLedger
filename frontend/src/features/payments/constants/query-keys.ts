import type { PaymentListParams } from "@/features/payments/types/payment";

export const paymentKeys = {
  all: () => ["payments"] as const,
  lists: () => [...paymentKeys.all(), "list"] as const,
  list: (params: PaymentListParams) => [...paymentKeys.lists(), params] as const,
  details: () => [...paymentKeys.all(), "detail"] as const,
  detail: (id: string) => [...paymentKeys.details(), id] as const,
};

/**
 * Payment allocations are only ever listed one way - every allocation on
 * one payment (`GET /payments/{payment_id}/allocations`, no pagination) - so
 * this has a single `byPayment` entry rather than the fuller `list(params)`
 * shape `paymentKeys` needs for its filterable List page, mirroring
 * `invoiceItemKeys`'s `byInvoice` shape.
 */
export const paymentAllocationKeys = {
  all: () => ["payment-allocations"] as const,
  byPayment: (paymentId: string) => [...paymentAllocationKeys.all(), "payment", paymentId] as const,
};
