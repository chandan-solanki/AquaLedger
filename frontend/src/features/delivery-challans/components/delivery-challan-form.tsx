"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { format, parseISO } from "date-fns";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { DatePicker, FormActions, FormGrid, FormSection, SearchableSelect, TextArea } from "@/components/form";
import { Button } from "@/components/ui/button";
import { useInvoiceOptions } from "@/features/delivery-challans/hooks/use-invoice-options";
import {
  DEFAULT_DELIVERY_CHALLAN_FORM_VALUES,
  deliveryChallanFormSchema,
  type DeliveryChallanFormValues,
} from "@/features/delivery-challans/schemas/delivery-challan-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface DeliveryChallanFormProps {
  /** Present for Edit (populated from the loaded delivery challan record); omitted for Create (empty form). */
  defaultValues?: DeliveryChallanFormValues;
  onSubmit: (values: DeliveryChallanFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
  /** Edit: the originating invoice is immutable after creation, so the picker is shown (for context) but disabled, never hidden. */
  disableInvoiceSelect?: boolean;
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
 * The shared Delivery Challan Create/Edit form - header fields only:
 * Invoice, Challan Date, Remarks, composed entirely from the enterprise
 * form components, mirroring `PurchaseOrderForm`. Owns its own submit
 * try/catch: a 422's `field_errors` map onto the matching fields, anything
 * else (409 not-draft, 404/422 invoice not found/not deliverable, network,
 * 5xx) surfaces as a toast.
 *
 * There is no Challan Number field (server-assigned only at dispatch) and
 * no Status field (always DRAFT at creation). There are no financial
 * fields, line items, or totals here either - items are a separate
 * sub-resource and this document carries no money at all.
 *
 * The Invoice field is a `SearchableSelect` over `useInvoiceOptions()`'s
 * `eligibleOptions` (ISSUED/PARTIALLY_PAID/PAID only, this feature's own
 * client-side narrowing - see that hook's own docstring for why) rather
 * than a raw text id field. The backend's own eligibility re-check
 * (`DELIVERY_CHALLAN_INVOICE_NOT_DELIVERABLE`) is left server-validated
 * only, mirroring `PurchaseOrderForm`'s posture toward its own Supplier
 * field.
 */
export function DeliveryChallanForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
  disableInvoiceSelect = false,
}: DeliveryChallanFormProps) {
  const invoiceOptions = useInvoiceOptions();
  const {
    handleSubmit,
    register,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<DeliveryChallanFormValues>({
    resolver: zodResolver(deliveryChallanFormSchema),
    defaultValues: defaultValues ?? DEFAULT_DELIVERY_CHALLAN_FORM_VALUES,
  });

  async function handleFormSubmit(values: DeliveryChallanFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<DeliveryChallanFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Delivery Challan Details">
        <FormGrid columns={2}>
          <SearchableSelect
            label="Invoice"
            required
            disabled={disableInvoiceSelect}
            description="Only issued, partially paid, or paid invoices can be delivered against."
            placeholder={invoiceOptions.isLoading ? "Loading invoices…" : "Select an invoice"}
            options={invoiceOptions.eligibleOptions}
            value={watch("invoice_id") || undefined}
            onChange={(value) => value && setValue("invoice_id", value, { shouldValidate: true })}
            error={errors.invoice_id?.message}
            className="md:col-span-full"
          />

          <DatePicker
            label="Challan Date"
            required
            error={errors.challan_date?.message}
            value={toDateOrUndefined(watch("challan_date"))}
            onChange={(date) => setValue("challan_date", toIsoDateString(date), { shouldValidate: true })}
          />
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
