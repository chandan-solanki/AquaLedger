"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { FormActions, FormField, FormGrid, FormSection, SearchableSelect, TextArea } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useBoatOptions } from "@/features/trips/hooks/use-boat-options";
import { TRIP_STATUS_OPTIONS } from "@/features/trips/constants/trip-status";
import { TRIP_TYPE_OPTIONS } from "@/features/trips/constants/trip-type";
import {
  DEFAULT_TRIP_FORM_VALUES,
  tripFormSchema,
  type TripFormValues,
} from "@/features/trips/schemas/trip-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface TripFormProps {
  /** Present for Edit (populated from the loaded trip record); omitted for Create (empty form). */
  defaultValues?: TripFormValues;
  onSubmit: (values: TripFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * The shared Trip Create/Edit form - identical field set and validation for
 * both flows, composed entirely from the Sprint 2 enterprise form
 * components, mirroring `BoatForm`/`FishForm`. Owns its own submit
 * try/catch: a 422's `field_errors` map onto the matching fields, anything
 * else (409 duplicate trip number, 422 boat-already-active / boat-not-active
 * / invalid-return-datetime business rules, 404 boat not found, network,
 * 5xx - see app/modules/trips/exceptions.py) surfaces as a toast, per this
 * session's Error Handling scope.
 *
 * The Boat field is a `SearchableSelect` over `useBoatOptions()` (this
 * feature's own hook, already built for the List page's Boat filter) rather
 * than a raw text id field - `boat_id` is a foreign key, and picking from
 * this tenant's actual boats is the only way to supply a valid one.
 */
export function TripForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save" }: TripFormProps) {
  const boatOptions = useBoatOptions();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<TripFormValues>({
    resolver: zodResolver(tripFormSchema),
    defaultValues: defaultValues ?? DEFAULT_TRIP_FORM_VALUES,
  });

  async function handleFormSubmit(values: TripFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<TripFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Trip Details">
        <FormGrid columns={2}>
          <FormField label="Trip Number" required error={errors.trip_number?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("trip_number")}
              />
            )}
          </FormField>

          <SearchableSelect
            label="Boat"
            required
            placeholder="Select a boat"
            options={boatOptions.options}
            value={watch("boat_id") || undefined}
            onChange={(value) => value && setValue("boat_id", value, { shouldValidate: true })}
            error={errors.boat_id?.message}
          />

          <SearchableSelect
            label="Trip Type"
            required
            options={TRIP_TYPE_OPTIONS}
            value={watch("trip_type")}
            onChange={(value) => value && setValue("trip_type", value, { shouldValidate: true })}
            error={errors.trip_type?.message}
          />

          <SearchableSelect
            label="Status"
            required
            options={TRIP_STATUS_OPTIONS}
            value={watch("status")}
            onChange={(value) => value && setValue("status", value, { shouldValidate: true })}
            error={errors.status?.message}
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
        </FormGrid>
      </FormSection>

      <FormSection title="Schedule">
        <FormGrid columns={2}>
          <FormField label="Departure" required error={errors.departure_datetime?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                type="datetime-local"
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("departure_datetime")}
              />
            )}
          </FormField>

          <FormField label="Expected Return" error={errors.expected_return_datetime?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                type="datetime-local"
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("expected_return_datetime")}
              />
            )}
          </FormField>

          <FormField label="Actual Return" error={errors.actual_return_datetime?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                type="datetime-local"
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("actual_return_datetime")}
              />
            )}
          </FormField>
        </FormGrid>
      </FormSection>

      <FormSection title="Ports">
        <FormGrid columns={2}>
          <FormField label="Departure Port" error={errors.departure_port?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("departure_port")}
              />
            )}
          </FormField>

          <FormField label="Arrival Port" error={errors.arrival_port?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("arrival_port")}
              />
            )}
          </FormField>
        </FormGrid>
      </FormSection>

      <TextArea label="Notes" error={errors.notes?.message} {...register("notes")} />

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
