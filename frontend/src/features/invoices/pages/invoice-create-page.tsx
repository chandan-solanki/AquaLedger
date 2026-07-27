"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { InvoiceForm } from "@/features/invoices/components/invoice-form";
import { useCreateInvoice } from "@/features/invoices/hooks/use-create-invoice";
import { toInvoiceRequestPayload, type InvoiceFormValues } from "@/features/invoices/schemas/invoice-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * Header-only Create page (Sprint 7 Session 2) - a created invoice always
 * lands in `draft` status with `invoice_number` NULL (numbers are assigned
 * only at issue, a later session's workflow), so the success toast never
 * references a number.
 */
export function InvoiceCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createInvoice = useCreateInvoice();

  if (!hasPermission("invoice:create")) {
    return (
      <ErrorState
        title="You don't have permission to create invoices"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: InvoiceFormValues) {
    const loadingToastId = toastLoading("Creating invoice…");
    try {
      await createInvoice.mutateAsync(toInvoiceRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess("Draft invoice was created.");
      router.push("/invoices");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is InvoiceForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Invoice" description="Create a draft invoice for a company.">
      <InvoiceForm onSubmit={handleSubmit} onCancel={() => router.push("/invoices")} submitLabel="Create Invoice" />
    </FormPageTemplate>
  );
}
