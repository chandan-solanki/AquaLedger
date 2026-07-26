"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import {
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  RateInput,
  SearchableSelect,
  TextArea,
} from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FISH_STATUS_OPTIONS } from "@/features/fish/constants/fish-status";
import {
  DEFAULT_FISH_FORM_VALUES,
  fishFormSchema,
  type FishFormValues,
} from "@/features/fish/schemas/fish-form-schema";
import { FISH_UNIT_OPTIONS } from "@/features/fish/types/fish";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface FishFormProps {
  /** Present for Edit (populated from the loaded fish record); omitted for Create (empty form). */
  defaultValues?: FishFormValues;
  onSubmit: (values: FishFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * The shared Fish Create/Edit form - identical field set and validation for
 * both flows, composed entirely from the Sprint 2 enterprise form
 * components, mirroring `CompanyForm` exactly. Owns its own submit
 * try/catch: a 422's `field_errors` map onto the matching fields, anything
 * else (409 duplicate code/name, network, 5xx) surfaces as a toast, per this
 * session's Error Handling scope.
 */
export function FishForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save" }: FishFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FishFormValues>({
    resolver: zodResolver(fishFormSchema),
    defaultValues: defaultValues ?? DEFAULT_FISH_FORM_VALUES,
  });

  async function handleFormSubmit(values: FishFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<FishFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Fish Details">
        <FormGrid columns={2}>
          <FormField label="Fish Name" required error={errors.name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("name")} />
            )}
          </FormField>

          <FormField label="Fish Code" required error={errors.code?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("code")} />
            )}
          </FormField>

          <FormField label="Local Name" error={errors.local_name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("local_name")}
              />
            )}
          </FormField>

          <FormField label="Scientific Name" error={errors.scientific_name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("scientific_name")}
              />
            )}
          </FormField>

          <FormField label="Category" error={errors.category?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("category")}
              />
            )}
          </FormField>

          <SearchableSelect
            label="Unit"
            required
            options={FISH_UNIT_OPTIONS}
            value={watch("unit")}
            onChange={(value) => value && setValue("unit", value, { shouldValidate: true })}
            error={errors.unit?.message}
          />

          <SearchableSelect
            label="Status"
            required
            options={FISH_STATUS_OPTIONS}
            value={watch("status")}
            onChange={(value) => value && setValue("status", value, { shouldValidate: true })}
            error={errors.status?.message}
          />

          <FormField label="HSN Code" error={errors.hsn_code?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("hsn_code")}
              />
            )}
          </FormField>

          <RateInput
            label="Default Purchase Rate"
            error={errors.default_purchase_rate?.message}
            {...register("default_purchase_rate")}
          />

          <RateInput
            label="Default Sale Rate"
            error={errors.default_sale_rate?.message}
            {...register("default_sale_rate")}
          />
        </FormGrid>
      </FormSection>

      <FormSection title="Description">
        <TextArea label="Description" error={errors.description?.message} {...register("description")} />
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
