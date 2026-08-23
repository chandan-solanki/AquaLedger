"use client";

import { useRouter } from "next/navigation";

import { FormPageTemplate } from "@/components/templates/form-page-template";
import { TenantForm } from "@/features/platform/components/tenant-form";
import { useCreateTenant } from "@/features/platform/hooks/use-create-tenant";
import {
  toTenantCreateRequestPayload,
  type TenantFormValues,
} from "@/features/platform/schemas/tenant-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

/**
 * Tenant provisioning is one atomic backend operation (tenant + system
 * roles + initial administrator + audit entry, all-or-nothing) — this page
 * only has to submit the form and route to the result, the same shape as
 * CompanyCreatePage/UserCreatePage. No permission check here: the whole
 * `/platform/*` subtree is already gated by `PlatformGuard`
 * (`isPlatformAdmin`), not a permission code.
 */
export function PlatformTenantCreatePage() {
  const router = useRouter();
  const createTenant = useCreateTenant();

  async function handleSubmit(values: TenantFormValues) {
    const loadingToastId = toastLoading("Provisioning tenant…");
    try {
      const result = await createTenant.mutateAsync(toTenantCreateRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess(`${result.tenant.name} was provisioned.`);
      router.push(`/platform/tenants/${result.tenant.id}`);
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is TenantForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="New Tenant"
      description="Provision a tenant with its system roles and initial administrator."
    >
      <TenantForm
        onSubmit={handleSubmit}
        onCancel={() => router.push("/platform/tenants")}
        submitLabel="Provision Tenant"
      />
    </FormPageTemplate>
  );
}
