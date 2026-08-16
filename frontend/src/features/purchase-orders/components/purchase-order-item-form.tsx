"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { FormActions, FormField, FormGrid, FormSection, PercentageInput, QuantityInput, RateInput } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DEFAULT_PURCHASE_ORDER_ITEM_FORM_VALUES,
  purchaseOrderItemFormSchema,
  type PurchaseOrderItemFormValues,
} from "@/features/purchase-orders/schemas/purchase-order-item-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface PurchaseOrderItemFormProps {
  /** Present for Edit (populated from the loaded item record); omitted for Create (empty form). */
  defaultValues?: PurchaseOrderItemFormValues;
  onSubmit: (values: PurchaseOrderItemFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

/**
 * The shared Purchase Order Item Create/Edit form - fields match
 * `PurchaseOrderItemCreateRequest`/`PurchaseOrderItemUpdateRequest` exactly
 * (app/modules/purchase_orders/schemas.py). Rendered inside a Dialog on the
 * Purchase Order Detail page (`PurchaseOrderItemTable`), not a routed page,
 * mirroring `PurchaseBillItemForm`.
 *
 * There is no fish/product selector - a purchase order line has no link to
 * a fish master or a trip catch, so every field here is a plain input.
 * Financial fields (discount_amount/taxable_amount/tax_amount/line_total)
 * are never in this form - they are entirely server-computed and only ever
 * rendered read-only, in `PurchaseOrderItemTable`'s columns.
 */
export function PurchaseOrderItemForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}: PurchaseOrderItemFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<PurchaseOrderItemFormValues>({
    resolver: zodResolver(purchaseOrderItemFormSchema),
    defaultValues: defaultValues ?? DEFAULT_PURCHASE_ORDER_ITEM_FORM_VALUES,
  });

  async function handleFormSubmit(values: PurchaseOrderItemFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<PurchaseOrderItemFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Item Details">
        <FormGrid columns={2}>
          <FormField label="Description" required error={errors.description?.message} className="md:col-span-full">
            {({ id, describedBy, "aria-invalid": ariaInvalid }) => (
              <Input
                id={id}
                aria-describedby={describedBy}
                aria-invalid={ariaInvalid}
                {...register("description")}
              />
            )}
          </FormField>

          <QuantityInput label="Quantity" required error={errors.quantity?.message} {...register("quantity")} />

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
