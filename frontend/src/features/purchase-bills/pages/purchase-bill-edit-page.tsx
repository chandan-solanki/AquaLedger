"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { PurchaseBillForm } from "@/features/purchase-bills/components/purchase-bill-form";
import { usePurchaseBill } from "@/features/purchase-bills/hooks/use-purchase-bill";
import { useUpdatePurchaseBill } from "@/features/purchase-bills/hooks/use-update-purchase-bill";
import {
  toPurchaseBillFormValues,
  toPurchaseBillUpdatePayload,
  type PurchaseBillFormValues,
} from "@/features/purchase-bills/schemas/purchase-bill-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Header-only Edit page. Only `draft` purchase bills may be updated - the
 * backend rejects anything else with a 409 `PURCHASE_BILL_NOT_DRAFT`
 * (app/modules/purchase/service.py's `_ensure_draft`), which surfaces
 * through `PurchaseBillForm`'s generic error-toast path like any other
 * business-rule conflict; this page doesn't preemptively block itself for
 * a non-draft bill, mirroring `InvoiceEditPage`.
 */
export function PurchaseBillEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const purchaseBillId = params.id;
  const { hasPermission } = usePermissions();

  const purchaseBillQuery = usePurchaseBill(purchaseBillId);
  const updatePurchaseBill = useUpdatePurchaseBill();

  if (!hasPermission("purchase:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit purchase bills"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = purchaseBillQuery.isError ? normalizeApiError(purchaseBillQuery.error) : null;

  async function handleSubmit(values: PurchaseBillFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      await updatePurchaseBill.mutateAsync({
        id: purchaseBillId,
        payload: toPurchaseBillUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess("Purchase bill was updated.");
      router.push("/purchase-bills");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is PurchaseBillForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Purchase Bill"
      description={purchaseBillQuery.data?.billNumber ?? undefined}
      isLoading={purchaseBillQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load purchase bill",
              description: apiError.message,
              onRetry: () => purchaseBillQuery.refetch(),
            }
          : null
      }
    >
      {purchaseBillQuery.data && (
        <PurchaseBillForm
          defaultValues={toPurchaseBillFormValues(purchaseBillQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/purchase-bills")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
