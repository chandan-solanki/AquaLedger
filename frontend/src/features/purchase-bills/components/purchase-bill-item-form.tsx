"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import {
  FormActions,
  FormField,
  FormGrid,
  FormSection,
  PercentageInput,
  QuantityInput,
  RateInput,
  SearchableSelect,
} from "@/components/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePurchaseOrderItems } from "@/features/purchase-orders";
import {
  DEFAULT_PURCHASE_BILL_ITEM_FORM_VALUES,
  purchaseBillItemFormSchema,
  type PurchaseBillItemFormValues,
} from "@/features/purchase-bills/schemas/purchase-bill-item-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { formatQuantity } from "@/utils/format-number";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface PurchaseBillItemFormProps {
  /** Present for Edit (populated from the loaded item record); omitted for Create (empty form). */
  defaultValues?: PurchaseBillItemFormValues;
  onSubmit: (values: PurchaseBillItemFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
  /**
   * The parent purchase bill's own linked purchase order (Sprint 12
   * Session 12), if any - when present, offers a "Purchase Order Item"
   * selector sourced from that order's own items and their remaining
   * quantities (`GET /purchase-orders/{id}/items`). Omitted/null for a
   * standalone bill, which has nothing to link items against.
   */
  purchaseOrderId?: string | null;
}

/**
 * The shared Purchase Bill Item Create/Edit form - fields match
 * `PurchaseBillItemCreateRequest`/`PurchaseBillItemUpdateRequest` exactly
 * (app/modules/purchase/schemas.py). Rendered inside a Dialog on the
 * Purchase Bill Detail page (`PurchaseBillItemTable`), not a routed page,
 * mirroring `InvoiceItemForm`.
 *
 * Unlike `InvoiceItemForm`, there is no Trip Catch selector - a purchase
 * line has no link to a sold-fish master or a trip catch, so every field
 * here is a plain input. Financial fields (discount_amount/taxable_amount/
 * tax_amount/line_total) are never in this form - they are entirely
 * server-computed and only ever rendered read-only, in
 * `PurchaseBillItemTable`'s columns.
 */
export function PurchaseBillItemForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
  purchaseOrderId,
}: PurchaseBillItemFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<PurchaseBillItemFormValues>({
    resolver: zodResolver(purchaseBillItemFormSchema),
    defaultValues: defaultValues ?? DEFAULT_PURCHASE_BILL_ITEM_FORM_VALUES,
  });
  const purchaseOrderItemsQuery = usePurchaseOrderItems(purchaseOrderId ?? undefined);
  const purchaseOrderItems = purchaseOrderItemsQuery.data ?? [];
  const selectedPurchaseOrderItemId = watch("purchase_order_item_id");
  const selectedPurchaseOrderItem = purchaseOrderItems.find(
    (item) => item.id === selectedPurchaseOrderItemId
  );
  const enteredQuantity = watch("quantity");
  const remainingForSelectedItem = selectedPurchaseOrderItem
    ? Number(selectedPurchaseOrderItem.remainingQuantity ?? selectedPurchaseOrderItem.quantity)
    : undefined;
  const overLimitHint =
    selectedPurchaseOrderItem &&
    remainingForSelectedItem !== undefined &&
    enteredQuantity &&
    Number(enteredQuantity) > remainingForSelectedItem
      ? `Only ${formatQuantity(String(remainingForSelectedItem))} ${selectedPurchaseOrderItem.unit} remains available for billing.`
      : undefined;

  async function handleFormSubmit(values: PurchaseBillItemFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<PurchaseBillItemFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Item Details">
        <FormGrid columns={2}>
          {purchaseOrderId && (
            <>
              <SearchableSelect
                label="Purchase Order Item"
                description="Optional - bills this line against a specific purchase order item's remaining quantity. Fully billed items can't be selected."
                placeholder={
                  purchaseOrderItemsQuery.isLoading
                    ? "Loading purchase order items…"
                    : "Select a purchase order item (optional)"
                }
                className="md:col-span-full"
                options={purchaseOrderItems.map((item) => {
                  const remaining = Number(item.remainingQuantity ?? item.quantity);
                  const isFullyBilled = remaining <= 0;
                  const label = isFullyBilled
                    ? `${item.description ?? "Item"} — Ordered ${formatQuantity(item.quantity)} ${item.unit} (Fully billed)`
                    : `${item.description ?? "Item"} — Ordered ${formatQuantity(item.quantity)}, Billed ${formatQuantity(
                        item.billedQuantity ?? "0"
                      )}, Remaining ${formatQuantity(item.remainingQuantity ?? item.quantity)} ${item.unit}`;
                  return { value: item.id, label, disabled: isFullyBilled };
                })}
                value={watch("purchase_order_item_id") || undefined}
                onChange={(value) => {
                  setValue("purchase_order_item_id", value ?? "");
                  const selected = purchaseOrderItems.find((item) => item.id === value);
                  if (selected) {
                    setValue("description", selected.description ?? "", { shouldValidate: true });
                    setValue("unit", selected.unit, { shouldValidate: true });
                    setValue("rate", selected.rate, { shouldValidate: true });
                    setValue("tax_rate", selected.taxRate, { shouldValidate: true });
                  }
                }}
                error={errors.purchase_order_item_id?.message}
              />

              {selectedPurchaseOrderItem && (
                <p className="text-muted-foreground text-sm md:col-span-full">
                  Ordered: {formatQuantity(selectedPurchaseOrderItem.quantity)}{" "}
                  {selectedPurchaseOrderItem.unit} · Already billed:{" "}
                  {formatQuantity(selectedPurchaseOrderItem.billedQuantity ?? "0")}{" "}
                  {selectedPurchaseOrderItem.unit} · Remaining:{" "}
                  {formatQuantity(
                    selectedPurchaseOrderItem.remainingQuantity ?? selectedPurchaseOrderItem.quantity
                  )}{" "}
                  {selectedPurchaseOrderItem.unit}
                </p>
              )}
            </>
          )}

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

          <QuantityInput
            label="Quantity"
            required
            error={errors.quantity?.message ?? overLimitHint}
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
