"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { AsyncSelect, CurrencyInput, FormActions, FormGrid } from "@/components/form";
import type { ComboboxOption } from "@/components/form";
import { Button } from "@/components/ui/button";
import { purchaseBillKeys, purchaseBillService } from "@/features/purchase-bills";
import type { PurchaseBill, PurchaseBillStatus } from "@/features/purchase-bills";
import { useSearch } from "@/hooks/use-search";
import { toastError } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";
import { mapServerErrorsToForm } from "@/utils/map-server-errors-to-form";

// allocated_amount: Decimal, max_digits=14, decimal_places=2, gt=0 (app/modules/supplier_payments/schemas.py).
const AMOUNT_PATTERN = /^\d{1,12}(\.\d{1,2})?$/;

const amountField = z
  .string()
  .trim()
  .min(1, "Allocation amount is required")
  .refine((value) => AMOUNT_PATTERN.test(value), "Enter a valid amount (up to 2 decimal places)")
  .refine((value) => Number(value) > 0, "Must be greater than 0");

/**
 * Fields match SupplierPaymentAllocationCreateRequest/
 * SupplierPaymentAllocationUpdateRequest exactly (app/modules/
 * supplier_payments/schemas.py) - just the two the backend accepts, nothing
 * else. Colocated here rather than a separate schemas/ file since the form
 * itself is this small, mirroring `paymentAllocationFormSchema`.
 */
const supplierPaymentAllocationFormSchema = z.object({
  purchase_bill_id: z.string().trim().min(1, "Purchase bill is required"),
  allocated_amount: amountField,
});

export type SupplierPaymentAllocationFormValues = z.infer<typeof supplierPaymentAllocationFormSchema>;

export const DEFAULT_SUPPLIER_PAYMENT_ALLOCATION_FORM_VALUES: SupplierPaymentAllocationFormValues = {
  purchase_bill_id: "",
  allocated_amount: "",
};

