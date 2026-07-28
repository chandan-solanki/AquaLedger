"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { PaymentForm } from "@/features/payments/components/payment-form";
import { usePayment } from "@/features/payments/hooks/use-payment";
import { useUpdatePayment } from "@/features/payments/hooks/use-update-payment";
import {
  toPaymentFormValues,
  toPaymentUpdatePayload,
  type PaymentFormValues,
} from "@/features/payments/schemas/payment-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Header-only Edit page (Sprint 8 Session 2). Only `draft` payments may be
 * updated - the backend rejects anything else with a 409 `PAYMENT_NOT_DRAFT`
 * (app/modules/payments/service.py's `_ensure_draft`), which surfaces
 * through `PaymentForm`'s generic error-toast path like any other business-
 * rule conflict; this session doesn't preemptively block the page for a
 * non-draft payment, mirroring `InvoiceEditPage`.
 */
export function PaymentEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const paymentId = params.id;
  const { hasPermission } = usePermissions();

  const paymentQuery = usePayment(paymentId);
  const updatePayment = useUpdatePayment();

  if (!hasPermission("payment:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit payments"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = paymentQuery.isError ? normalizeApiError(paymentQuery.error) : null;

  async function handleSubmit(values: PaymentFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      await updatePayment.mutateAsync({ id: paymentId, payload: toPaymentUpdatePayload(values) });
      dismissToast(loadingToastId);
      toastSuccess("Payment was updated.");
      router.push("/payments");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is PaymentForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Payment"
      description={paymentQuery.data?.paymentNumber ?? undefined}
      isLoading={paymentQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load payment record",
              description: apiError.message,
              onRetry: () => paymentQuery.refetch(),
            }
          : null
      }
    >
      {paymentQuery.data && (
        <PaymentForm
          defaultValues={toPaymentFormValues(paymentQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/payments")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
