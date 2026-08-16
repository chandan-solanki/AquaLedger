"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { PurchaseOrderForm } from "@/features/purchase-orders/components/purchase-order-form";
import { usePurchaseOrder } from "@/features/purchase-orders/hooks/use-purchase-order";
import { useUpdatePurchaseOrder } from "@/features/purchase-orders/hooks/use-update-purchase-order";
import {
  toPurchaseOrderFormValues,
  toPurchaseOrderUpdatePayload,
  type PurchaseOrderFormValues,
} from "@/features/purchase-orders/schemas/purchase-order-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Header-only Edit page. Only `draft` purchase orders may be updated - the
 * backend rejects anything else with a 409 `PURCHASE_ORDER_NOT_DRAFT`,
 * which surfaces through `PurchaseOrderForm`'s generic error-toast path
 * like any other business-rule conflict; this page doesn't preemptively
 * block itself for a non-draft order, mirroring `PurchaseBillEditPage`.
 */
export function PurchaseOrderEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const purchaseOrderId = params.id;
  const { hasPermission } = usePermissions();

  const purchaseOrderQuery = usePurchaseOrder(purchaseOrderId);
  const updatePurchaseOrder = useUpdatePurchaseOrder();

  if (!hasPermission("purchase_order:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit purchase orders"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = purchaseOrderQuery.isError ? normalizeApiError(purchaseOrderQuery.error) : null;

  async function handleSubmit(values: PurchaseOrderFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      await updatePurchaseOrder.mutateAsync({
        id: purchaseOrderId,
        payload: toPurchaseOrderUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess("Purchase order was updated.");
      router.push("/purchase-orders");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is PurchaseOrderForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Purchase Order"
      description={purchaseOrderQuery.data?.poNumber ?? undefined}
      isLoading={purchaseOrderQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load purchase order",
              description: apiError.message,
              onRetry: () => purchaseOrderQuery.refetch(),
            }
          : null
      }
    >
      {purchaseOrderQuery.data && (
        <PurchaseOrderForm
          defaultValues={toPurchaseOrderFormValues(purchaseOrderQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/purchase-orders")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
