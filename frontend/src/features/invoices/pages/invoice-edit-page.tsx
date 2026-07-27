"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { InvoiceForm } from "@/features/invoices/components/invoice-form";
import { useInvoice } from "@/features/invoices/hooks/use-invoice";
import { useUpdateInvoice } from "@/features/invoices/hooks/use-update-invoice";
import {
  toInvoiceFormValues,
  toInvoiceUpdatePayload,
  type InvoiceFormValues,
} from "@/features/invoices/schemas/invoice-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

/**
 * Header-only Edit page (Sprint 7 Session 2). Only `draft` invoices may be
 * updated - the backend rejects anything else with a 409 `INVOICE_NOT_DRAFT`
 * (app/modules/invoices/service.py's `_ensure_draft`), which surfaces
 * through `InvoiceForm`'s generic error-toast path like any other business-
 * rule conflict; this session doesn't preemptively block the page for a
 * non-draft invoice, mirroring how `TripEditPage` leaves equivalent
 * state-machine guards server-validated only.
 */
export function InvoiceEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const invoiceId = params.id;
  const { hasPermission } = usePermissions();

  const invoiceQuery = useInvoice(invoiceId);
  const updateInvoice = useUpdateInvoice();

  if (!hasPermission("invoice:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit invoices"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = invoiceQuery.isError ? normalizeApiError(invoiceQuery.error) : null;

  async function handleSubmit(values: InvoiceFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      await updateInvoice.mutateAsync({ id: invoiceId, payload: toInvoiceUpdatePayload(values) });
      dismissToast(loadingToastId);
      toastSuccess("Invoice was updated.");
      router.push("/invoices");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is InvoiceForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Invoice"
      description={invoiceQuery.data?.invoiceNumber ?? undefined}
      isLoading={invoiceQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load invoice record",
              description: apiError.message,
              onRetry: () => invoiceQuery.refetch(),
            }
          : null
      }
    >
      {invoiceQuery.data && (
        <InvoiceForm
          defaultValues={toInvoiceFormValues(invoiceQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/invoices")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
