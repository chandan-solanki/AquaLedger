"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { format, parseISO } from "date-fns";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { CurrencyInput, DatePicker, FormActions, FormField, FormGrid, FormSection, SearchableSelect, TextArea } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EXPENSE_TYPE_OPTIONS } from "@/features/trips/constants/expense-type";
import {
  DEFAULT_TRIP_EXPENSE_FORM_VALUES,
  tripExpenseFormSchema,
  type TripExpenseFormValues,
} from "@/features/trips/schemas/trip-expense-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface TripExpenseFormProps {
  /** Present for Edit (populated from the loaded trip expense record); omitted for Create (empty form). */
  defaultValues?: TripExpenseFormValues;
  onSubmit: (values: TripExpenseFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
  /** Renders every field disabled and hides Save - the row action's "View" state for a user with `trip_expense:view` but not `trip_expense:edit`. */
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
 * The shared Trip Expense Create/Edit form - composed entirely from the
 * Sprint 2 enterprise form components, mirroring `TripCatchForm`. There is
 * no Trip selector - the owning trip is always the current Trip Detail
 * page's trip (Sprint 6 Session 6's Navigation rule: "Users should never
 * manually choose the trip").
 *
 * `readOnly` wraps the whole field set in a native `<fieldset disabled>`,
 * which cascades disabled state to every descendant control without each
 * field needing its own `disabled` wiring, and hides the Save action.
 */
export function TripExpenseForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
  readOnly = false,
}: TripExpenseFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<TripExpenseFormValues>({
    resolver: zodResolver(tripExpenseFormSchema),
    defaultValues: defaultValues ?? DEFAULT_TRIP_EXPENSE_FORM_VALUES,
  });

  async function handleFormSubmit(values: TripExpenseFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<TripExpenseFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <fieldset disabled={readOnly} className="m-0 space-y-6 border-0 p-0">
        <FormSection title="Expense Details">
          <FormGrid columns={2}>
            <SearchableSelect
              label="Expense Type"
              required
              options={EXPENSE_TYPE_OPTIONS}
              value={watch("expense_type")}
              onChange={(value) => value && setValue("expense_type", value, { shouldValidate: true })}
              error={errors.expense_type?.message}
            />

            <CurrencyInput label="Amount" required error={errors.amount?.message} {...register("amount")} />

            <DatePicker
              label="Expense Date"
              required
              error={errors.expense_date?.message}
              value={toDateOrUndefined(watch("expense_date"))}
              onChange={(date) => setValue("expense_date", toIsoDateString(date), { shouldValidate: true })}
            />

            <FormField label="Vendor Name" error={errors.vendor_name?.message}>
              {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
                <Input
                  id={id}
                  aria-describedby={describedBy}
                  aria-invalid={ariaInvalid}
                  {...register("vendor_name")}
                />
              )}
            </FormField>

            <FormField label="Receipt Number" error={errors.receipt_number?.message}>
              {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
                <Input
                  id={id}
                  aria-describedby={describedBy}
                  aria-invalid={ariaInvalid}
                  {...register("receipt_number")}
                />
              )}
            </FormField>
          </FormGrid>
        </FormSection>

        <TextArea label="Description" error={errors.description?.message} {...register("description")} />
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
