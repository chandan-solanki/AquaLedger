"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { PurchaseBillForm } from "@/features/purchase-bills/components/purchase-bill-form";
import { useCreatePurchaseBill } from "@/features/purchase-bills/hooks/use-create-purchase-bill";
import {
  toPurchaseBillRequestPayload,
  type PurchaseBillFormValues,
} from "@/features/purchase-bills/schemas/purchase-bill-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * Header-only Create page - a created purchase bill always lands in `draft`
 * status with `bill_number` NULL (numbers are assigned only at posting, not
 * yet wired up on this frontend), so the success toast never references a
 * number. Mirrors `InvoiceCreatePage`.
 */
export function PurchaseBillCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createPurchaseBill = useCreatePurchaseBill();

  if (!hasPermission("purchase:create")) {
    return (
      <ErrorState
        title="You don't have permission to create purchase bills"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: PurchaseBillFormValues) {
    const loadingToastId = toastLoading("Creating purchase bill…");
    try {
      await createPurchaseBill.mutateAsync(toPurchaseBillRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess("Draft purchase bill was created.");
      router.push("/purchase-bills");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is PurchaseBillForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Purchase Bill" description="Create a draft purchase bill for a supplier.">
      <PurchaseBillForm
        onSubmit={handleSubmit}
        onCancel={() => router.push("/purchase-bills")}
        submitLabel="Create Purchase Bill"
      />
    </FormPageTemplate>
  );
}
