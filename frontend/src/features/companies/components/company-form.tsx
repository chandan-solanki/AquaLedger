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
  PhoneInput,
  SearchableSelect,
  TextArea,
} from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { COMPANY_STATUS_OPTIONS } from "@/features/companies/constants/company-status";
import { COMPANY_TYPE_OPTIONS } from "@/features/companies/constants/company-type";
import {
  DEFAULT_COMPANY_FORM_VALUES,
  companyFormSchema,
  type CompanyFormValues,
} from "@/features/companies/schemas/company-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface CompanyFormProps {
  /** Present for Edit (populated from the loaded company); omitted for Create (empty form). */
  defaultValues?: CompanyFormValues;
  onSubmit: (values: CompanyFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * The shared Company Create/Edit form - identical field set and validation
 * for both flows, composed entirely from the Sprint 2 enterprise form
 * components. Owns its own submit try/catch: a 422's `field_errors` map
 * onto the matching fields, anything else (409 duplicate code, network,
 * 5xx) surfaces as a toast, per this session's Error Handling scope.
 */
export function CompanyForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save" }: CompanyFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<CompanyFormValues>({
    resolver: zodResolver(companyFormSchema),
    defaultValues: defaultValues ?? DEFAULT_COMPANY_FORM_VALUES,
  });

  async function handleFormSubmit(values: CompanyFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<CompanyFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Company Details">
        <FormGrid columns={2}>
          <FormField label="Company Name" required error={errors.name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("name")} />
            )}
          </FormField>

          <FormField label="Company Code" required error={errors.code?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("code")} />
            )}
          </FormField>

          <SearchableSelect
            label="Company Type"
            required
            options={COMPANY_TYPE_OPTIONS}
            value={watch("company_type")}
            onChange={(value) => value && setValue("company_type", value, { shouldValidate: true })}
            error={errors.company_type?.message}
          />

          <SearchableSelect
            label="Status"
            required
            options={COMPANY_STATUS_OPTIONS}
            value={watch("status")}
            onChange={(value) => value && setValue("status", value, { shouldValidate: true })}
            error={errors.status?.message}
          />

          <GSTINInput label="GSTIN" error={errors.gstin?.message} {...register("gstin")} />

          <PhoneInput label="Phone" error={errors.phone?.message} {...register("phone")} />

          <EmailInput label="Email" error={errors.email?.message} {...register("email")} />
        </FormGrid>
      </FormSection>

      <FormSection title="Address">
        <FormGrid columns={2}>
          <FormField label="Address" error={errors.address_line1?.message} className="md:col-span-full">
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("address_line1")}
              />
            )}
          </FormField>

          <FormField label="City" error={errors.city?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("city")} />
            )}
          </FormField>

          <FormField label="State" error={errors.state?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("state")} />
            )}
          </FormField>

          <FormField label="Country" error={errors.country?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("country")} />
            )}
          </FormField>

          <FormField label="Postal Code" error={errors.pincode?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("pincode")} />
            )}
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title="Notes">
        <TextArea label="Notes" error={errors.notes?.message} {...register("notes")} />
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
            {isSubmitting ? "Saving…" : submitLabel}
          </Button>
        }
      />
    </form>
  );
}
