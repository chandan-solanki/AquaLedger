"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { SupplierPaymentForm } from "@/features/supplier-payments/components/supplier-payment-form";
import { useCreateSupplierPayment } from "@/features/supplier-payments/hooks/use-create-supplier-payment";
import {
  toSupplierPaymentRequestPayload,
  type SupplierPaymentFormValues,
} from "@/features/supplier-payments/schemas/supplier-payment-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * Header-only Create page (Sprint 9 Session 2) - a created supplier payment
 * always lands in `draft` status with `payment_number` NULL (numbers are
 * assigned only at posting, a later session's workflow), so the success
 * toast never references a number. Mirrors `PaymentCreatePage` exactly.
 */
export function SupplierPaymentCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createSupplierPayment = useCreateSupplierPayment();

  if (!hasPermission("supplier_payment:create")) {
    return (
      <ErrorState
        title="You don't have permission to create supplier payments"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: SupplierPaymentFormValues) {
    const loadingToastId = toastLoading("Creating supplier payment…");
    try {
      await createSupplierPayment.mutateAsync(toSupplierPaymentRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess("Draft supplier payment was created.");
      router.push("/supplier-payments");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is SupplierPaymentForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Supplier Payment" description="Record a payment made to a supplier.">
      <SupplierPaymentForm
        onSubmit={handleSubmit}
        onCancel={() => router.push("/supplier-payments")}
        submitLabel="Create Supplier Payment"
      />
    </FormPageTemplate>
  );
}
