"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import {
  EmailInput,
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  GSTINInput,
  PANInput,
  PhoneInput,
} from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  companyProfileFormSchema,
  DEFAULT_COMPANY_PROFILE_FORM_VALUES,
  type CompanyProfileFormValues,
} from "@/features/company-profile/schemas/company-profile-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface CompanyProfileFormProps {
  defaultValues: CompanyProfileFormValues;
  onSubmit: (values: CompanyProfileFormValues) => Promise<void>;
  disabled?: boolean;
}

/**
 * The Company Profile form - a single-record settings screen (no Create/
 * Edit split, PUT-only), organized into the sections the sprint brief calls
 * for: Identity, Contact, Address, Tax & Registration. Composed from the
 * same Sprint 2 enterprise form primitives `CompanyForm` uses, and owns its
 * own submit try/catch the same way (422 field errors map onto the
 * matching field, anything else surfaces as a toast).
 */
export function CompanyProfileForm({ defaultValues, onSubmit, disabled = false }: CompanyProfileFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<CompanyProfileFormValues>({
    resolver: zodResolver(companyProfileFormSchema),
    defaultValues: defaultValues ?? DEFAULT_COMPANY_PROFILE_FORM_VALUES,
  });

  async function handleFormSubmit(values: CompanyProfileFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<CompanyProfileFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  const isReadOnly = disabled || isSubmitting;

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Company Identity">
        <FormGrid columns={2}>
          <FormField label="Legal / Registered Name" required error={errors.legal_name?.message} className="md:col-span-full">
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("legal_name")} />
            )}
          </FormField>

          <FormField label="Display / Trade Name" error={errors.display_name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("display_name")} />
            )}
          </FormField>

          <FormField label="Company Code" error={errors.company_code?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("company_code")} />
            )}
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title="Contact Information">
        <FormGrid columns={2}>
          <PhoneInput label="Phone" error={errors.phone?.message} disabled={isReadOnly} {...register("phone")} />
          <PhoneInput label="Alternate Phone" error={errors.alt_phone?.message} disabled={isReadOnly} {...register("alt_phone")} />
          <EmailInput label="Email" error={errors.email?.message} disabled={isReadOnly} {...register("email")} />

          <FormField label="Website" error={errors.website?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                type="url"
                placeholder="https://example.com"
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                disabled={isReadOnly}
                {...register("website")}
              />
            )}
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title="Business Address">
        <FormGrid columns={2}>
          <FormField label="Address Line 1" error={errors.address_line1?.message} className="md:col-span-full">
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("address_line1")} />
            )}
          </FormField>

          <FormField label="Address Line 2" error={errors.address_line2?.message} className="md:col-span-full">
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("address_line2")} />
            )}
          </FormField>

          <FormField label="City" error={errors.city?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("city")} />
            )}
          </FormField>

          <FormField label="State" error={errors.state?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("state")} />
            )}
          </FormField>

          <FormField label="State Code" error={errors.state_code?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("state_code")} />
            )}
          </FormField>

          <FormField label="Pincode" error={errors.pincode?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("pincode")} />
            )}
          </FormField>

          <FormField label="Country" error={errors.country?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} disabled={isReadOnly} {...register("country")} />
            )}
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title="Tax & Registration">
        <FormGrid columns={2}>
          <GSTINInput label="GSTIN" error={errors.gstin?.message} disabled={isReadOnly} {...register("gstin")} />
          <PANInput label="PAN" error={errors.pan?.message} disabled={isReadOnly} {...register("pan")} />
        </FormGrid>
      </FormSection>

      <FormActions
        secondary={
          <Button type="button" variant="outline" onClick={() => reset(defaultValues)} disabled={isReadOnly || !isDirty}>
            Reset
          </Button>
        }
        primary={
          <Button type="submit" disabled={isReadOnly}>
            {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
            {isSubmitting ? "Saving…" : "Save Changes"}
          </Button>
        }
      />
    </form>
  );
}
