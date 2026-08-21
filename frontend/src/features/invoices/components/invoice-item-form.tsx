"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FISH_UNIT_LABELS } from "@/features/fish";
import { CATCH_GRADE_LABELS, tripCatchService, tripKeys, tripService, useFishOptions } from "@/features/trips";
import type { TripCatch } from "@/features/trips";
import { useTripCatchConflicts } from "@/features/invoices/hooks/use-trip-catch-conflicts";
import { useTripCatchDraftDemand } from "@/features/invoices/hooks/use-trip-catch-draft-demand";
import {
  DEFAULT_INVOICE_ITEM_FORM_VALUES,
  invoiceItemFormSchema,
  type InvoiceItemFormValues,
} from "@/features/invoices/schemas/invoice-item-form-schema";
import { useSearch } from "@/hooks/use-search";
import { cn } from "@/lib/utils";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { formatQuantity } from "@/utils/format-number";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface InvoiceItemFormProps {
  /** The invoice this item belongs to (Create and Edit alike) - excluded from its own "other draft demand" (Sprint 15 Session 5, `useTripCatchDraftDemand`'s `excludeInvoiceId`). */
  invoiceId: string;
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
  /** Fires whenever the catch behind `value` is resolved (fresh selection or Edit-mode initial load), or with `undefined` once nothing is selected - lets the parent show stock context without re-fetching the same catch. */
  onResolvedChange: (tripCatch: TripCatch | undefined) => void;
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
function TripCatchSelectorField({ value, error, onSelect, onResolvedChange }: TripCatchSelectorFieldProps) {
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
        const isOutOfStock = Number(tc.availableQuantity) <= 0;
        return {
          value: tc.id,
          label: `${tripNumber} — ${fish?.name ?? "Unknown fish"}`,
          description: isOutOfStock
            ? `${gradeLabel} · Out of stock`
            : `${gradeLabel} · Available: ${formatQuantity(tc.availableQuantity)} ${unitLabel}`,
          // The currently selected catch stays clickable even at zero stock - Edit mode must never
          // hide a historical selection, only steer the user away from picking a *new* empty one.
          disabled: isOutOfStock && tc.id !== value,
        };
      }),
    [catches, fishOptions.fishById, tripNumberByTripId, value]
  );

  const selectedOption = options.find((option) => option.value === value);
  const resolvedCatch = catches.find((tc) => tc.id === value);

  useEffect(() => {
    onResolvedChange(resolvedCatch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedCatch]);

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
 * Sprint 15 Session 9: "does any OTHER invoice already reference the
 * selected trip catch" - shown the moment a catch is chosen, before the
 * item is even saved. Reuses Session 6's per-catch `GET .../conflicts`
 * endpoint (via the existing `useTripCatchConflicts` hook) exactly as-is -
 * zero backend changes, since that endpoint already excludes the current
 * invoice via `excludeInvoiceId` and already returns each other invoice's
 * status/quantity, which is all the count/draft/consumed breakdown below
 * needs. `invoiceId` is always a real, saved id by the time this form
 * renders (a new invoice is created header-first, see `InvoiceCreatePage`,
 * before its Items section - and thus this form - ever mounts), so there is
 * no "no invoice id yet" branch to handle for Create vs Edit; both pass the
 * same real id.
 *
 * Deliberately additive, not a replacement for Session 5's own "Other Draft
 * Invoices"/"Potentially Available" panel above (which keeps its own
 * separate, already-tested fetch) - that panel only ever covered draft
 * demand; this one is the fuller picture Sessions 7/8 already established
 * (count + draft + consumed), including invoices that already consumed the
 * stock, which Session 5 never surfaced. Informational only, never a
 * validation rule: renders nothing when there's no other usage, and nothing
 * on a failed lookup either - either way, saving is never blocked by this
 * component.
 */
