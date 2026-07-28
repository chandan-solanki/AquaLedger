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
import { SUPPLIER_PAYMENT_METHOD_OPTIONS } from "@/features/supplier-payments/constants/supplier-payment-method";
import { useSupplierOptions } from "@/features/supplier-payments/hooks/use-supplier-options";
import {
  DEFAULT_SUPPLIER_PAYMENT_FORM_VALUES,
  supplierPaymentFormSchema,
  type SupplierPaymentFormValues,
} from "@/features/supplier-payments/schemas/supplier-payment-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface SupplierPaymentFormProps {
  /** Present for Edit (populated from the loaded payment record); omitted for Create (empty form). */
  defaultValues?: SupplierPaymentFormValues;
  onSubmit: (values: SupplierPaymentFormValues) => Promise<void>;
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
 * The shared Supplier Payment Create/Edit form - header fields only (Sprint
 * 9 Session 2, see TASKS.md): Supplier, Payment Date, Payment Method, Amount,
 * Reference Number, Bank Name, Remarks, composed entirely from the Sprint 2
 * enterprise form components, mirroring `PaymentForm`. Owns its own submit
 * try/catch: a 422's `field_errors` map onto the matching fields, anything
 * else (409 not-draft, 404/422 supplier not found/inactive, network, 5xx -
 * see app/modules/supplier_payments/exceptions.py) surfaces as a toast.
 *
 * There is no Payment Number field (server-assigned only at posting) and no
 * Status/Allocated Amount/Unallocated Amount fields (always DRAFT/0/`amount`
 * at creation; only later sessions' Allocate/Post actions change them) -
 * none of these is a real `SupplierPaymentCreateRequest`/
 * `SupplierPaymentUpdateRequest` field.
 *
 * The Supplier field is a `SearchableSelect` over `useSupplierOptions()`
 * (this feature's own hook, already built in Session 1 for the List page's
 * Supplier filter) rather than a raw text id field - `supplier_id` is a
 * foreign key, and picking from this tenant's actual suppliers is the only
 * way to supply a valid one. The backend's own "supplier must be active"
 * rule (`SupplierPaymentSupplierInactiveError`) is left server-validated
 * only, mirroring how `PaymentForm` leaves "company must be active"
 * server-validated.
 */
export function SupplierPaymentForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}: SupplierPaymentFormProps) {
  const supplierOptions = useSupplierOptions();
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<SupplierPaymentFormValues>({
    resolver: zodResolver(supplierPaymentFormSchema),
    defaultValues: defaultValues ?? DEFAULT_SUPPLIER_PAYMENT_FORM_VALUES,
  });

  async function handleFormSubmit(values: SupplierPaymentFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<SupplierPaymentFormValues>(apiError.fieldErrors, setError);
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
            label="Supplier"
            required
            placeholder="Select a supplier"
            options={supplierOptions.options}
            value={watch("supplier_id") || undefined}
            onChange={(value) => value && setValue("supplier_id", value, { shouldValidate: true })}
            error={errors.supplier_id?.message}
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
            options={SUPPLIER_PAYMENT_METHOD_OPTIONS}
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
