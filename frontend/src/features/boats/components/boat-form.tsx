"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { format, parseISO } from "date-fns";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import {
  DatePicker,
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  NumberInput,
  PhoneInput,
  QuantityInput,
  SearchableSelect,
  TextArea,
} from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BOAT_STATUS_OPTIONS } from "@/features/boats/constants/boat-status";
import {
  DEFAULT_BOAT_FORM_VALUES,
  boatFormSchema,
  type BoatFormValues,
} from "@/features/boats/schemas/boat-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface BoatFormProps {
  /** Present for Edit (populated from the loaded boat record); omitted for Create (empty form). */
  defaultValues?: BoatFormValues;
  onSubmit: (values: BoatFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

function toDateOrUndefined(value: string): Date | undefined {
  if (!value) return undefined;
  const parsed = parseISO(value);
  return Number.isNaN(parsed.getTime()) ? undefined : parsed;
}

function toIsoDateString(date: Date | undefined): string {
  return date ? format(date, "yyyy-MM-dd") : "";
}

/**
 * The shared Boat Create/Edit form - identical field set and validation for
 * both flows, composed entirely from the Sprint 2 enterprise form
 * components, mirroring `FishForm`/`CompanyForm`. Owns its own submit
 * try/catch: a 422's `field_errors` map onto the matching fields, anything
 * else (409 duplicate code/registration number, network, 5xx) surfaces as a
 * toast, per this session's Error Handling scope.
 *
 * No company field - a boat is owned by the tenant only. A `Company` is a
 * customer (buyer), never a boat owner (ARCHITECTURE.md's Business Model).
 */
export function BoatForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save" }: BoatFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<BoatFormValues>({
    resolver: zodResolver(boatFormSchema),
    defaultValues: defaultValues ?? DEFAULT_BOAT_FORM_VALUES,
  });

  async function handleFormSubmit(values: BoatFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<BoatFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Boat Details">
        <FormGrid columns={2}>
          <FormField label="Boat Name" required error={errors.name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("name")} />
            )}
          </FormField>

          <FormField label="Boat Code / Number" required error={errors.code?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("code")} />
            )}
          </FormField>

          <FormField label="Registration Number" required error={errors.registration_number?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("registration_number")}
              />
            )}
          </FormField>

          <FormField label="Boat Type" error={errors.boat_type?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                placeholder="e.g. trawler"
                {...register("boat_type")}
              />
            )}
          </FormField>

          <QuantityInput
            label="Capacity"
            unit="kg"
            error={errors.capacity_kg?.message}
            {...register("capacity_kg")}
          />

          <SearchableSelect
            label="Status"
            required
            options={BOAT_STATUS_OPTIONS}
            value={watch("status")}
            onChange={(value) => value && setValue("status", value, { shouldValidate: true })}
            error={errors.status?.message}
          />
        </FormGrid>
      </FormSection>

      <FormSection title="Engine & Crew">
        <FormGrid columns={2}>
          <FormField label="Engine Number" error={errors.engine_number?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("engine_number")}
              />
            )}
          </FormField>

          <NumberInput
            label="Engine Power"
            suffix="HP"
            error={errors.engine_hp?.message}
            {...register("engine_hp")}
          />

          <FormField label="Captain Name" error={errors.captain_name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("captain_name")}
              />
            )}
          </FormField>

          <PhoneInput label="Captain Phone" error={errors.captain_phone?.message} {...register("captain_phone")} />
        </FormGrid>
      </FormSection>

      <FormSection title="Compliance">
        <FormGrid columns={2}>
          <FormField label="License Number" error={errors.license_number?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("license_number")}
              />
            )}
          </FormField>

          <DatePicker
            label="License Expiry"
            error={errors.license_expiry?.message}
            value={toDateOrUndefined(watch("license_expiry"))}
            onChange={(date) => setValue("license_expiry", toIsoDateString(date), { shouldValidate: true })}
          />

          <DatePicker
            label="Insurance Expiry"
            error={errors.insurance_expiry?.message}
            value={toDateOrUndefined(watch("insurance_expiry"))}
            onChange={(date) => setValue("insurance_expiry", toIsoDateString(date), { shouldValidate: true })}
          />
        </FormGrid>
      </FormSection>

      <FormSection title="Description">
        <TextArea label="Description" error={errors.notes?.message} {...register("notes")} />
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
