"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { format, parseISO } from "date-fns";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import {
  CurrencyInput,
  DatePicker,
  FormActions,
  FormGrid,
  FormSection,
  SearchableSelect,
  TextArea,
} from "@/components/form";
import { Button } from "@/components/ui/button";
import { useCompanyOptions } from "@/features/invoices/hooks/use-company-options";
import {
  DEFAULT_INVOICE_FORM_VALUES,
  invoiceFormSchema,
  type InvoiceFormValues,
} from "@/features/invoices/schemas/invoice-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface InvoiceFormProps {
  /** Present for Edit (populated from the loaded invoice record); omitted for Create (empty form). */
  defaultValues?: InvoiceFormValues;
  onSubmit: (values: InvoiceFormValues) => Promise<void>;
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
 * The shared Invoice Create/Edit form - header fields only (Sprint 7
 * Session 2, see TASKS.md): Company, Invoice Date, Due Date, Transport
 * Charge, Other Charge, Remarks, composed entirely from the Sprint 2
 * enterprise form components, mirroring `TripForm`/`BoatForm`. Owns its own
 * submit try/catch: a 422's `field_errors` map onto the matching fields,
 * anything else (409 not-draft, 404/422 company not found/inactive,
 * network, 5xx - see app/modules/invoices/exceptions.py) surfaces as a
 * toast, per this session's Error Handling scope.
 *
 * There is no Invoice Number field (server-assigned only at issue) and no
 * Status field (always DRAFT at creation; only a later session's Issue
 * action changes it) - neither is a real `InvoiceCreateRequest`/
 * `InvoiceUpdateRequest` field. There are also no line items or totals -
 * Session 3+ scope.
 *
 * The Company field is a `SearchableSelect` over `useCompanyOptions()`
 * (this feature's own hook, already built in Session 1 for the List page's
 * Company filter) rather than a raw text id field - `company_id` is a
 * foreign key, and picking from this tenant's actual companies is the only
 * way to supply a valid one. The backend's own "company must be active"
 * rule (`InvoiceCompanyInactiveError`) is left server-validated only,
 * mirroring how `TripForm` leaves "boat already active" server-validated.
 */
export function InvoiceForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save" }: InvoiceFormProps) {
  const companyOptions = useCompanyOptions();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<InvoiceFormValues>({
    resolver: zodResolver(invoiceFormSchema),
    defaultValues: defaultValues ?? DEFAULT_INVOICE_FORM_VALUES,
  });

  async function handleFormSubmit(values: InvoiceFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<InvoiceFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Invoice Details">
        <FormGrid columns={2}>
          <SearchableSelect
            label="Company"
            required
            placeholder="Select a company"
            options={companyOptions.options}
            value={watch("company_id") || undefined}
            onChange={(value) => value && setValue("company_id", value, { shouldValidate: true })}
            error={errors.company_id?.message}
          />

          <DatePicker
            label="Invoice Date"
            required
            error={errors.invoice_date?.message}
            value={toDateOrUndefined(watch("invoice_date"))}
            onChange={(date) => setValue("invoice_date", toIsoDateString(date), { shouldValidate: true })}
          />

          <DatePicker
            label="Due Date"
            error={errors.due_date?.message}
            value={toDateOrUndefined(watch("due_date"))}
            onChange={(date) => setValue("due_date", toIsoDateString(date), { shouldValidate: true })}
          />

          <CurrencyInput
            label="Transport Charge"
            error={errors.transport_charge?.message}
            {...register("transport_charge")}
          />

          <CurrencyInput label="Other Charge" error={errors.other_charge?.message} {...register("other_charge")} />
        </FormGrid>
      </FormSection>

      <TextArea label="Remarks" error={errors.remarks?.message} {...register("remarks")} />

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
