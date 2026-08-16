"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { DeliveryChallanForm } from "@/features/delivery-challans/components/delivery-challan-form";
import { useCreateDeliveryChallan } from "@/features/delivery-challans/hooks/use-create-delivery-challan";
import {
  toDeliveryChallanRequestPayload,
  type DeliveryChallanFormValues,
} from "@/features/delivery-challans/schemas/delivery-challan-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * Header-only Create page - a created delivery challan always lands in
 * `draft` status with `challan_number` NULL (numbers are assigned only at
 * dispatch), so the success toast never references a number. Line items are
 * added afterward on the Detail page, mirroring `PurchaseOrderCreatePage`.
 */
export function DeliveryChallanCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createDeliveryChallan = useCreateDeliveryChallan();

  if (!hasPermission("delivery_challan:create")) {
    return (
      <ErrorState
        title="You don't have permission to create delivery challans"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: DeliveryChallanFormValues) {
    const loadingToastId = toastLoading("Creating delivery challan…");
    try {
      const challan = await createDeliveryChallan.mutateAsync(toDeliveryChallanRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess("Draft delivery challan was created.");
      router.push(`/delivery-challans/${challan.id}`);
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is DeliveryChallanForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="New Delivery Challan"
      description="Record a draft delivery challan against an issued invoice."
    >
      <DeliveryChallanForm
        onSubmit={handleSubmit}
        onCancel={() => router.push("/delivery-challans")}
        submitLabel="Create Delivery Challan"
      />
    </FormPageTemplate>
  );
}
