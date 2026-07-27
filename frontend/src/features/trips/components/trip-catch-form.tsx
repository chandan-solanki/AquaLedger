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
  QuantityInput,
  SearchableSelect,
  TextArea,
} from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FISH_UNIT_LABELS } from "@/features/fish";
import { CATCH_GRADE_OPTIONS } from "@/features/trips/constants/catch-grade";
import { useFishOptions } from "@/features/trips/hooks/use-fish-options";
import {
  DEFAULT_TRIP_CATCH_FORM_VALUES,
  tripCatchFormSchema,
  type TripCatchFormValues,
} from "@/features/trips/schemas/trip-catch-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface TripCatchFormProps {
  /** Present for Edit (populated from the loaded trip catch record); omitted for Create (empty form). */
  defaultValues?: TripCatchFormValues;
  onSubmit: (values: TripCatchFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
  /** Renders every field disabled and hides Save - the row action's "View" state for a user with `trip_catch:view` but not `trip_catch:edit`. */
  readOnly?: boolean;
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
 * The shared Trip Catch Create/Edit form - composed entirely from the
 * Sprint 2 enterprise form components, mirroring `TripForm`/`BoatForm`.
 * There is no Trip selector - the owning trip is always the current Trip
 * Detail page's trip (Sprint 6 Session 6's Navigation rule: "Users should
 * never manually choose the trip"); the Fish selector is a
 * `SearchableSelect` over `useFishOptions()`, the same hook
 * `TripCatchTable` already uses to resolve fish names/units.
 *
 * The Inventory fields (Available/Sold/Waste Quantity) only render in edit
 * mode (`defaultValues` present) - the backend fixes them to
 * `quantity_caught`/`0`/`0` at creation and ignores those keys entirely on
 * create, so an editable control for them on Create would do nothing.
 *
 * `readOnly` wraps the whole field set in a native `<fieldset disabled>`,
 * which cascades disabled state to every descendant control without each
 * field needing its own `disabled` wiring, and hides the Save action.
 */
export function TripCatchForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
  readOnly = false,
}: TripCatchFormProps) {
  const isEditMode = Boolean(defaultValues);
  const fishOptions = useFishOptions();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<TripCatchFormValues>({
    resolver: zodResolver(tripCatchFormSchema),
    defaultValues: defaultValues ?? DEFAULT_TRIP_CATCH_FORM_VALUES,
  });

  const selectedFish = fishOptions.fishById.get(watch("fish_id"));
  const unit = selectedFish ? FISH_UNIT_LABELS[selectedFish.unit] : undefined;

  async function handleFormSubmit(values: TripCatchFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<TripCatchFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <fieldset disabled={readOnly} className="m-0 space-y-6 border-0 p-0">
        <FormSection title="Catch Details">
          <FormGrid columns={2}>
            <SearchableSelect
              label="Fish"
              required
              placeholder="Select a fish"
              options={fishOptions.options}
              value={watch("fish_id") || undefined}
              onChange={(value) => value && setValue("fish_id", value, { shouldValidate: true })}
              error={errors.fish_id?.message}
            />

            <SearchableSelect
              label="Grade"
              placeholder="No grade"
              options={CATCH_GRADE_OPTIONS}
              value={watch("grade") || undefined}
              onChange={(value) => setValue("grade", value ?? "", { shouldValidate: true })}
              error={errors.grade?.message}
            />

            <QuantityInput
              label="Quantity Caught"
              required
              unit={unit}
              error={errors.quantity_caught?.message}
              {...register("quantity_caught")}
            />

            <DatePicker
              label="Landing Date"
              required
              error={errors.landing_date?.message}
              value={toDateOrUndefined(watch("landing_date"))}
              onChange={(date) => setValue("landing_date", toIsoDateString(date), { shouldValidate: true })}
            />

            <FormField label="Landing Port" error={errors.landing_port?.message}>
              {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
                <Input
                  id={id}
                  aria-describedby={describedBy}
                  aria-invalid={ariaInvalid}
                  {...register("landing_port")}
                />
              )}
            </FormField>
          </FormGrid>
        </FormSection>

        {isEditMode && (
          <FormSection title="Inventory">
            <FormGrid columns={2}>
              <QuantityInput
                label="Available Quantity"
                unit={unit}
                error={errors.available_quantity?.message}
                {...register("available_quantity")}
              />

              <QuantityInput
                label="Sold Quantity"
                unit={unit}
                error={errors.sold_quantity?.message}
                {...register("sold_quantity")}
              />

              <QuantityInput
                label="Waste Quantity"
                unit={unit}
                error={errors.waste_quantity?.message}
                {...register("waste_quantity")}
              />
            </FormGrid>
          </FormSection>
        )}

        <TextArea label="Remarks" error={errors.remarks?.message} {...register("remarks")} />
      </fieldset>

      <FormActions
        secondary={
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            {readOnly ? "Close" : "Cancel"}
          </Button>
        }
        primary={
          !readOnly && (
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="animate-spin motion-reduce:animate-none" />}
              {isSubmitting ? "Saving…" : submitLabel}
            </Button>
          )
        }
      />
    </form>
  );
}
