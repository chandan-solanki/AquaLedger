"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { PurchaseOrderForm } from "@/features/purchase-orders/components/purchase-order-form";
import { useCreatePurchaseOrder } from "@/features/purchase-orders/hooks/use-create-purchase-order";
import {
  toPurchaseOrderRequestPayload,
  type PurchaseOrderFormValues,
} from "@/features/purchase-orders/schemas/purchase-order-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * Header-only Create page - a created purchase order always lands in
 * `draft` status with `po_number` NULL (numbers are assigned only at
 * confirm), so the success toast never references a number. Mirrors
 * `PurchaseBillCreatePage`.
 */
export function PurchaseOrderCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createPurchaseOrder = useCreatePurchaseOrder();

  if (!hasPermission("purchase_order:create")) {
    return (
      <ErrorState
        title="You don't have permission to create purchase orders"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: PurchaseOrderFormValues) {
    const loadingToastId = toastLoading("Creating purchase order…");
    try {
      await createPurchaseOrder.mutateAsync(toPurchaseOrderRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess("Draft purchase order was created.");
      router.push("/purchase-orders");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is PurchaseOrderForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Purchase Order" description="Create a draft purchase order for a supplier.">
      <PurchaseOrderForm
        onSubmit={handleSubmit}
        onCancel={() => router.push("/purchase-orders")}
        submitLabel="Create Purchase Order"
      />
    </FormPageTemplate>
  );
}
