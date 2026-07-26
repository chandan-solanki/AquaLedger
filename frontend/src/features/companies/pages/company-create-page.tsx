"use client";

import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/feedback/error-state";
import { FormPageTemplate } from "@/components/templates/form-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { CompanyForm } from "@/features/companies/components/company-form";
import { useCreateCompany } from "@/features/companies/hooks/use-create-company";
import {
  toCompanyRequestPayload,
  type CompanyFormValues,
} from "@/features/companies/schemas/company-form-schema";
import { dismissToast, toastLoading, toastSuccess } from "@/lib/toast";

export function CompanyCreatePage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const createCompany = useCreateCompany();

  if (!hasPermission("company:create")) {
    return (
      <ErrorState
        title="You don't have permission to create companies"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  async function handleSubmit(values: CompanyFormValues) {
    const loadingToastId = toastLoading("Creating company…");
    try {
      const company = await createCompany.mutateAsync(toCompanyRequestPayload(values));
      dismissToast(loadingToastId);
      toastSuccess(`${company.name} was created.`);
      router.push("/companies");
    } catch (error) {
      dismissToast(loadingToastId);
      // Field-error mapping / the failure toast is CompanyForm's own job.
      throw error;
    }
  }

  return (
    <FormPageTemplate title="New Company" description="Add a customer, supplier, or trading partner.">
      <CompanyForm
        onSubmit={handleSubmit}
        onCancel={() => router.push("/companies")}
        submitLabel="Create Company"
      />
    </FormPageTemplate>
  );
}
