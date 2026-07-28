"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { SupplierPaymentForm } from "@/features/supplier-payments/components/supplier-payment-form";
import { useSupplierPayment } from "@/features/supplier-payments/hooks/use-supplier-payment";
import { useUpdateSupplierPayment } from "@/features/supplier-payments/hooks/use-update-supplier-payment";
import {
  toSupplierPaymentFormValues,
  toSupplierPaymentUpdatePayload,
  type SupplierPaymentFormValues,
} from "@/features/supplier-payments/schemas/supplier-payment-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Header-only Edit page (Sprint 9 Session 2). Only `draft` supplier payments
 * may be updated - the backend rejects anything else with a 409
 * `SUPPLIER_PAYMENT_NOT_DRAFT` (app/modules/supplier_payments/service.py's
 * `_ensure_draft`), which surfaces through `SupplierPaymentForm`'s generic
 * error-toast path like any other business-rule conflict; this session
 * doesn't preemptively block the page for a non-draft payment, mirroring
 * `PaymentEditPage`.
 */
export function SupplierPaymentEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const supplierPaymentId = params.id;
  const { hasPermission } = usePermissions();

  const supplierPaymentQuery = useSupplierPayment(supplierPaymentId);
  const updateSupplierPayment = useUpdateSupplierPayment();

  if (!hasPermission("supplier_payment:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit supplier payments"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = supplierPaymentQuery.isError ? normalizeApiError(supplierPaymentQuery.error) : null;

  async function handleSubmit(values: SupplierPaymentFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      await updateSupplierPayment.mutateAsync({
        id: supplierPaymentId,
        payload: toSupplierPaymentUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess("Supplier payment was updated.");
      router.push("/supplier-payments");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is SupplierPaymentForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Supplier Payment"
      description={supplierPaymentQuery.data?.paymentNumber ?? undefined}
      isLoading={supplierPaymentQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load supplier payment record",
              description: apiError.message,
              onRetry: () => supplierPaymentQuery.refetch(),
            }
          : null
      }
    >
      {supplierPaymentQuery.data && (
        <SupplierPaymentForm
          defaultValues={toSupplierPaymentFormValues(supplierPaymentQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/supplier-payments")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