function OtherInvoiceUsageNotice({
  tripCatchId,
  invoiceId,
  unitLabel,
}: {
  tripCatchId: string;
  invoiceId: string;
  unitLabel: string;
}) {
  const conflictsQuery = useTripCatchConflicts(tripCatchId, invoiceId, undefined);

  if (conflictsQuery.isLoading) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="size-3 animate-spin motion-reduce:animate-none" aria-hidden />
        Checking other invoices…
      </p>
    );
  }

  // Undefined on either "hasn't resolved yet" (already handled above) or a failed lookup - both
  // degrade to rendering nothing, never an error message that could distract from the form itself.
  const invoices = conflictsQuery.data?.conflictingInvoices;
  if (!invoices || invoices.length === 0) {
    return null;
  }

  const draftQuantity = invoices
    .filter((invoice) => invoice.status === "draft")
    .reduce((sum, invoice) => sum + Number(invoice.quantity), 0);
  const consumedQuantity = invoices
    .filter((invoice) => invoice.status !== "draft")
    .reduce((sum, invoice) => sum + Number(invoice.quantity), 0);

  const countLabel = `Referenced by ${invoices.length} other invoice${invoices.length === 1 ? "" : "s"}`;
  let detailLabel: string | null = null;
  if (draftQuantity > 0 && consumedQuantity > 0) {
    detailLabel = `${formatQuantity(draftQuantity)} ${unitLabel} draft · ${formatQuantity(consumedQuantity)} ${unitLabel} consumed`;
  } else if (draftQuantity > 0) {
    detailLabel = `${formatQuantity(draftQuantity)} ${unitLabel} in draft invoices`;
  } else if (consumedQuantity > 0) {
    detailLabel = `${formatQuantity(consumedQuantity)} ${unitLabel} already consumed`;
  }

  return (
    <div className="space-y-0.5 text-xs text-muted-foreground">
      <p>{countLabel}</p>
      {detailLabel && <p>{detailLabel}</p>}
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
 * ever rendered read-only, in `InvoiceItemTable`'s columns.
 *
 * "quantity must not exceed the trip catch's available_quantity" (Sprint 15
 * Session 4): the backend remains the sole source of truth and the final,
 * lock-protected check happens only at issue time
 * (`TripCatchService.deduct_available_quantity`) - this form's own check
 * (below, against the trip catch's `available_quantity` at the moment it was
 * fetched) is a UX convenience only, blocking an obviously-doomed submit a
 * beat earlier than the server's own 422 would.
 *
 * Sprint 15 Session 5 adds "other draft demand" - how much of this same
 * catch OTHER draft invoices already reference. This is informational only,
 * never a hard block (draft demand is not a reservation - another draft
 * could be deleted or edited before this one issues), and is deliberately
 * never fetched for an already-out-of-stock catch (`availableQuantity`
 * gates `useTripCatchDraftDemand` below) so it can never make the existing
 * "Out of stock" state more confusing.
 */
export function InvoiceItemForm({
  invoiceId,
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}: InvoiceItemFormProps) {
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

  const [selectedTripCatch, setSelectedTripCatch] = useState<TripCatch | undefined>();
  const selectedFish = fishOptions.fishById.get(watch("fish_id"));
  const quantity = watch("quantity");
  const unitLabel = selectedFish ? FISH_UNIT_LABELS[selectedFish.unit] : "";

  const availableQuantity =
    selectedTripCatch && selectedTripCatch.id === watch("trip_catch_id")
      ? Number(selectedTripCatch.availableQuantity)
      : undefined;
  const enteredQuantity = Number(quantity);
  const hasEnteredQuantity = quantity.trim() !== "" && Number.isFinite(enteredQuantity);
  const remainingQuantity =
    availableQuantity !== undefined && hasEnteredQuantity ? availableQuantity - enteredQuantity : availableQuantity;
  const exceedsAvailable = remainingQuantity !== undefined && remainingQuantity < 0;

  // Never asked for a zero-or-less-available catch - "other draft demand" would only muddy an
  // already-unambiguous "Out of stock" state.
  const draftDemandTripCatchId =
    availableQuantity !== undefined && availableQuantity > 0 ? (selectedTripCatch?.id ?? "") : "";
  const draftDemandQuery = useTripCatchDraftDemand(draftDemandTripCatchId, invoiceId);
  const otherDraftQuantity = draftDemandQuery.data
    ? Number(draftDemandQuery.data.otherDraftQuantity)
    : undefined;
  const hasOtherDraftDemand = otherDraftQuantity !== undefined && otherDraftQuantity > 0;
  const potentiallyAvailable =
    availableQuantity !== undefined && otherDraftQuantity !== undefined
      ? availableQuantity - otherDraftQuantity
      : undefined;
  // Only a soft, non-blocking signal - and only in the gap between "exceeds what other drafts
  // leave" and "exceeds what's actually available right now" (that stronger case already gets
  // the hard block above, so there's no need to also warn about it here).
  const exceedsPotentiallyAvailable =
    !exceedsAvailable &&
    potentiallyAvailable !== undefined &&
    hasEnteredQuantity &&
    enteredQuantity > potentiallyAvailable;

  async function handleFormSubmit(values: InvoiceItemFormValues) {
    if (selectedTripCatch && selectedTripCatch.id === values.trip_catch_id) {
      const available = Number(selectedTripCatch.availableQuantity);
      if (Number(values.quantity) > available) {
        setError("quantity", {
          type: "availableQuantity",
          message: `Only ${formatQuantity(selectedTripCatch.availableQuantity)} ${unitLabel} is currently available.`,
        });
        return;
      }
    }
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
              onResolvedChange={setSelectedTripCatch}
            />
          </div>

          {selectedTripCatch && (
            <div className="md:col-span-full space-y-1 rounded-lg border bg-muted/30 px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
                <span className="text-muted-foreground">Available Stock</span>
                <span className="font-semibold tabular-nums">
                  {formatQuantity(selectedTripCatch.availableQuantity)} {unitLabel}
                </span>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
                <span className="text-muted-foreground">Remaining after this item</span>
                <span
                  className={cn("font-semibold tabular-nums", exceedsAvailable && "text-destructive")}
                >
                  {remainingQuantity !== undefined ? formatQuantity(remainingQuantity) : "—"} {unitLabel}
                </span>
              </div>

              {hasOtherDraftDemand && (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
                    <span className="text-muted-foreground">Other Draft Invoices</span>
                    <span className="font-semibold tabular-nums">
                      {formatQuantity(otherDraftQuantity!)} {unitLabel}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
                    <span className="text-muted-foreground">Potentially Available</span>
                    <span className="font-semibold tabular-nums">
                      {formatQuantity(potentiallyAvailable!)} {unitLabel}
                    </span>
                  </div>
                </>
              )}
            </div>
          )}

          {hasOtherDraftDemand && (
            <div className="md:col-span-full">
              <Alert>
                <AlertDescription>
                  <p>
                    Other draft invoices are using this catch. Stock is not reserved until the
                    invoice is issued.
                  </p>
                  {exceedsPotentiallyAvailable && (
                    <p>
                      {formatQuantity(availableQuantity!)} {unitLabel} is currently available, but{" "}
                      {formatQuantity(otherDraftQuantity!)} {unitLabel} is already requested by
                      other draft invoices. This invoice may fail to issue if those drafts are
                      issued first.
                    </p>
                  )}
                </AlertDescription>
              </Alert>
            </div>
          )}

          {selectedTripCatch && (
            <div className="md:col-span-full">
              <OtherInvoiceUsageNotice
                tripCatchId={selectedTripCatch.id}
                invoiceId={invoiceId}
                unitLabel={unitLabel}
              />
            </div>
          )}

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
            unit={unitLabel || undefined}
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
