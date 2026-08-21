"use client";

import { useRouter, useSearchParams } from "next/navigation";

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
 *
 * Sprint 15 Session 4: an optional `?tripCatchId=` query param carries a
 * specific catch chosen from the Fish Stock detail page's "Create Invoice"
 * action. This page never selects a customer or line item itself - it only
 * forwards the id to the newly-created invoice's Detail page, which opens
 * the Add Item dialog pre-filled with that catch (`InvoiceItemTable`).
 */
export function InvoiceCreatePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefillTripCatchId = searchParams.get("tripCatchId") ?? undefined;
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
      const invoice = await createInvoice.mutateAsync(toInvoiceRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess("Draft invoice was created.");
      router.push(
        prefillTripCatchId ? `/invoices/${invoice.id}?openItem=${prefillTripCatchId}` : "/invoices"
      );
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
