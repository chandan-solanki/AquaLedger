"use client";

import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { CompanyForm } from "@/features/companies/components/company-form";
import { useCompany } from "@/features/companies/hooks/use-company";
import { useUpdateCompany } from "@/features/companies/hooks/use-update-company";
import {
  toCompanyFormValues,
  toCompanyUpdatePayload,
  type CompanyFormValues,
} from "@/features/companies/schemas/company-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export function CompanyEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const companyId = params.id;
  const { hasPermission } = usePermissions();

  const companyQuery = useCompany(companyId);
  const updateCompany = useUpdateCompany();

  if (!hasPermission("company:edit")) {
    return (
      <ErrorState
        title="You don't have permission to edit companies"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const apiError = companyQuery.isError ? normalizeApiError(companyQuery.error) : null;

  async function handleSubmit(values: CompanyFormValues) {
    const loadingToastId = toastLoading("Saving changes…");
    try {
      const company = await updateCompany.mutateAsync({
        id: companyId,
        payload: toCompanyUpdatePayload(values),
      });
      dismissToast(loadingToastId);
      toastSuccess(`${company.name} was updated.`);
      router.push("/companies");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is CompanyForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate
      title="Edit Company"
      description={companyQuery.data?.name}
      isLoading={companyQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load company",
              description: apiError.message,
              onRetry: () => companyQuery.refetch(),
            }
          : null
      }
    >
      {companyQuery.data && (
        <CompanyForm
          defaultValues={toCompanyFormValues(companyQuery.data)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/companies")}
          submitLabel="Save Changes"
        />
      )}
    </FormPageTemplate>
  );
}
