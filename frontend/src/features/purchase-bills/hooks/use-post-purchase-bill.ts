"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supplierKeys } from "@/features/suppliers";
import { purchaseBillKeys } from "@/features/purchase-bills/constants/query-keys";
import { purchaseBillService } from "@/features/purchase-bills/services/purchase-bill-service";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Post is the purchase bill module's one true business transaction
 * (app/modules/purchase/service.py's `PurchaseService.post`, mirroring
 * `useIssueInvoice`): `draft` -> `posted`, irreversible. The backend
 * assigns `bill_number`, recalculates all totals from the bill's current
 * items, and increases the billing supplier's `outstanding_amount` by
 * `balance_amount`, all inside one transaction - nothing is computed here,
 * only invalidated, so the next read shows the server's own numbers.
 *
 * Invalidation reaches beyond this bill: `supplierKeys.detail` for the
 * exact billing supplier (known from the mutation's own return value) -
 * unlike Supplier Payment's own `post` (which touches nothing outside
 * itself), Purchase Bill's `post` has a real side effect on Supplier data,
 * the same way Invoice's `issue` reaches into Company.
 */
export function usePostPurchaseBill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => purchaseBillService.postPurchaseBill(id),
    onSuccess: (bill) => {
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.detail(bill.id) });
      queryClient.invalidateQueries({ queryKey: purchaseBillKeys.lists() });
      queryClient.invalidateQueries({ queryKey: supplierKeys.detail(bill.supplierId) });
      toastSuccess(bill.billNumber ? `${bill.billNumber} posted.` : "Purchase bill posted.");
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
