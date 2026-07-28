"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { SupplierForm } from "@/features/suppliers/components/supplier-form";
import { useCreateSupplier } from "@/features/suppliers/hooks/use-create-supplier";
import {
  toSupplierRequestPayload,
  type SupplierFormValues,
} from "@/features/suppliers/schemas/supplier-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

export function SupplierCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createSupplier = useCreateSupplier();

  if (!hasPermission("supplier:create")) {
    return (
      <ErrorState
        title="You don't have permission to create suppliers"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: SupplierFormValues) {
    const loadingToastId = toastLoading("Creating supplier…");
    try {
      const supplier = await createSupplier.mutateAsync(toSupplierRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess(`${supplier.name} was created.`);
      router.push("/suppliers");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is SupplierForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Supplier" description="Add a supplier you purchase fish or goods from.">
      <SupplierForm
        onSubmit={handleSubmit}
        onCancel={() => router.push("/suppliers")}
        submitLabel="Create Supplier"
      />
    </FormPageTemplate>
  );
}
