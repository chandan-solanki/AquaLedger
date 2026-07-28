"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { EmailInput, FormActions, FormField, FormGrid, FormSection, GSTINInput, PhoneInput } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DEFAULT_SUPPLIER_FORM_VALUES,
  supplierFormSchema,
  type SupplierFormValues,
} from "@/features/suppliers/schemas/supplier-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface SupplierFormProps {
  /** Present for Edit (populated from the loaded supplier); omitted for Create (empty form). */
  defaultValues?: SupplierFormValues;
  onSubmit: (values: SupplierFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * The shared Supplier Create/Edit form - identical field set and validation
 * for both flows, composed entirely from the Sprint 2 enterprise form
 * components, mirroring `CompanyForm`. Owns its own submit try/catch: a
 * 422's `field_errors` map onto the matching fields, anything else (409
 * duplicate code/name, network, 5xx) surfaces as a toast.
 *
 * There is no Status field (unlike `CompanyForm`) - the backend never
 * accepts `status` on a supplier at all (`SupplierCreateRequest`/
 * `SupplierUpdateRequest` both omit it; always `active` on create, server-
 * owned thereafter) - and no Company Type field either, since a Supplier has
 * no such concept.
 */
export function SupplierForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save" }: SupplierFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SupplierFormValues>({
    resolver: zodResolver(supplierFormSchema),
    defaultValues: defaultValues ?? DEFAULT_SUPPLIER_FORM_VALUES,
  });

  async function handleFormSubmit(values: SupplierFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<SupplierFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Supplier Details">
        <FormGrid columns={2}>
          <FormField label="Supplier Name" required error={errors.name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("name")} />
            )}
          </FormField>

          <FormField label="Supplier Code" required error={errors.code?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("code")} />
            )}
          </FormField>

          <GSTINInput label="GSTIN" error={errors.gstin?.message} {...register("gstin")} />

          <PhoneInput label="Phone" error={errors.phone?.message} {...register("phone")} />

          <EmailInput label="Email" error={errors.email?.message} {...register("email")} />
        </FormGrid>
      </FormSection>

      <FormSection title="Address">
        <FormGrid columns={2}>
          <FormField label="Address" error={errors.address?.message} className="md:col-span-full">
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("address")} />
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
            {isSubmitting ? "Saving…" : submitLabel}
          </Button>
        }
      />
    </form>
  );
}
