"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { DeliveryChallanForm } from "@/features/delivery-challans/components/delivery-challan-form";
import { useDeliveryChallan } from "@/features/delivery-challans/hooks/use-delivery-challan";
import { useUpdateDeliveryChallan } from "@/features/delivery-challans/hooks/use-update-delivery-challan";
import {
  toDeliveryChallanFormValues,
  toDeliveryChallanUpdatePayload,
  type DeliveryChallanFormValues,
} from "@/features/delivery-challans/schemas/delivery-challan-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Header-only Edit page. Only `draft` delivery challans may be updated - the
 * backend rejects anything else with a 409 `DELIVERY_CHALLAN_NOT_DRAFT`,
 * which surfaces through `DeliveryChallanForm`'s generic error-toast path
 * like any other business-rule conflict; this page doesn't preemptively
 * block itself for a non-draft challan, mirroring `PurchaseOrderEditPage`.
 * The Invoice field is shown (disabled) for context but can never be
 * changed - `invoice_id` is immutable after creation.
 */
export function DeliveryChallanEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const deliveryChallanId = params.id;
  const { hasPermission } = usePermissions();

  const deliveryChallanQuery = useDeliveryChallan(deliveryChallanId);
  const updateDeliveryChallan = useUpdateDeliveryChallan();

  if (!hasPermission("delivery_challan:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit delivery challans"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = deliveryChallanQuery.isError ? normalizeApiError(deliveryChallanQuery.error) : null;

  async function handleSubmit(values: DeliveryChallanFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      await updateDeliveryChallan.mutateAsync({
        id: deliveryChallanId,
        payload: toDeliveryChallanUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess("Delivery challan was updated.");
      router.push(`/delivery-challans/${deliveryChallanId}`);
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is DeliveryChallanForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Delivery Challan"
      description={deliveryChallanQuery.data?.challanNumber ?? undefined}
      isLoading={deliveryChallanQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load delivery challan",
              description: apiError.message,
              onRetry: () => deliveryChallanQuery.refetch(),
            }
          : null
      }
    >
      {deliveryChallanQuery.data && (
        <DeliveryChallanForm
          defaultValues={toDeliveryChallanFormValues(deliveryChallanQuery.data)}
          disableInvoiceSelect
          onSubmit={handleSubmit}
          onCancel={() => router.push(`/delivery-challans/${deliveryChallanId}`)}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
