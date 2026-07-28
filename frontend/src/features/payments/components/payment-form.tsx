"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { format, parseISO } from "date-fns";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import {
  CurrencyInput,
  DatePicker,
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  SearchableSelect,
  TextArea,
} from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PAYMENT_METHOD_OPTIONS } from "@/features/payments/constants/payment-method";
import { useCompanyOptions } from "@/features/payments/hooks/use-company-options";
import {
  DEFAULT_PAYMENT_FORM_VALUES,
  paymentFormSchema,
  type PaymentFormValues,
} from "@/features/payments/schemas/payment-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface PaymentFormProps {
  /** Present for Edit (populated from the loaded payment record); omitted for Create (empty form). */
  defaultValues?: PaymentFormValues;
  onSubmit: (values: PaymentFormValues) => Promise<void>;
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
 * The shared Payment Create/Edit form - header fields only (Sprint 8
 * Session 2, see TASKS.md): Customer, Payment Date, Payment Method, Amount,
 * Reference Number, Bank Name, Remarks, composed entirely from the Sprint 2
 * enterprise form components, mirroring `InvoiceForm`. Owns its own submit
 * try/catch: a 422's `field_errors` map onto the matching fields, anything
 * else (409 not-draft, 404/422 company not found/inactive, network, 5xx -
 * see app/modules/payments/exceptions.py) surfaces as a toast.
 *
 * There is no Payment Number field (server-assigned only at posting) and no
 * Status/Allocated Amount/Unallocated Amount fields (always DRAFT/0/`amount`
 * at creation; only later sessions' Allocate/Post actions change them) -
 * none of these is a real `PaymentCreateRequest`/`PaymentUpdateRequest`
 * field.
 *
 * The Customer field is a `SearchableSelect` over `useCompanyOptions()`
 * (this feature's own hook, already built in Session 1 for the List page's
 * Company filter) rather than a raw text id field - `company_id` is a
 * foreign key, and picking from this tenant's actual companies is the only
 * way to supply a valid one. The backend's own "company must be active"
 * rule (`PaymentCompanyInactiveError`) is left server-validated only,
 * mirroring how `InvoiceForm` leaves "company must be active" server-
 * validated.
 */
export function PaymentForm({ defaultValues, onSubmit, onCancel, submitLabel = "Save" }: PaymentFormProps) {
  const companyOptions = useCompanyOptions();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<PaymentFormValues>({
    resolver: zodResolver(paymentFormSchema),
    defaultValues: defaultValues ?? DEFAULT_PAYMENT_FORM_VALUES,
  });

  async function handleFormSubmit(values: PaymentFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<PaymentFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Payment Details">
        <FormGrid columns={2}>
          <SearchableSelect
            label="Customer"
            required
            placeholder="Select a customer"
            options={companyOptions.options}
            value={watch("company_id") || undefined}
            onChange={(value) => value && setValue("company_id", value, { shouldValidate: true })}
            error={errors.company_id?.message}
          />

          <DatePicker
            label="Payment Date"
            required
            error={errors.payment_date?.message}
            value={toDateOrUndefined(watch("payment_date"))}
            onChange={(date) => setValue("payment_date", toIsoDateString(date), { shouldValidate: true })}
          />

          <SearchableSelect
            label="Payment Method"
            required
            options={PAYMENT_METHOD_OPTIONS}
            value={watch("payment_method")}
            onChange={(value) => value && setValue("payment_method", value, { shouldValidate: true })}
            error={errors.payment_method?.message}
          />

          <CurrencyInput label="Amount" required error={errors.amount?.message} {...register("amount")} />

          <FormField label="Reference Number" error={errors.reference_number?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("reference_number")}
              />
            )}
          </FormField>

          <FormField label="Bank Name" error={errors.bank_name?.message}>
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input id={id} aria-describedby={describedBy} aria-invalid={ariaInvalid} {...register("bank_name")} />
            )}
          </FormField>
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
