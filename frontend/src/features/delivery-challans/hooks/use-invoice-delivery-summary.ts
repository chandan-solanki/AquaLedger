"use client";

import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";

import { useInvoiceItems } from "@/features/invoices";
import type { InvoiceItem } from "@/features/invoices";
import { deliveryChallanItemKeys, deliveryChallanKeys } from "@/features/delivery-challans/constants/query-keys";
import { deliveryChallanItemService } from "@/features/delivery-challans/services/delivery-challan-item-service";
import { deliveryChallanService } from "@/features/delivery-challans/services/delivery-challan-service";
import type { DeliveryChallanListParams } from "@/features/delivery-challans/types/delivery-challan";

export interface InvoiceItemDeliverySummary {
  invoiceItem: InvoiceItem;
  /** Total quantity delivered against this invoice item across every non-cancelled delivery challan (this one included). */
  deliveredQuantity: number;
  /** `invoiceItem.quantity` minus `deliveredQuantity` - a UX guard only, never authoritative (see this hook's own docstring). */
  remainingQuantity: number;
}

/**
 * Per-invoice-item delivered/remaining quantities, computed entirely
 * client-side from existing endpoints - the backend exposes no dedicated
 * "invoice items with delivery summary" endpoint (unlike
 * `GET /purchase-orders/{id}/items`'s own `billed_quantity`/
 * `remaining_quantity`), even though the delivery_challans repository
 * already carries the exact aggregation this needs
 * (`sum_delivered_by_invoice_items`) - it is simply never wired to an
 * endpoint, since Session 14's scope was the backend lifecycle foundation,
 * not this UI. Rather than extend that already-complete, already-tested
 * backend foundation for a read-only convenience this session's own brief
 * says to build the frontend around instead, this hook reconstructs the
 * same result from three already-public endpoints: every item on the
 * invoice (`GET /invoices/{id}/items`), every non-deleted delivery challan
 * against it regardless of status (`GET /delivery-challans?invoice_id=`),
 * and each of those challans' own items - excluding CANCELLED challans,
 * mirroring the repository's own exclusion exactly.
 *
 * This is a UX guard only, same posture as every other quantity check in
 * this feature's forms: the backend's own `_validate_invoice_item_link`
 * re-runs the identical check, authoritatively, on every add/update.
 *
 * Bounded, not unbounded N+1: a challan's own line count and an invoice's
 * own challan count are both small (the same "small and bounded" posture
 * the backend's own docstrings assume throughout this module), so this is a
 * handful of parallel requests, never one per row of a large list.
 */
export function useInvoiceDeliverySummary(invoiceId: string | undefined) {
  const invoiceItemsQuery = useInvoiceItems(invoiceId);

  const challanListParams: DeliveryChallanListParams = {
    invoice_id: invoiceId,
    sort: "-created_at",
    page: 1,
    page_size: 100,
  };
  const challansQuery = useQuery({
    queryKey: deliveryChallanKeys.list(challanListParams),
    queryFn: () => deliveryChallanService.listDeliveryChallans(challanListParams),
    enabled: Boolean(invoiceId),
  });

  const relevantChallanIds = useMemo(
    () => (challansQuery.data?.data ?? []).filter((challan) => challan.status !== "cancelled").map((challan) => challan.id),
    [challansQuery.data]
  );

  const itemQueries = useQueries({
    queries: relevantChallanIds.map((challanId) => ({
      queryKey: deliveryChallanItemKeys.byChallan(challanId),
      queryFn: () => deliveryChallanItemService.listDeliveryChallanItems(challanId),
    })),
  });

  const isLoading =
    invoiceItemsQuery.isLoading || challansQuery.isLoading || itemQueries.some((query) => query.isLoading);

  const summaries = useMemo<InvoiceItemDeliverySummary[]>(() => {
    const deliveredByInvoiceItemId = new Map<string, number>();
    for (const query of itemQueries) {
      for (const item of query.data ?? []) {
        deliveredByInvoiceItemId.set(
          item.invoiceItemId,
          (deliveredByInvoiceItemId.get(item.invoiceItemId) ?? 0) + Number(item.quantity)
        );
      }
    }
    return (invoiceItemsQuery.data ?? []).map((invoiceItem) => {
      const deliveredQuantity = deliveredByInvoiceItemId.get(invoiceItem.id) ?? 0;
      return {
        invoiceItem,
        deliveredQuantity,
        remainingQuantity: Number(invoiceItem.quantity) - deliveredQuantity,
      };
    });
    // itemQueries' data is read directly above; its own array identity is not a meaningful dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoiceItemsQuery.data, itemQueries.map((query) => query.dataUpdatedAt).join(",")]);

  return { summaries, isLoading };
}
