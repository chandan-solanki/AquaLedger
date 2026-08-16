"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { format, parseISO } from "date-fns";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { DatePicker, FormActions, FormGrid, FormSection, SearchableSelect, TextArea } from "@/components/form";
import { Button } from "@/components/ui/button";
import { useBillablePurchaseOrders } from "@/features/purchase-bills/hooks/use-billable-purchase-orders";
import { useSupplierOptions } from "@/features/purchase-bills/hooks/use-supplier-options";
import {
  DEFAULT_PURCHASE_BILL_FORM_VALUES,
  purchaseBillFormSchema,
  type PurchaseBillFormValues,
} from "@/features/purchase-bills/schemas/purchase-bill-form-schema";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

export interface PurchaseBillFormProps {
  /** Present for Edit (populated from the loaded purchase bill record); omitted for Create (empty form). */
  defaultValues?: PurchaseBillFormValues;
  onSubmit: (values: PurchaseBillFormValues) => Promise<void>;
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
 * The shared Purchase Bill Create/Edit form - header fields only: Supplier,
 * Bill Date, Due Date, Remarks, composed entirely from the Sprint 2
 * enterprise form components, mirroring `InvoiceForm`. Owns its own submit
 * try/catch: a 422's `field_errors` map onto the matching fields, anything
 * else (409 not-draft, 404/422 supplier not found/inactive, network, 5xx -
 * see app/modules/purchase/exceptions.py) surfaces as a toast.
 *
 * There is no Bill Number field (server-assigned only at posting) and no
 * Status field (always DRAFT at creation; `PurchaseBillUpdateRequest` never
 * accepts it either). Unlike `InvoiceForm`, there is also no Transport
 * Charge/Other Charge field - the backend does not accept either on this
 * resource at all (see `purchaseBillFormSchema`'s own docstring). There are
 * no line items or totals here either - items are a separate sub-resource.
 *
 * The Supplier field is a `SearchableSelect` over `useSupplierOptions()`
 * (this feature's own hook, already built for the List page's Supplier
 * filter) rather than a raw text id field - `supplier_id` is a foreign key,
 * and picking from this tenant's actual suppliers is the only way to supply
 * a valid one. The backend's own "supplier must be active" rule
 * (`PurchaseBillSupplierInactiveError`) is left server-validated only,
 * mirroring how `InvoiceForm` leaves "company must be active" server-
 * validated.
 *
 * The optional Purchase Order field (Sprint 12 Session 12) only ever
 * appears in Create mode (`!defaultValues`) - `purchase_order_id` is
 * immutable after creation (no field on `PurchaseBillUpdateRequest`), so
 * there is nothing to show or change once a bill already exists. It stays
 * disabled until a supplier is picked (`useBillablePurchaseOrders` is
 * supplier-scoped and already filters to confirmed/fulfilled orders only -
 * the backend's own billable-status rule), and resets whenever the
 * supplier changes, since a previously-selected order could belong to the
 * old supplier.
 */
export function PurchaseBillForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}: PurchaseBillFormProps) {
  const isEdit = Boolean(defaultValues);
  const supplierOptions = useSupplierOptions();
  const {
    handleSubmit,
    register,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<PurchaseBillFormValues>({
    resolver: zodResolver(purchaseBillFormSchema),
    defaultValues: defaultValues ?? DEFAULT_PURCHASE_BILL_FORM_VALUES,
  });
  const supplierId = watch("supplier_id");
  const billablePurchaseOrders = useBillablePurchaseOrders(supplierId || undefined);

  async function handleFormSubmit(values: PurchaseBillFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<PurchaseBillFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormSection title="Purchase Bill Details">
        <FormGrid columns={2}>
          <SearchableSelect
            label="Supplier"
            required
            placeholder="Select a supplier"
            options={supplierOptions.options}
            value={watch("supplier_id") || undefined}
            onChange={(value) => {
              if (!value) return;
              setValue("supplier_id", value, { shouldValidate: true });
              setValue("purchase_order_id", "");
            }}
            error={errors.supplier_id?.message}
          />

          {!isEdit && (
            <SearchableSelect
              label="Purchase Order"
              description="Optional - links this bill to a confirmed or fulfilled purchase order for the selected supplier."
              placeholder={supplierId ? "Select a purchase order (optional)" : "Select a supplier first"}
              disabled={!supplierId}
              options={billablePurchaseOrders.options}
              value={watch("purchase_order_id") || undefined}
              onChange={(value) => setValue("purchase_order_id", value ?? "", { shouldValidate: true })}
              error={errors.purchase_order_id?.message}
            />
          )}

          <DatePicker
            label="Bill Date"
            required
            error={errors.bill_date?.message}
            value={toDateOrUndefined(watch("bill_date"))}
            onChange={(date) => setValue("bill_date", toIsoDateString(date), { shouldValidate: true })}
          />

          <DatePicker
            label="Due Date"
            error={errors.due_date?.message}
            value={toDateOrUndefined(watch("due_date"))}
            onChange={(date) => setValue("due_date", toIsoDateString(date), { shouldValidate: true })}
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
