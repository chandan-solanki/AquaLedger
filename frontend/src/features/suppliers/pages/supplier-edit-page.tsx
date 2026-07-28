"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { SupplierForm } from "@/features/suppliers/components/supplier-form";
import { useSupplier } from "@/features/suppliers/hooks/use-supplier";
import { useUpdateSupplier } from "@/features/suppliers/hooks/use-update-supplier";
import {
  toSupplierFormValues,
  toSupplierUpdatePayload,
  type SupplierFormValues,
} from "@/features/suppliers/schemas/supplier-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export function SupplierEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const supplierId = params.id;
  const { hasPermission } = usePermissions();

  const supplierQuery = useSupplier(supplierId);
  const updateSupplier = useUpdateSupplier();

  if (!hasPermission("supplier:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit suppliers"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = supplierQuery.isError ? normalizeApiError(supplierQuery.error) : null;

  async function handleSubmit(values: SupplierFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      const supplier = await updateSupplier.mutateAsync({
        id: supplierId,
        payload: toSupplierUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess(`${supplier.name} was updated.`);
      router.push("/suppliers");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is SupplierForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Supplier"
      description={supplierQuery.data?.name}
      isLoading={supplierQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load supplier",
              description: apiError.message,
              onRetry: () => supplierQuery.refetch(),
            }
          : null
      }
    >
      {supplierQuery.data && (
        <SupplierForm
          defaultValues={toSupplierFormValues(supplierQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/suppliers")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
