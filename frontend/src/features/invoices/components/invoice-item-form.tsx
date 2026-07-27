"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { useQueries, useQuery } from "@tanstack/react-query";

import {
  AsyncSelect,
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  PercentageInput,
  QuantityInput,
  RateInput,
} from "@/components/form";
import type { ComboboxOption } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FISH_UNIT_LABELS } from "@/features/fish";
import { CATCH_GRADE_LABELS, tripCatchService, tripKeys, tripService, useFishOptions } from "@/features/trips";
import type { TripCatch } from "@/features/trips";
import {
  DEFAULT_INVOICE_ITEM_FORM_VALUES,
  invoiceItemFormSchema,
  type InvoiceItemFormValues,
} from "@/features/invoices/schemas/invoice-item-form-schema";
import { useSearch } from "@/hooks/use-search";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { formatQuantity } from "@/utils/format-number";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface InvoiceItemFormProps {
  /** Present for Edit (populated from the loaded invoice item record); omitted for Create (empty form). */
  defaultValues?: InvoiceItemFormValues;
  onSubmit: (values: InvoiceItemFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * Resolves each candidate trip catch's owning `trip_number` via Trips' own
 * public `tripService.getTrip` (`@/features/trips`) - `TripCatchResponse`
 * carries only `trip_id` (app/modules/trip_catches/schemas.py), and unlike
 * Boats/Fish/Companies there is no bounded "all trips" options list to
 * resolve against (Trips, like Invoices, is an unbounded transactional
 * resource) - so every unique `trip_id` appearing in the current search
 * results is resolved individually via `useQueries`, deduplicated and
 * cached under the exact same `tripKeys.detail(id)` key `useTrip` itself
 * uses, so repeat appearances across searches never refetch.
 */
function useTripNumbers(tripIds: string[]) {
  const uniqueIds = useMemo(() => Array.from(new Set(tripIds)), [tripIds]);
  const results = useQueries({
    queries: uniqueIds.map((id) => ({
      queryKey: tripKeys.detail(id),
      queryFn: () => tripService.getTrip(id),
      staleTime: 5 * 60 * 1000,
    })),
  });

  return useMemo(() => {
    const map = new Map<string, string>();
    uniqueIds.forEach((id, index) => {
      const trip = results[index]?.data;
      if (trip) map.set(id, trip.tripNumber);
    });
    return map;
  }, [uniqueIds, results]);
}

interface TripCatchSelectorFieldProps {
  value: string;
  error?: string;
  onSelect: (tripCatch: TripCatch) => void;
}

/**
 * A searchable Trip Catch selector - the source of every invoice line
 * (ARCHITECTURE.md §16.1's "realized revenue" model; TASKS.md: "Trip Catch
 * is the business source"). Typeahead is driven by the backend's own
 * `GET /trip-catches` search (`q` matches the owning trip's trip_number and
 * the caught fish's name, app/modules/trip_catches/schemas.py) via
 * `AsyncSelect`; each result's label/description shows Trip Number, Fish,
 * Grade and Available Quantity so the user can pick the right catch without
 * leaving the form - only `trip_catch_id` is ever submitted (`onSelect`
 * hands the caller the full `TripCatch` so it can also derive `fish_id`).
 * Reuses `tripCatchService`/`useFishOptions`/`tripService`, all from the
 * Trips/Fish features' own public surfaces - no lookup logic is
 * reimplemented here.
 *
 * The currently selected catch is always resolved by id
 * (`tripCatchService.getTripCatch`) and merged into `options`, so Edit mode
 * shows a correct label immediately, before the user has typed anything.
 */
function TripCatchSelectorField({ value, error, onSelect }: TripCatchSelectorFieldProps) {
  const search = useSearch({ debounceMs: 300 });
  const fishOptions = useFishOptions();

  const searchQuery = useQuery({
    queryKey: ["trip-catches", "search", search.debouncedValue],
    queryFn: () =>
      tripCatchService.listTripCatches({
        q: search.debouncedValue || undefined,
        sort: "-created_at",
        page: 1,
        page_size: 20,
      }),
  });

  const selectedCatchQuery = useQuery({
    queryKey: ["trip-catches", "detail", value],
    queryFn: () => tripCatchService.getTripCatch(value),
    enabled: Boolean(value),
    staleTime: 5 * 60 * 1000,
  });

  const catches = useMemo(() => {
    const results = searchQuery.data?.data ?? [];
    if (selectedCatchQuery.data && !results.some((tc) => tc.id === selectedCatchQuery.data!.id)) {
      return [selectedCatchQuery.data, ...results];
    }
    return results;
  }, [searchQuery.data, selectedCatchQuery.data]);

  const tripNumberByTripId = useTripNumbers(catches.map((tc) => tc.tripId));

  const options = useMemo<ComboboxOption[]>(
    () =>
      catches.map((tc) => {
        const fish = fishOptions.fishById.get(tc.fishId);
        const tripNumber = tripNumberByTripId.get(tc.tripId) ?? "Trip";
        const gradeLabel = tc.grade ? CATCH_GRADE_LABELS[tc.grade] : "No grade";
        const unitLabel = fish ? FISH_UNIT_LABELS[fish.unit] : "";
        return {
          value: tc.id,
          label: `${tripNumber} — ${fish?.name ?? "Unknown fish"}`,
          description: `${gradeLabel} · Available: ${formatQuantity(tc.availableQuantity)} ${unitLabel}`,
        };
      }),
    [catches, fishOptions.fishById, tripNumberByTripId]
  );

  const selectedOption = options.find((option) => option.value === value);

  return (
    <div className="space-y-1.5">
      <AsyncSelect
        label="Trip Catch"
        required
        placeholder="Search by trip number or fish name…"
        searchPlaceholder="Search trip catches…"
        options={options}
        value={value || undefined}
        onSearchChange={search.setValue}
        isLoading={searchQuery.isFetching || selectedCatchQuery.isLoading}
        onChange={(selectedId) => {
          const chosen = catches.find((tc) => tc.id === selectedId);
          if (chosen) onSelect(chosen);
        }}
        error={error}
      />
      {selectedOption?.description && (
        <p className="px-1 text-xs text-muted-foreground">{selectedOption.description}</p>
      )}
    </div>
  );
}

/**
 * The shared Invoice Item Create/Edit form - fields match
 * `InvoiceItemCreateRequest`/`InvoiceItemUpdateRequest` exactly
 * (app/modules/invoices/schemas.py). Rendered inside a Dialog on the
 * Invoice Detail page (`InvoiceItemTable`), not a routed page - Sprint 7
 * Session 3's Routes scope is `/invoices/[id]` only (TASKS.md).
 *
 * `fish_id` is never an independently-editable field: the backend requires
 * it to match the chosen trip catch's own fish (422
 * `INVOICE_ITEM_FISH_MISMATCH` otherwise), so `TripCatchSelectorField`'s
 * `onSelect` sets both `trip_catch_id` and `fish_id` together, and `unit`
 * is pre-filled from the selected fish's default unit code (still freely
 * editable afterward - the `InvoiceItem` model's own docstring: "a plain
 * string snapshot... not a foreign key or shared enum with fish.unit").
 * Financial fields (discount_amount/taxable_amount/tax_amount/line_total)
 * are never in this form - they are entirely server-computed and only
 * ever rendered read-only, in `InvoiceItemTable`'s columns. The backend's
 * "quantity must not exceed the trip catch's available_quantity" rule is
 * left server-validated only (surfaces as a generic 422 toast below),
 * mirroring how `TripForm`/`TripCatchForm` leave equivalent cross-entity
 * business rules server-validated.
 */
export function InvoiceItemForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save" }: InvoiceItemFormProps) {
  const fishOptions = useFishOptions();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<InvoiceItemFormValues>({
    resolver: zodResolver(invoiceItemFormSchema),
    defaultValues: defaultValues ?? DEFAULT_INVOICE_ITEM_FORM_VALUES,
  });

  const selectedFish = fishOptions.fishById.get(watch("fish_id"));

  async function handleFormSubmit(values: InvoiceItemFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<InvoiceItemFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Item Details">
        <FormGrid columns={2}>
          <div className="md:col-span-full">
            <TripCatchSelectorField
              value={watch("trip_catch_id")}
              error={errors.trip_catch_id?.message}
              onSelect={(tripCatch) => {
                setValue("trip_catch_id", tripCatch.id, { shouldValidate: true });
                setValue("fish_id", tripCatch.fishId, { shouldValidate: true });
                const fish = fishOptions.fishById.get(tripCatch.fishId);
                if (fish) setValue("unit", fish.unit, { shouldValidate: true });
              }}
            />
          </div>

          <FormField label="Description" error={errors.description?.message} className="md:col-span-full">
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("description")}
              />
            )}
          </FormField>

          <QuantityInput
            label="Quantity"
            required
            unit={selectedFish ? FISH_UNIT_LABELS[selectedFish.unit] : undefined}
            error={errors.quantity?.message}
            {...register("quantity")}
          />

          <FormField label="Unit" required error={errors.unit?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("unit")} />
            )}
          </FormField>

          <RateInput label="Rate" required error={errors.rate?.message} {...register("rate")} />

          <PercentageInput
            label="Discount %"
            error={errors.discount_percent?.message}
            {...register("discount_percent")}
          />

          <PercentageInput label="Tax %" error={errors.tax_rate?.message} {...register("tax_rate")} />
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
