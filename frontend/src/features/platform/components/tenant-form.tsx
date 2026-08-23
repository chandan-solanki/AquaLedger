"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { EmailInput, FormActions, FormField, FormGrid, FormSection } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DEFAULT_TENANT_FORM_VALUES,
  tenantFormSchema,
  type TenantFormValues,
} from "@/features/platform/schemas/tenant-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface TenantFormProps {
  onSubmit: (values: TenantFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * The tenant provisioning form — tenant identity plus its first
 * administrator's credentials, matching TenantCreateRequest exactly (no
 * plan/currency/fiscal-month fields; see tenant.ts's TenantCreateRequest
 * doc comment for why those are out of scope here). Owns its own submit
 * try/catch: a 422's `field_errors` (including nested
 * `administrator.password`) map onto the matching fields, anything else
 * (409 duplicate slug/email/username, network, 5xx) surfaces as a toast.
 *
 * Password fields are never prefilled and are cleared by the caller
 * (`reset()`) once provisioning succeeds - this form is Create-only, there
 * is no Edit flow that would need to repopulate them.
 */
export function TenantForm({ onSubmit, onCancel, submitLabel = "Provision Tenant" }: TenantFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TenantFormValues>({
    resolver: zodResolver(tenantFormSchema),
    defaultValues: DEFAULT_TENANT_FORM_VALUES,
  });

  async function handleFormSubmit(values: TenantFormValues) {
    try {
      await onSubmit(values);
      // Success: clear the password fields immediately rather than leaving
      // them in the DOM/form state even momentarily longer than necessary.
      reset(DEFAULT_TENANT_FORM_VALUES);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<TenantFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Tenant Details">
        <FormGrid columns={2}>
          <FormField label="Tenant Name" required error={errors.name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("name")} />
            )}
          </FormField>

          <FormField
            label="Slug"
            required
            error={errors.slug?.message}
            description="Lowercase letters, numbers and single hyphens, e.g. 'ocean-fresh-traders'."
          >
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                autoComplete="off"
                {...register("slug")}
              />
            )}
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection
        title="Initial Administrator"
        description="This account is created with full administrator access to the new tenant."
      >
        <FormGrid columns={2}>
          <FormField
            label="Full Name"
            required
            error={errors.administrator?.full_name?.message}
            className="md:col-span-full"
          >
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("administrator.full_name")}
              />
            )}
          </FormField>

          <EmailInput
            label="Email"
            required
            error={errors.administrator?.email?.message}
            {...register("administrator.email")}
          />

          <FormField label="Username" required error={errors.administrator?.username?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                autoComplete="off"
                {...register("administrator.username")}
              />
            )}
          </FormField>

          <FormField label="Password" required error={errors.administrator?.password?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                type="password"
                autoComplete="new-password"
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                disabled={isSubmitting}
                {...register("administrator.password")}
              />
            )}
          </FormField>

          <FormField label="Confirm Password" required error={errors.confirm_password?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                type="password"
                autoComplete="new-password"
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                disabled={isSubmitting}
                {...register("confirm_password")}
              />
            )}
          </FormField>
        </FormGrid>
      </FormSection>

      <FormActions
        secondary={
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        }
        primary={
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
            {isSubmitting ? "Provisioning…" : submitLabel}
          </Button>
        }
      />
    </form>
  );
}