export interface SupplierPaymentAllocationFormProps {
  /** The owning supplier payment's `supplier_id` - scopes the Purchase Bill search to that supplier's own bills (a real, backend-supported `supplier_id` filter), a UX convenience only: the backend itself never requires an allocation's bill to belong to the same supplier as the payment. */
  supplierId: string;
  /** The owning supplier payment's current `unallocated_amount` - shown as an informational hint only, never enforced client-side (see this component's own docstring). */
  paymentUnallocatedAmount: string;
  /** Present for Edit (populated from the loaded allocation record); omitted for Create (empty form). */
  defaultValues?: SupplierPaymentAllocationFormValues;
  onSubmit: (values: SupplierPaymentAllocationFormValues) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

const ALLOCATABLE_PURCHASE_BILL_STATUSES: PurchaseBillStatus[] = ["posted", "partially_paid"];

interface PurchaseBillSelectorFieldProps {
  value: string;
  supplierId: string;
  error?: string;
  onSelect: (bill: PurchaseBill) => void;
}

/**
 * A searchable Purchase Bill selector, backed by the Purchase Bills
 * feature's own public `purchaseBillService`/`purchaseBillKeys`
 * (`@/features/purchase-bills`) - no lookup logic duplicated here,
 * mirroring `InvoiceSelectorField` (`payment-allocation-form.tsx`).
 * Typeahead is driven by the backend's own `GET /purchase` search (`q`
 * matches bill_number and the billing supplier's name), scoped to the
 * owning supplier payment's supplier via the real `supplier_id` filter.
 * Results are narrowed to `posted`/`partially_paid` bills client-side - a
 * plain filter on an already-fetched `status` field, not a computation -
 * since those are the only statuses the backend accepts for a new
 * allocation (app/modules/supplier_payments/service.py's
 * `_ALLOCATABLE_PURCHASE_BILL_STATUSES`); the backend remains the actual
 * authority (422 `SUPPLIER_PAYMENT_PURCHASE_BILL_NOT_ALLOCATABLE`
 * otherwise). Each option's description shows Bill Date and Balance/Total
 * (per TASKS.md's "Display: Purchase Bill Number, Bill Date, Supplier,
 * Balance, Total") so the user can judge fit without leaving the form -
 * "Supplier" itself is omitted from the description since every result here
 * already belongs to the one supplier this payment is scoped to. The
 * currently selected bill is always resolved by id and merged into
 * `options`, so Edit mode shows a correct label immediately, before the user
 * has typed anything.
 */
function PurchaseBillSelectorField({ value, supplierId, error, onSelect }: PurchaseBillSelectorFieldProps) {
  const search = useSearch({ debounceMs: 300 });

  const searchQuery = useQuery({
    queryKey: ["purchase-bills", "search", supplierId, search.debouncedValue],
    queryFn: () =>
      purchaseBillService.listPurchaseBills({
        q: search.debouncedValue || undefined,
        supplier_id: supplierId,
        sort: "-bill_date",
        page: 1,
        page_size: 20,
      }),
  });

  const selectedBillQuery = useQuery({
    queryKey: purchaseBillKeys.detail(value),
    queryFn: () => purchaseBillService.getPurchaseBill(value),
    enabled: Boolean(value),
    staleTime: 5 * 60 * 1000,
  });

  const bills = useMemo(() => {
    const results = (searchQuery.data?.data ?? []).filter((bill) =>
      ALLOCATABLE_PURCHASE_BILL_STATUSES.includes(bill.status)
    );
    if (selectedBillQuery.data && !results.some((bill) => bill.id === selectedBillQuery.data!.id)) {
      return [selectedBillQuery.data, ...results];
    }
    return results;
  }, [searchQuery.data, selectedBillQuery.data]);

  const options = useMemo<ComboboxOption[]>(
    () =>
      bills.map((bill) => ({
        value: bill.id,
        label: bill.billNumber ?? "Draft bill",
        description: `${formatDate(bill.billDate)} · Balance: ${formatCurrency(bill.balanceAmount)} · Total: ${formatCurrency(bill.totalAmount)}`,
      })),
    [bills]
  );

  const selectedOption = options.find((option) => option.value === value);

  return (
    <div className="space-y-1.5 md:col-span-full">
      <AsyncSelect
        label="Purchase Bill"
        required
        placeholder="Search by bill number…"
        searchPlaceholder="Search purchase bills…"
        options={options}
        value={value || undefined}
        onSearchChange={search.setValue}
        isLoading={searchQuery.isFetching || selectedBillQuery.isLoading}
        onChange={(selectedId) => {
          const chosen = bills.find((bill) => bill.id === selectedId);
          if (chosen) onSelect(chosen);
        }}
        error={error}
      />
      {selectedOption?.description && (
        <p className="px-1 text-xs text-muted-foreground">{selectedOption.description}</p>
      )}
    </div>
  );
}

/**
 * The shared Supplier Payment Allocation Create/Edit form - just the two
 * fields the backend accepts (Purchase Bill, Allocation Amount), rendered
 * inside a Dialog on the Supplier Payment Detail page
 * (`SupplierPaymentAllocationTable`), not a routed page.
 *
 * The backend's two allocation ceilings - `allocated_amount` must not
 * exceed the purchase bill's current `balance_amount` nor the payment's
 * current `unallocated_amount` (app/modules/supplier_payments/domain/
 * allocation.py's `validate_allocation_amount`) - are deliberately left
 * server-validated only, surfacing as the generic 422 toast below: for an
 * update, the backend adjusts both ceilings by adding back this same
 * allocation's own prior amount before comparing, a live, transaction-
 * scoped calculation this form has no way to reproduce safely from cached
 * data without risking drift from the source of truth, mirroring
 * `PaymentAllocationForm`. Both ceiling values are still shown as
 * informational hints - the bill's balance/total in the Purchase Bill
 * selector's option description, the payment's unallocated amount under
 * Allocation Amount - so the user rarely needs the round trip to find out.
 */
export function SupplierPaymentAllocationForm({
  supplierId,
  paymentUnallocatedAmount,
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}: SupplierPaymentAllocationFormProps) {
  const {
    handleSubmit,
    register,
    setError,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<SupplierPaymentAllocationFormValues>({
    resolver: zodResolver(supplierPaymentAllocationFormSchema),
    defaultValues: defaultValues ?? DEFAULT_SUPPLIER_PAYMENT_ALLOCATION_FORM_VALUES,
  });

  async function handleFormSubmit(values: SupplierPaymentAllocationFormValues) {
    try {
      await onSubmit(values);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.category === "validation" && apiError.fieldErrors) {
        mapServerErrorsToForm<SupplierPaymentAllocationFormValues>(apiError.fieldErrors, setError);
        return;
      }
      toastError(apiError.message);
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} noValidate className="space-y-6">
      <FormGrid columns={2}>
        <PurchaseBillSelectorField
          value={watch("purchase_bill_id")}
          supplierId={supplierId}
          error={errors.purchase_bill_id?.message}
          onSelect={(bill) => setValue("purchase_bill_id", bill.id, { shouldValidate: true })}
        />

        <CurrencyInput
          label="Allocation Amount"
          required
          description={`Up to ${formatCurrency(paymentUnallocatedAmount)} unallocated on this payment.`}
          error={errors.allocated_amount?.message}
          {...register("allocated_amount")}
        />
      </FormGrid>

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
