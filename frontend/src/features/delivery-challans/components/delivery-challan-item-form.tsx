"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { FormActions, FormGrid, FormSection, QuantityInput, SearchableSelect } from "@/components/form";
import { Button } from "@/components/ui/button";
import { useInvoiceDeliverySummary } from "@/features/delivery-challans/hooks/use-invoice-delivery-summary";
import {
  DEFAULT_DELIVERY_CHALLAN_ITEM_FORM_VALUES,
  deliveryChallanItemFormSchema,
  type DeliveryChallanItemFormValues,
} from "@/features/delivery-challans/schemas/delivery-challan-item-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { formatQuantity } from "@/utils/format-number";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface DeliveryChallanItemFormProps {
  /** Present for Edit (populated from the loaded item record); omitted for Create (empty form). */
  defaultValues?: DeliveryChallanItemFormValues;
  onSubmit: (values: DeliveryChallanItemFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
  /** The parent delivery challan's own linked invoice - every item added must reference one of its items. */
  invoiceId: string;
  /**
   * Edit only: the item's own current quantity, before this edit. Added
   * back onto the selected invoice item's own `remainingQuantity` so
   * raising the quantity back up to (but not beyond) the invoice item's own
   * invoiced quantity always looks achievable - mirrors the backend's own
   * `exclude_item_id` semantics in
   * `DeliveryChallanService._validate_invoice_item_link`.
   */
  editingOwnQuantity?: string;
}

/**
 * The shared Delivery Challan Item Create/Edit form - the most important UI
 * piece in this feature (this session's own Phase 8/9): selecting which
 * invoice item this line delivers against, and how much. Rendered inside a
 * Dialog on the Delivery Challan Detail page
 * (`delivery-challan-item-table.tsx`), not a routed page, mirroring
 * `PurchaseOrderItemForm`.
 *
 * `invoice_item_id` is immutable after creation (no field for it on
 * `DeliveryChallanItemUpdateRequest`), so the Invoice Item picker is shown
 * (for context) but disabled on Edit, never hidden - only `quantity` can
 * change. There is no description/unit/rate field - a delivery challan item
 * carries no financial fields at all, and `unit` is always derived
 * server-side from the linked invoice item.
 *
 * Every "Invoiced"/"Delivered"/"Remaining" figure shown here comes from
 * `useInvoiceDeliverySummary` - a client-side reconstruction, never an
 * authoritative backend field (see that hook's own docstring). The
 * quantity cap is a UX guard only: the backend's own over-delivery check
 * (`DELIVERY_CHALLAN_OVER_DELIVERY`) remains the actual authority.
 */
export function DeliveryChallanItemForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
  invoiceId,
  editingOwnQuantity,
}: DeliveryChallanItemFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<DeliveryChallanItemFormValues>({
    resolver: zodResolver(deliveryChallanItemFormSchema),
    defaultValues: defaultValues ?? DEFAULT_DELIVERY_CHALLAN_ITEM_FORM_VALUES,
  });
  const { summaries, isLoading } = useInvoiceDeliverySummary(invoiceId);
  const isEditing = Boolean(defaultValues);
  const selectedInvoiceItemId = watch("invoice_item_id");
  const selectedSummary = summaries.find((summary) => summary.invoiceItem.id === selectedInvoiceItemId);
  const remainingForSelected = selectedSummary
    ? selectedSummary.remainingQuantity + Number(editingOwnQuantity ?? "0")
    : undefined;
  const enteredQuantity = watch("quantity");
  const overLimitHint =
    selectedSummary &&
    remainingForSelected !== undefined &&
    enteredQuantity &&
    Number(enteredQuantity) > remainingForSelected
      ? `Only ${formatQuantity(remainingForSelected)} ${selectedSummary.invoiceItem.unit} remaining for delivery.`
      : undefined;

  async function handleFormSubmit(values: DeliveryChallanItemFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<DeliveryChallanItemFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Item Details">
        <FormGrid columns={1}>
          <SearchableSelect
            label="Invoice Item"
            required
            disabled={isEditing}
            description="Which invoiced item this delivery line covers. Fully delivered items can't be selected."
            placeholder={isLoading ? "Loading invoice items…" : "Select an invoice item"}
            options={summaries.map((summary) => {
              const isFullyDelivered = summary.remainingQuantity <= 0;
              const label = isFullyDelivered
                ? `${summary.invoiceItem.description ?? "Item"} — Invoiced ${formatQuantity(summary.invoiceItem.quantity)} ${summary.invoiceItem.unit} (Fully delivered)`
                : `${summary.invoiceItem.description ?? "Item"} — Invoiced ${formatQuantity(summary.invoiceItem.quantity)}, Delivered ${formatQuantity(summary.deliveredQuantity)}, Remaining ${formatQuantity(summary.remainingQuantity)} ${summary.invoiceItem.unit}`;
              return { value: summary.invoiceItem.id, label, disabled: isFullyDelivered && !isEditing };
            })}
            value={watch("invoice_item_id") || undefined}
            onChange={(value) => value && setValue("invoice_item_id", value, { shouldValidate: true })}
            error={errors.invoice_item_id?.message}
          />

          {selectedSummary && (
            <p className="text-muted-foreground text-sm">
              Invoiced: {formatQuantity(selectedSummary.invoiceItem.quantity)} {selectedSummary.invoiceItem.unit}{" "}
              · Already delivered (other lines):{" "}
              {formatQuantity(selectedSummary.deliveredQuantity - Number(editingOwnQuantity ?? "0"))}{" "}
              {selectedSummary.invoiceItem.unit} · Remaining:{" "}
              {formatQuantity(remainingForSelected ?? selectedSummary.remainingQuantity)} {selectedSummary.invoiceItem.unit}
            </p>
          )}

          <QuantityInput
            label="Delivery Quantity"
            required
            unit={selectedSummary?.invoiceItem.unit}
            error={errors.quantity?.message ?? overLimitHint}
            {...register("quantity")}
          />
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
