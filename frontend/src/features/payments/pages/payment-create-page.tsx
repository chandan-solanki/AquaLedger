"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { PaymentForm } from "@/features/payments/components/payment-form";
import { useCreatePayment } from "@/features/payments/hooks/use-create-payment";
import { toPaymentRequestPayload, type PaymentFormValues } from "@/features/payments/schemas/payment-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * Header-only Create page (Sprint 8 Session 2) - a created payment always
 * lands in `draft` status with `payment_number` NULL (numbers are assigned
 * only at posting, a later session's workflow), so the success toast never
 * references a number.
 */
export function PaymentCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createPayment = useCreatePayment();

  if (!hasPermission("payment:create")) {
    return (
      <ErrorState
        title="You don't have permission to create payments"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: PaymentFormValues) {
    const loadingToastId = toastLoading("Creating payment…");
    try {
      await createPayment.mutateAsync(toPaymentRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess("Draft payment was created.");
      router.push("/payments");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is PaymentForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Payment" description="Record a payment received from a customer.">
      <PaymentForm onSubmit={handleSubmit} onCancel={() => router.push("/payments")} submitLabel="Create Payment" />
    </FormPageTemplate>
  );
}
