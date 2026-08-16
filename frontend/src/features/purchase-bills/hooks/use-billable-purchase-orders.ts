"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { purchaseOrderKeys, purchaseOrderService } from "@/features/purchase-orders";

const PAGE_SIZE = 100;

/**
 * Confirmed/fulfilled purchase orders for one supplier (Sprint 12 Session
 * 12) - the pool a Purchase Bill can legally link to
 * (app/modules/purchase/service.py's `_validate_purchase_order_link`
 * rejects DRAFT/CANCELLED orders with a 422). Reuses the existing `GET
 * /purchase-orders` list endpoint via its `billable=true` filter (Sprint 12
 * Session 13 - app/modules/purchase_orders/repository.py's `search`
 * restricts to CONFIRMED/FULFILLED server-side) rather than a new search
 * API. Filtering server-side, not in the browser, matters here: a supplier
 * with many draft/cancelled orders ahead of its confirmed/fulfilled ones in
 * `-created_at` order could otherwise have real billable orders pushed off
 * a fixed-size page before the client ever sees them. `page_size` stays a
 * generous flat bound (not full pagination) since one supplier's own
 * billable-order count is still small in practice.
 *
 * Disabled until a supplier id is available - mirrors every other
 * supplier-scoped picker in this codebase (`useSupplierOptions` etc.).
 */
export function useBillablePurchaseOrders(supplierId: string | undefined) {
  const params = {
    supplier_id: supplierId,
    billable: true,
    sort: "-created_at",
    page: 1,
    page_size: PAGE_SIZE,
  };

  const query = useQuery({
    queryKey: purchaseOrderKeys.list(params),
    queryFn: () => purchaseOrderService.listPurchaseOrders(params),
    enabled: Boolean(supplierId),
  });

  const orders = query.data?.data;

  return useMemo(() => {
    const billable = orders ?? [];
    return {
      options: billable.map(
        (order): ComboboxOption => ({
          value: order.id,
          label: order.poNumber ?? order.id,
        })
      ),
      orders: billable,
      isLoading: query.isLoading,
    };
  }, [orders, query.isLoading]);
}
