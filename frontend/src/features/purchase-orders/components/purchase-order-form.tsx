"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { format, parseISO } from "date-fns";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { DatePicker, FormActions, FormGrid, FormSection, SearchableSelect, TextArea } from "@/components/form";
import { Button } from "@/components/ui/button";
import { useSupplierOptions } from "@/features/purchase-orders/hooks/use-supplier-options";
import {
  DEFAULT_PURCHASE_ORDER_FORM_VALUES,
  purchaseOrderFormSchema,
  type PurchaseOrderFormValues,
} from "@/features/purchase-orders/schemas/purchase-order-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface PurchaseOrderFormProps {
  /** Present for Edit (populated from the loaded purchase order record); omitted for Create (empty form). */
  defaultValues?: PurchaseOrderFormValues;
  onSubmit: (values: PurchaseOrderFormValues) => Promise<void>;
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
 * The shared Purchase Order Create/Edit form - header fields only:
 * Supplier, PO Date, Expected Delivery Date, Remarks, composed entirely
 * from the enterprise form components, mirroring `PurchaseBillForm`. Owns
 * its own submit try/catch: a 422's `field_errors` map onto the matching
 * fields, anything else (409 not-draft, 404/422 supplier not found/
 * inactive, network, 5xx) surfaces as a toast.
 *
 * There is no PO Number field (server-assigned only at confirm) and no
 * Status field (always DRAFT at creation; `PurchaseOrderUpdateRequest`
 * never accepts it either). There are no financial fields, line items, or
 * totals here either - items are a separate sub-resource.
 *
 * The Supplier field is a `SearchableSelect` over `useSupplierOptions()`
 * (this feature's own hook) rather than a raw text id field - `supplier_id`
 * is a foreign key, and picking from this tenant's actual suppliers is the
 * only way to supply a valid one. The backend's own "supplier must be
 * active" rule (`PurchaseOrderSupplierInactiveError`) is left
 * server-validated only, mirroring `PurchaseBillForm`.
 */
export function PurchaseOrderForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}: PurchaseOrderFormProps) {
  const supplierOptions = useSupplierOptions();
  const {
    handleSubmit,
    register,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<PurchaseOrderFormValues>({
    resolver: zodResolver(purchaseOrderFormSchema),
    defaultValues: defaultValues ?? DEFAULT_PURCHASE_ORDER_FORM_VALUES,
  });

  async function handleFormSubmit(values: PurchaseOrderFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<PurchaseOrderFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Purchase Order Details">
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
            label="PO Date"
            required
            error={errors.order_date?.message}
            value={toDateOrUndefined(watch("order_date"))}
            onChange={(date) => setValue("order_date", toIsoDateString(date), { shouldValidate: true })}
          />

          <DatePicker
            label="Expected Delivery Date"
            error={errors.expected_delivery_date?.message}
            value={toDateOrUndefined(watch("expected_delivery_date"))}
            onChange={(date) =>
              setValue("expected_delivery_date", toIsoDateString(date), { shouldValidate: true })
            }
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
